import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Variável de ambiente não configurada: {name}")
    return value


PORT = int(os.getenv("PORT", "3333"))
HOST = os.getenv("HOST", "0.0.0.0")
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

SERPRO_CLIENT_ID = env("SERPRO_CLIENT_ID")
SERPRO_CLIENT_SECRET = env("SERPRO_CLIENT_SECRET")
SERPRO_SCOPE = os.getenv("SERPRO_SCOPE", "signature_session")

SERPRO_AUTHORIZE_URL = env("SERPRO_AUTHORIZE_URL")
SERPRO_TOKEN_URL = env("SERPRO_TOKEN_URL")
SERPRO_SIGNATURE_URL = env("SERPRO_SIGNATURE_URL")
SERPRO_CERTIFICATE_URL = env("SERPRO_CERTIFICATE_URL")

CALLBACK_URL = env("CALLBACK_URL").split("?")[0].strip()

HASH_ALGORITHM_OID = os.getenv("HASH_ALGORITHM_OID", "2.16.840.1.101.3.4.2.1")
SERPRO_SIGNATURE_FORMAT = os.getenv("SERPRO_SIGNATURE_FORMAT", "RAW")

JOBS_DIR = Path(os.getenv("JOBS_DIR", "./storage/jobs"))
SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR", "./storage/sessions"))

ENCRYPTION_KEY_BASE64 = env("ENCRYPTION_KEY_BASE64")
