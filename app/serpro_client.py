from urllib.parse import urlencode

import httpx

from . import config


def montar_url_autorizacao(protocolo: str, cpf: str, code_challenge: str) -> str:
    params = {
        "response_type": "code",
        "client_id": config.SERPRO_CLIENT_ID,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "redirect_uri": config.CALLBACK_URL,
        "scope": config.SERPRO_SCOPE,
        "state": protocolo,
        "login_hint": "".join(ch for ch in str(cpf or "") if ch.isdigit()),
    }

    return f"{config.SERPRO_AUTHORIZE_URL}?{urlencode(params)}"


async def trocar_code_por_token(code: str, code_verifier: str) -> dict:
    data = {
        "grant_type": "authorization_code",
        "client_id": config.SERPRO_CLIENT_ID,
        "client_secret": config.SERPRO_CLIENT_SECRET,
        "code": code,
        "code_verifier": code_verifier,
        "redirect_uri": config.CALLBACK_URL,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            config.SERPRO_TOKEN_URL,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "cache-control": "no-cache",
            },
        )

        response.raise_for_status()
        return response.json()


async def recuperar_certificado_serpro(access_token: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(
            config.SERPRO_CERTIFICATE_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )

        response.raise_for_status()
        data = response.json()

    certificates = data.get("certificates") or []

    if not certificates:
        raise RuntimeError("SERPRO não retornou certificados")

    pem = "\n".join(
        cert.get("certificate", "")
        for cert in certificates
        if cert.get("certificate")
    )

    if not pem.strip():
        raise RuntimeError("SERPRO retornou certificates sem certificate")

    return pem


async def assinar_hash_serpro(
    access_token: str,
    id_: str,
    alias: str,
    hash_base64: str,
) -> str:
    payload = {
        "hashes": [
            {
                "id": id_,
                "alias": alias,
                "hash": hash_base64,
                "hash_algorithm": config.HASH_ALGORITHM_OID,
                "signature_format": config.SERPRO_SIGNATURE_FORMAT,
            }
        ]
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            config.SERPRO_SIGNATURE_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )

        response.raise_for_status()
        data = response.json()

    signature = (data.get("signatures") or [{}])[0].get("raw_signature")

    if not signature:
        raise RuntimeError(f"SERPRO não retornou raw_signature: {data}")

    return signature
