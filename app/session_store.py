import json
from datetime import datetime, timezone

from .config import SESSIONS_DIR
from .crypto_store import encrypt_json, decrypt_json, sha256_hex


def session_file(cpf: str):
    clean = "".join(ch for ch in str(cpf or "") if ch.isdigit())
    return SESSIONS_DIR / f"{sha256_hex(clean)}.json.enc"


async def salvar_sessao(cpf: str, data: dict) -> dict:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "cpf": cpf,
        "criadoEm": datetime.now(timezone.utc).isoformat(),
        **data,
    }

    session_file(cpf).write_text(
        json.dumps(encrypt_json(payload), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return payload


async def ler_sessao_valida(cpf: str) -> dict | None:
    try:
        payload = decrypt_json(json.loads(session_file(cpf).read_text(encoding="utf-8")))

        expires_at = payload.get("expiresAt")

        if not expires_at:
            return None

        if datetime.fromisoformat(expires_at) <= datetime.now(timezone.utc):
            return None

        return payload

    except Exception:
        return None
