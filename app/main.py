import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, unquote

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from . import config
from .job_store import atualizar_job, criar_job, ler_job
from .logger import log, log_error, mask_cpf
from .pades_signer import assinar_pdf_pades
from .pkce import gerar_pkce
from .serpro_client import (
    montar_url_autorizacao,
    recuperar_certificado_serpro,
    trocar_code_por_token,
)
from .session_store import ler_sessao_valida, salvar_sessao


app = FastAPI(
    title="SERPRO Python PAdES Service",
    version="1.0.0",
)


class CriarAssinaturaRequest(BaseModel):
    cpf: str
    pdfBase64: str
    alias: str | None = None


def limpar_cpf(cpf: str) -> str:
    return "".join(ch for ch in str(cpf or "") if ch.isdigit())


def parse_callback_query(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if not code or not state:
        url = str(request.url)
        raw = url.split("?", 1)[1] if "?" in url else ""
        params = parse_qs(unquote(raw))

        code = code or (params.get("code") or [None])[0]
        state = state or (params.get("state") or [None])[0]
        error = error or (params.get("error") or [None])[0]

    return code, state, error


@app.get("/")
async def root():
    return {
        "service": "serpro-python-pades-service",
        "status": "online",
        "signatureFormat": config.SERPRO_SIGNATURE_FORMAT,
        "scope": config.SERPRO_SCOPE,
    }


@app.post("/assinaturas")
async def criar_assinatura(req: CriarAssinaturaRequest):
    try:
        cpf = limpar_cpf(req.cpf)

        if not cpf or not req.pdfBase64:
            return JSONResponse(
                {
                    "sucesso": False,
                    "erro": "Informe cpf e pdfBase64",
                },
                status_code=400,
            )

        protocolo = str(uuid.uuid4())
        pkce = gerar_pkce()
        alias = req.alias or "Documento PDF"

        job = await criar_job(
            protocolo,
            {
                "cpf": cpf,
                "cpfMascarado": mask_cpf(cpf),
                "alias": alias,
                "scope": config.SERPRO_SCOPE,
                "codeVerifier": pkce["code_verifier"],
                "status": "AGUARDANDO_AUTORIZACAO",
                "pdfBase64": req.pdfBase64,
            },
        )

        log(
            protocolo,
            "CRIAR_ASSINATURA",
            "Job criado",
            {
                "cpf": mask_cpf(cpf),
                "scope": config.SERPRO_SCOPE,
            },
        )

        sessao = await ler_sessao_valida(cpf)

        if sessao and config.SERPRO_SCOPE == "signature_session":
            await atualizar_job(
                protocolo,
                {
                    "status": "AUTORIZADO_POR_SESSAO",
                },
            )

            asyncio.create_task(processar_assinatura(protocolo, sessao["accessToken"]))

            return {
                "sucesso": True,
                "protocolo": protocolo,
                "status": "AUTORIZADO_POR_SESSAO",
            }

        url = montar_url_autorizacao(
            protocolo,
            cpf,
            pkce["code_challenge"],
        )

        await atualizar_job(
            protocolo,
            {
                "urlAutorizacao": url,
            },
        )

        return {
            "sucesso": True,
            "protocolo": protocolo,
            "status": job["status"],
            "urlAutorizacao": url,
        }

    except Exception as erro:
        log_error(None, "POST_ASSINATURAS", erro)

        return JSONResponse(
            {
                "sucesso": False,
                "erro": str(erro),
            },
            status_code=500,
        )


@app.get("/serpro/callback")
async def callback(request: Request):
    code, state, error = parse_callback_query(request)
    protocolo = state

    try:
        log(
            protocolo,
            "CALLBACK_SERPRO",
            "Callback recebido",
            {
                "hasCode": bool(code),
                "error": error,
            },
        )

        if not protocolo:
            return PlainTextResponse(
                "Callback inválido: state não encontrado.",
                status_code=400,
            )

        job = await ler_job(protocolo)

        if not job:
            return PlainTextResponse(
                "Protocolo não encontrado.",
                status_code=404,
            )

        if error:
            await atualizar_job(
                protocolo,
                {
                    "status": "AUTORIZACAO_RECUSADA",
                    "erro": error,
                },
            )

            return PlainTextResponse(
                "Autorização recusada pelo usuário.",
                status_code=400,
            )

        if not code:
            return PlainTextResponse(
                "Callback inválido: code não encontrado.",
                status_code=400,
            )

        await atualizar_job(
            protocolo,
            {
                "status": "TROCANDO_TOKEN",
                "authorizationCode": code,
            },
        )

        token_data = await trocar_code_por_token(
            code,
            job["codeVerifier"],
        )

        expires_in = int(token_data.get("expires_in") or 300)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        await salvar_sessao(
            job["cpf"],
            {
                "accessToken": token_data["access_token"],
                "tokenType": token_data.get("token_type", "Bearer"),
                "expiresIn": expires_in,
                "expiresAt": expires_at.isoformat(),
                "scope": token_data.get("scope", job["scope"]),
                "authorizedIdentificationType": token_data.get("authorized_identification_type"),
                "authorizedIdentification": token_data.get("authorized_identification"),
            },
        )

        await atualizar_job(
            protocolo,
            {
                "status": "AUTORIZADO",
                "tokenExpiresAt": expires_at.isoformat(),
            },
        )

        asyncio.create_task(processar_assinatura(protocolo, token_data["access_token"]))

        return PlainTextResponse(
            "Autorização recebida com sucesso. Você já pode fechar esta janela."
        )

    except Exception as erro:
        log_error(protocolo, "CALLBACK_SERPRO", erro)

        if protocolo:
            await atualizar_job(
                protocolo,
                {
                    "status": "ERRO",
                    "erro": str(erro),
                },
            )

        return PlainTextResponse(
            "Erro ao processar callback SERPRO.",
            status_code=500,
        )


@app.get("/assinaturas/{protocolo}")
async def consultar(protocolo: str):
    job = await ler_job(protocolo)

    if not job:
        return JSONResponse(
            {
                "sucesso": False,
                "erro": "Protocolo não encontrado",
            },
            status_code=404,
        )

    return {
        "sucesso": True,
        "protocolo": job["protocolo"],
        "status": job["status"],
        "criadoEm": job["criadoEm"],
        "atualizadoEm": job["atualizadoEm"],
        "cpf": job["cpfMascarado"],
        "alias": job["alias"],
        "scope": job["scope"],
        "urlAutorizacao": job.get("urlAutorizacao")
        if job["status"] == "AGUARDANDO_AUTORIZACAO"
        else None,
        "erro": job.get("erro"),
        "pdfAssinadoBase64": job.get("pdfAssinadoBase64")
        if job["status"] == "ASSINADO"
        else None,
    }


async def processar_assinatura(protocolo: str, access_token: str):
    try:
        job = await ler_job(protocolo)

        if not job:
            raise RuntimeError("Job não encontrado")

        await atualizar_job(
            protocolo,
            {
                "status": "RECUPERANDO_CERTIFICADO",
            },
        )

        log(
            protocolo,
            "CERTIFICATE_DISCOVERY",
            "Recuperando certificado SERPRO",
        )

        cert_pem = await recuperar_certificado_serpro(access_token)

        await atualizar_job(
            protocolo,
            {
                "status": "ASSINANDO_PDF",
            },
        )

        log(
            protocolo,
            "PADES",
            "Assinando PDF com pyHanko",
        )

        signed_b64 = await assinar_pdf_pades(
            pdf_base64=job["pdfBase64"],
            certificate_pem=cert_pem,
            access_token=access_token,
            protocolo=protocolo,
            alias=job["alias"],
        )

        await atualizar_job(
            protocolo,
            {
                "status": "ASSINADO",
                "pdfAssinadoBase64": signed_b64,
                "pdfBase64": None,
            },
        )

        log(
            protocolo,
            "ASSINADO",
            "Processo finalizado",
        )

    except Exception as erro:
        log_error(protocolo, "PROCESSAMENTO", erro)

        await atualizar_job(
            protocolo,
            {
                "status": "ERRO",
                "erro": str(erro),
            },
        )
