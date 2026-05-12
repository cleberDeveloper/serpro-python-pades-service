# SERPRO Python PAdES Service

Serviço em **Python + FastAPI + pyHanko** para assinatura digital de PDFs no padrão **PAdES**, utilizando **SERPRO ID** com assinatura remota.

O objetivo deste projeto é permitir que uma aplicação envie:

```json
{
  "cpf": "CPF_DO_TITULAR",
  "pdfBase64": "PDF_EM_BASE64",
  "alias": "Nome do documento"
}
```

e receba posteriormente o PDF assinado digitalmente em Base64.

---

## Visão geral do fluxo

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

## Tecnologias utilizadas

- Python 3
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

## Estrutura do projeto

```text
serpro-python-pades-service/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── serpro_client.py
│   ├── pades_signer.py
│   ├── job_store.py
│   ├── session_store.py
│   ├── crypto_store.py
│   ├── pkce.py
│   └── logger.py
├── storage/
│   ├── jobs/
│   └── sessions/
├── logs/
├── requirements.txt
├── ecosystem.config.cjs
├── .env.example
├── .gitignore
└── README.md
```

---

# 1. Pré-requisitos

Servidor Linux Ubuntu com acesso SSH.

Instale os pacotes básicos:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip unzip curl openssl -y
```

Se for usar PM2:

```bash
sudo apt install nodejs npm -y
sudo npm install -g pm2
```

Verifique:

```bash
python3 --version
pip3 --version
pm2 --version
```

---

# 2. Baixar ou clonar o projeto

Exemplo usando Git:

```bash
cd /opt
git clone https://github.com/SEU_USUARIO/serpro-python-pades-service.git
cd /opt/serpro-python-pades-service
```

Ou, se estiver usando ZIP:

```bash
cd /opt
unzip serpro-python-pades-service-final.zip -d /opt
mv /opt/serpro-python-pades-service-final /opt/serpro-python-pades-service
cd /opt/serpro-python-pades-service
```

---

# 3. Criar ambiente virtual Python

```bash
cd /opt/serpro-python-pades-service

python3 -m venv .venv
source .venv/bin/activate
```

Atualize o `pip`:

```bash
pip install --upgrade pip
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

---

# 4. Criar arquivo `.env`

Este arquivo contém configurações sensíveis e **não deve ser enviado ao GitHub**.

Crie a partir do exemplo:

```bash
cp .env.example .env
nano .env
```

Se o arquivo `.env.example` não existir, crie manualmente:

```bash
nano .env
```

Conteúdo base:

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

ENCRYPTION_KEY_BASE64=COLE_AQUI_A_CHAVE_BASE64_DE_32_BYTES
```

---

# 5. Gerar chave de criptografia

O serviço usa AES-256-GCM para criptografar os arquivos de sessão e jobs.

Gere uma chave:

```bash
openssl rand -base64 32
```

Copie o resultado e coloque no `.env`:

```env
ENCRYPTION_KEY_BASE64=SUA_CHAVE_GERADA
```

A chave precisa representar exatamente **32 bytes**.

---

# 6. Configurações importantes do SERPRO

## 6.1 Client ID e Client Secret

Preencha no `.env`:

```env
SERPRO_CLIENT_ID=SEU_CLIENT_ID
SERPRO_CLIENT_SECRET=SEU_CLIENT_SECRET
```

## 6.2 Callback URL

Configure no SERPRO a mesma URL informada no `.env`:

```env
CALLBACK_URL=http://SEU_IP_OU_DOMINIO:3333/serpro/callback
```

Exemplo:

```env
CALLBACK_URL=http://69.162.109.68:3333/serpro/callback
```

Em produção, recomenda-se usar HTTPS:

```env
CALLBACK_URL=https://seu-dominio.com.br/serpro/callback
```

## 6.3 Formato de assinatura

Este projeto usa:

```env
SERPRO_SIGNATURE_FORMAT=RAW
```

O SERPRO assina o hash solicitado e o **pyHanko monta o PDF PAdES**.

Não altere para `CMS` neste projeto.

---

# 7. Criar pastas necessárias

```bash
mkdir -p storage/jobs
mkdir -p storage/sessions
mkdir -p logs
```

---

# 8. Testar manualmente

Ative o ambiente virtual:

```bash
cd /opt/serpro-python-pades-service
source .venv/bin/activate
```

Execute:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 3333
```

Em outro terminal, teste:

```bash
curl http://localhost:3333/
```

Resposta esperada:

```json
{
  "service": "serpro-python-pades-service",
  "status": "online",
  "signatureFormat": "RAW",
  "scope": "signature_session"
}
```

Para parar o teste manual:

```bash
CTRL + C
```

---

# 9. Rodar com PM2

O projeto inclui o arquivo:

```text
ecosystem.config.cjs
```

Conteúdo recomendado:

```javascript
module.exports = {
  apps: [
    {
      name: "serpro-python-pades-service",
      script: ".venv/bin/uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 3333",
      cwd: "/opt/serpro-python-pades-service",
      interpreter: "none",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
      error_file: "./logs/error.log",
      out_file: "./logs/out.log",
      log_file: "./logs/combined.log",
      time: true
    }
  ]
};
```

Atenção ao item:

```javascript
interpreter: "none"
```

Sem isso, o PM2 pode tentar executar o `uvicorn` como se fosse JavaScript/Node.

Suba o serviço:

```bash
cd /opt/serpro-python-pades-service

pm2 delete serpro-python-pades-service || true
pm2 start ecosystem.config.cjs --update-env
pm2 save
```

Ver logs:

```bash
pm2 logs serpro-python-pades-service
```

Ver status:

