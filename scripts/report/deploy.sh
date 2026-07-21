#!/usr/bin/env bash
#
# deploy.sh
# ---------
# O que faz   : Publica o relatório estático no Cloudflare Pages com um comando.
#               Faz upload direto da pasta REPORT_DIR via `wrangler pages deploy`
#               (nada passa pelo git — o relatório é output, fica fora do repo).
# Uso         : a partir da pasta do projeto (onde está o config.py):
#                 cd projetos/campinas
#                 ../../scripts/report/deploy.sh            # publica o que já foi gerado
#                 ../../scripts/report/deploy.sh --build    # regenera e depois publica
# Requer      : wrangler instalado e logado (`wrangler login`); relatório já
#               gerado por scripts/report/generate_report.py (ou use --build).
# Config      : lê REPORT_DIR, PAGES_PROJECT e PAGES_BRANCH do config.py do
#               projeto. Genérico — nada de nome/caminho hard-coded. Para
#               publicar outro projeto, rode a partir da pasta dele; só o
#               config.py muda (tipicamente troca só o PAGES_BRANCH).
# Privacidade : quem restringe o acesso (allowlist de emails) é o Cloudflare
#               Access, configurado uma vez no painel Zero Trust — este script
#               não mexe nisso; redeploys reusam a mesma URL e o mesmo Access.

set -euo pipefail

# Precisa rodar da pasta do projeto (mesma convenção dos scripts do pipeline:
# o config.py é resolvido pelo diretório de trabalho atual).
if [[ ! -f "config.py" ]]; then
  echo "erro: rode a partir da pasta do projeto (onde está o config.py)." >&2
  echo "  ex.: cd projetos/campinas && ../../scripts/report/deploy.sh" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --build: regenera o relatório antes de publicar.
if [[ "${1:-}" == "--build" ]]; then
  echo "==> gerando relatório..."
  python "${SCRIPT_DIR}/generate_report.py"
fi

# Lê os três parâmetros do config.py do projeto (fonte única da verdade).
# Um valor por linha — REPORT_DIR pode conter espaços (ex.: Google Drive).
{ read -r REPORT_DIR; read -r PAGES_PROJECT; read -r PAGES_BRANCH; } < <(python - <<'PY'
import sys
sys.path.insert(0, ".")
from config import REPORT_DIR, PAGES_PROJECT, PAGES_BRANCH
print(REPORT_DIR)
print(PAGES_PROJECT)
print(PAGES_BRANCH)
PY
)

if [[ ! -d "${REPORT_DIR}" || ! -f "${REPORT_DIR}/index.html" ]]; then
  echo "erro: relatório não encontrado em ${REPORT_DIR}" >&2
  echo "  gere antes com: python ${SCRIPT_DIR}/generate_report.py" >&2
  echo "  (ou rode este script com --build)" >&2
  exit 1
fi

echo "==> publicando ${REPORT_DIR}"
echo "    projeto Pages: ${PAGES_PROJECT}  (branch: ${PAGES_BRANCH})"
echo "    URL: https://${PAGES_BRANCH}.${PAGES_PROJECT}.pages.dev"
wrangler pages deploy "${REPORT_DIR}" --project-name "${PAGES_PROJECT}" --branch "${PAGES_BRANCH}"
