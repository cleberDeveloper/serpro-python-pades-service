import json
from datetime import datetime, timezone
from pathlib import Path

from .config import JOBS_DIR
from .crypto_store import encrypt_json, decrypt_json


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def job_dir(protocolo: str) -> Path:
    return JOBS_DIR / protocolo


def job_file(protocolo: str) -> Path:
    return job_dir(protocolo) / "job.json.enc"


async def criar_job(protocolo: str, data: dict) -> dict:
    job = {
        "protocolo": protocolo,
        "criadoEm": now(),
        "atualizadoEm": now(),
        "erro": None,
        "pdfAssinadoBase64": None,
        **data,
    }

    await salvar_job(job)
    return job


async def salvar_job(job: dict) -> dict:
    job["atualizadoEm"] = now()

    directory = job_dir(job["protocolo"])
    directory.mkdir(parents=True, exist_ok=True)

    job_file(job["protocolo"]).write_text(
        json.dumps(encrypt_json(job), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return job


async def ler_job(protocolo: str) -> dict | None:
    try:
        raw = job_file(protocolo).read_text(encoding="utf-8")
        return decrypt_json(json.loads(raw))
    except Exception:
        return None


async def atualizar_job(protocolo: str, data: dict) -> dict:
    job = await ler_job(protocolo)

    if not job:
        raise RuntimeError(f"Job não encontrado: {protocolo}")

    job.update(data)

    return await salvar_job(job)
