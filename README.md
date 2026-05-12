# SERPRO Python PAdES Service

Serviço em **Python + FastAPI + pyHanko** para assinatura digital de PDFs no padrão **PAdES**, utilizando **SERPRO ID** com assinatura remota.

---

# ⚠ Requisito obrigatório

Este projeto deve ser executado com:

```text
Python 3.12
```

Atualmente algumas dependências do ecossistema de assinatura digital ainda não possuem compatibilidade estável com Python 3.14.

Não utilize Python 3.14 neste projeto.

---

# Visão geral do fluxo

```text
1. Cliente envia CPF + PDF Base64
2. Serviço gera protocolo
3. Serviço gera URL de autorização OAuth SERPRO ID
4. Titular autoriza no SERPRO
5. SERPRO chama o callback do serviço
6. Serviço troca o code por access_token
7. Serviço recupera o certificado do titular
8. pyHanko prepara a assinatura PAdES
9. Serviço envia o hash ao SERPRO com signature_format=RAW
10. SERPRO retorna a assinatura criptográfica
11. pyHanko monta o PDF PAdES
12. Serviço retorna o PDF assinado em Base64
```

---

# Tecnologias utilizadas

- Python 3.12
- FastAPI
- Uvicorn
- pyHanko
- httpx
- cryptography
- PM2
- Linux Ubuntu
- SERPRO ID
- PAdES / ICP-Brasil

---

# Instalação do zero

## 1. Instalar dependências básicas

```bash
sudo apt update
sudo apt install unzip curl openssl nodejs npm -y
sudo npm install -g pm2
```

---

## 2. Instalar UV

O projeto utiliza o UV para garantir o uso correto do Python 3.12.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env
```

Verifique:

```bash
uv --version
```

---

## 3. Instalar Python 3.12

```bash
uv python install 3.12
```

Verifique:

```bash
uv python list
```

---

## 4. Clonar o projeto

```bash
cd /opt

git clone https://github.com/SEU_USUARIO/serpro-python-pades-service.git

cd /opt/serpro-python-pades-service
```

---

## 5. Criar ambiente virtual Python

```bash
uv venv --python 3.12 .venv
source .venv/bin/activate
```

Confirme:

```bash
python --version
```

Resultado esperado:

```text
Python 3.12.x
```

---

## 6. Instalar dependências Python

```bash
uv pip install -r requirements.txt
```

---

# Configuração

## 1. Criar arquivo .env

```bash
cp .env.example .env
nano .env
```

Conteúdo:

```env
PORT=3333
HOST=0.0.0.0

MOCK_MODE=false

SERPRO_CLIENT_ID=SEU_CLIENT_ID
SERPRO_CLIENT_SECRET=SEU_CLIENT_SECRET

SERPRO_SCOPE=signature_session

SERPRO_AUTHORIZE_URL=https://serproid.serpro.gov.br/oauth/v0/oauth/authorize
SERPRO_TOKEN_URL=https://serproid.serpro.gov.br/oauth/v0/oauth/token
SERPRO_SIGNATURE_URL=https://serproid.serpro.gov.br/oauth/v0/oauth/signature
SERPRO_CERTIFICATE_URL=https://serproid.serpro.gov.br/oauth/v0/oauth/certificate-discovery

CALLBACK_URL=http://SEU_IP_OU_DOMINIO:3333/serpro/callback

HASH_ALGORITHM_OID=2.16.840.1.101.3.4.2.1
SERPRO_SIGNATURE_FORMAT=RAW

JOBS_DIR=/opt/serpro-python-pades-service/storage/jobs
SESSIONS_DIR=/opt/serpro-python-pades-service/storage/sessions

ENCRYPTION_KEY_BASE64=COLE_AQUI_A_CHAVE
```

---

## 2. Gerar chave AES-256

```bash
openssl rand -base64 32
```

Cole no `.env`:

```env
ENCRYPTION_KEY_BASE64=SUA_CHAVE
```

---

## 3. Criar diretórios

```bash
mkdir -p storage/jobs
mkdir -p storage/sessions
mkdir -p logs
```

---

# Teste manual

```bash
source .venv/bin/activate

uvicorn app.main:app --host 0.0.0.0 --port 3333
```

Em outro terminal:

```bash
curl http://localhost:3333/
```

Resposta esperada:

```json
{
  "service": "serpro-python-pades-service",
  "status": "online",
  "signatureFormat": "RAW"
}
```

---

# PM2

## ecosystem.config.cjs

```javascript
module.exports = {
  apps: [
    {
      name: "serpro-python-pades-service",
      script: ".venv/bin/uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 3333",
      cwd: "/opt/serpro-python-pades-service",
      interpreter: "none",
      autorestart: true,
      watch: false,
      max_memory_restart: "500M"
    }
  ]
};
```

⚠ Importantíssimo:

```javascript
interpreter: "none"
```

Sem isso o PM2 tenta executar `uvicorn` como JavaScript.

---

## Subir serviço

```bash
pm2 delete serpro-python-pades-service || true
pm2 start ecosystem.config.cjs --update-env
pm2 save
```

Logs:

```bash
pm2 logs serpro-python-pades-service
```

---

# Endpoints

## Status

```http
GET /
```

---

## Criar assinatura

```http
POST /assinaturas
Content-Type: application/json
```

Body:

```json
{
  "cpf": "00000000000",
  "alias": "Contrato Teste",
  "pdfBase64": "JVBERi0x..."
}
```

---

## Consultar assinatura

```http
GET /assinaturas/{protocolo}
```

---

# GitHub

Nunca envie:

```text
.env
.venv/
storage/jobs/*
storage/sessions/*
logs/*
```

`.gitignore`:

```gitignore
.env
__pycache__/
*.pyc
.venv/
storage/jobs/*
storage/sessions/*
logs/*
!storage/jobs/.gitkeep
!storage/sessions/.gitkeep
!logs/.gitkeep
```

---

# Troubleshooting

## PM2 mostra “Unexpected identifier 'uvicorn'”

Falta:

```javascript
interpreter: "none"
```

---

## pydantic-core falhando

Você provavelmente está usando Python 3.14.

Confira:

```bash
python --version
```

O correto é:

```text
Python 3.12.x
```

---

# Produção

Recomendado:

- HTTPS com Nginx
- Reverse proxy
- Backup seguro
- Limpeza automática de jobs antigos
- Monitoramento de logs
- Assinatura visual
- Carimbo do tempo TSA
- PAdES-LT/LTV

---

# Licença

Sugestão:

```text
MIT
```