```bash
pm2 list
```

---

# 10. Inicializar automaticamente após reboot

Execute:

```bash
pm2 startup
```

O PM2 vai exibir um comando. Copie e execute exatamente o comando gerado.

Depois:

```bash
pm2 save
```

---

# 11. Endpoints da API

## 11.1 Verificar status

```http
GET /
```

Exemplo:

```bash
curl http://localhost:3333/
```

---

## 11.2 Criar solicitação de assinatura

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

Exemplo com curl:

```bash
curl -X POST http://localhost:3333/assinaturas \
  -H "Content-Type: application/json" \
  -d '{
    "cpf": "00000000000",
    "alias": "Contrato Teste",
    "pdfBase64": "JVBERi0x..."
  }'
```

Resposta esperada:

```json
{
  "sucesso": true,
  "protocolo": "uuid-do-protocolo",
  "status": "AGUARDANDO_AUTORIZACAO",
  "urlAutorizacao": "https://serproid.serpro.gov.br/..."
}
```

Abra a `urlAutorizacao` no navegador para autorizar.

---

## 11.3 Callback SERPRO

```http
GET /serpro/callback?code=...&state=...
```

Este endpoint é chamado automaticamente pelo SERPRO após autorização.

---

## 11.4 Consultar status da assinatura

```http
GET /assinaturas/{protocolo}
```

Exemplo:

```bash
curl http://localhost:3333/assinaturas/SEU_PROTOCOLO
```

Enquanto processa:

```json
{
  "sucesso": true,
  "status": "ASSINANDO_PDF",
  "pdfAssinadoBase64": null
}
```

Quando finalizar:

```json
{
  "sucesso": true,
  "status": "ASSINADO",
  "pdfAssinadoBase64": "JVBERi0x..."
}
```

---

# 12. Teste com Postman

## Criar assinatura

Método:

```text
POST
```

URL:

```text
http://SEU_IP:3333/assinaturas
```

Headers:

```text
Content-Type: application/json
```

Body:

```json
{
  "cpf": "CPF_DO_TITULAR",
  "alias": "Contrato Teste",
  "pdfBase64": "BASE64_DO_PDF"
}
```

Depois:

1. Copie a `urlAutorizacao`
2. Abra no navegador
3. Autorize no SERPRO
4. Consulte o protocolo:

```text
GET http://SEU_IP:3333/assinaturas/PROTOCOLO
```

---

# 13. Gerar Base64 de um PDF para teste

No Linux:

```bash
base64 -w 0 arquivo.pdf > arquivo_base64.txt
```

Copie o conteúdo de:

```text
arquivo_base64.txt
```

e use no campo:

```json
"pdfBase64": "..."
```

---

# 14. Decodificar PDF assinado retornado

Se a API retornar `pdfAssinadoBase64`, você pode salvar como arquivo:

```bash
echo "BASE64_AQUI" | base64 -d > assinado.pdf
```

---

# 15. Segurança para GitHub

Nunca envie:

```text
.env
storage/jobs/*
storage/sessions/*
logs/*
.venv/
```

O `.gitignore` deve conter:

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

Antes do `git push`, confira:

```bash
git status
```

Se o `.env` aparecer, remova do controle:

```bash
git rm --cached .env
```

Verifique se há segredos no projeto:

```bash
grep -R "SERPRO_CLIENT_SECRET\\|SERPRO_CLIENT_ID\\|ENCRYPTION_KEY_BASE64" . --exclude-dir=.git --exclude=.env
```

O ideal é aparecer somente no `.env.example`, com valores fictícios.

---

# 16. Troubleshooting

## 16.1 PM2 mostra `Unexpected identifier 'uvicorn'`

O PM2 está tentando executar o `uvicorn` como JavaScript.

Corrija o `ecosystem.config.cjs`:

```javascript
interpreter: "none"
```

Depois:

```bash
pm2 delete serpro-python-pades-service || true
pm2 start ecosystem.config.cjs --update-env
```

---

## 16.2 Erro de variável de ambiente ausente

Confira o `.env`:

```bash
cat .env
```

Teste se está no diretório correto:

```bash
pwd
```

Deve estar em:

```text
/opt/serpro-python-pades-service
```

---

## 16.3 Erro na chave de criptografia

Mensagem comum:

```text
ENCRYPTION_KEY_BASE64 precisa representar exatamente 32 bytes
```

Gere novamente:

```bash
openssl rand -base64 32
```

Atualize no `.env`.

---

## 16.4 Erro ao instalar dependências Python

Atualize o `pip`:

```bash
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 16.5 Serviço não responde na porta 3333

Confira se está rodando:

```bash
pm2 list
pm2 logs serpro-python-pades-service
```

Confira se a porta está aberta:

```bash
ss -tulpn | grep 3333
```

Se usar firewall:

```bash
sudo ufw allow 3333/tcp
```

---

# 17. Observações de produção

Recomendado para produção:

- usar HTTPS com Nginx reverse proxy
- não expor porta 3333 diretamente
- proteger o `.env`
- usar backups seguros
- monitorar logs
- validar PDFs assinados no ITI
- considerar fila assíncrona para alto volume
- implementar limpeza de jobs antigos
- implementar assinatura visual
- implementar carimbo do tempo TSA para PAdES-LT/LTV

---

# 18. Licença

Defina a licença conforme sua necessidade.

Sugestão para projeto open source:

```text
MIT
```

---

# 19. Aviso

Este projeto é um exemplo técnico de integração com SERPRO ID para assinatura digital PAdES.  
Antes de uso em produção, valide juridicamente, tecnicamente e operacionalmente o fluxo conforme os requisitos do seu negócio.
