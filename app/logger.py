import json
from datetime import datetime, timezone


def mask_cpf(cpf: str) -> str:
    value = "".join(ch for ch in str(cpf or "") if ch.isdigit())
    if len(value) < 5:
        return "***"
    return f"{value[:3]}***{value[-2:]}"


def log(protocolo, etapa, mensagem, extra=None):
    payload = {
        "dataHora": datetime.now(timezone.utc).isoformat(),
        "protocolo": protocolo,
        "etapa": etapa,
        "mensagem": mensagem,
    }

    if extra is not None:
        payload["extra"] = extra

    print(json.dumps(payload, ensure_ascii=False), flush=True)


def log_error(protocolo, etapa, erro):
    payload = {
        "dataHora": datetime.now(timezone.utc).isoformat(),
        "protocolo": protocolo,
        "etapa": etapa,
        "erro": str(erro),
    }

    print(json.dumps(payload, ensure_ascii=False), flush=True)
