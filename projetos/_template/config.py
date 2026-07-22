"""
config.py — TEMPLATE de projeto novo (gerado por scripts/novo_projeto.py)
--------------------------------------------------------------------------
Produto: diagnóstico territorial urbanístico. Os scripts em ../../scripts/
são genéricos: nenhuma coordenada, nome de município ou CRS deve ficar
hard-coded neles — tudo referencia este arquivo. Único arquivo a editar
para replicar o diagnóstico em outra cidade/bairro.

Este arquivo tem 3 categorias de campo:
1. Preenchidos automaticamente por scripts/novo_projeto.py (identificação
   básica) — confira, mas normalmente não precisam de edição manual extra.
2. Marcados "# TODO(scaffold)" — exigem decisão/dado humano antes de rodar
   o pipeline (BBOX, pesos do score). O pipeline AVISA e segue sem travar
   quando um desses está ausente — mas os resultados vão refletir a lacuna.
3. Nunca editados à mão em nenhum projeto: RAW_CATALOG, DATA_DIR, REPO_ROOT
   e os demais caminhos derivados no fim do arquivo — resolvidos por
   código a partir de config/config.local.json.

Depois de preencher, rode a partir da pasta do projeto:

    cd projetos/<slug>
    python ../../scripts/pipeline/run.py
"""

import json
import re
import unicodedata
from pathlib import Path


def _slugificar(texto):
    """Sem acentos/espaços — usado pra nomear pastas/URLs (MUNICIPIO_SLUG).
    MUNICIPIO.lower() sozinho quebra para município com espaço no nome
    (ex. "São José dos Campos"); só funcionava em Campinas por acidente
    (nome de uma palavra só)."""
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")

# ----------------------------------------------------------------------
# Identificação do projeto — preenchido por scripts/novo_projeto.py
# ----------------------------------------------------------------------
PROJECT_NAME = "__PROJECT_NAME__"
MUNICIPIO    = "__MUNICIPIO__"
UF           = "__UF__"
IBGE_COD_MUN = "__IBGE_COD_MUN__"

# Título de exibição do diagnóstico no site (Hero, TopBar, <title> da aba).
TITULO_PROJETO = "__TITULO_PROJETO__"

# Opcional: nome (no GeoPackage final) de um sub-recorte de intervenção
# dentro da área de estudo (ex.: um loteamento específico, quando a área de
# estudo é maior que o recorte de intervenção em si). Ingerido via geojson
# solto em raw/local/ (ver dados_locais.py) — o nome da camada é o stem do
# arquivo. None quando a área de estudo já É o recorte de intervenção
# (caso mais comum).
CAMADA_INTERVENCAO = None

# Cloudflare Pages: um único project "guarda-chuva" (produto) com um branch
# por projeto/bbox. Branch deploys viram <PAGES_BRANCH>.<PAGES_PROJECT>.pages.dev
# — não precisa criar um Pages project novo a cada cidade/bairro. Derivado
# do slug por padrão; troque se quiser um subdomínio diferente do slug.
PAGES_PROJECT = "diagnostico-urbanistico"
PAGES_BRANCH  = "__PAGES_BRANCH__"

# ----------------------------------------------------------------------
# Área de estudo — TODO(scaffold): decisão humana, não inventar
# ----------------------------------------------------------------------
# TODO(scaffold): desenhe o bbox da área de estudo (ex.: no geojson.io) e
# preencha os 4 vértices abaixo, em graus decimais (WGS84).
BBOX = {
    "north": 0.0,
    "south": 0.0,
    "east":  0.0,
    "west":  0.0,
}

CRS_PROJETO = "EPSG:31983"  # TODO(scaffold): troque para a projeção UTM correta da região (SIRGAS 2000 / UTM apropriado)
CRS_WGS84   = "EPSG:4326"   # CRS de entrada da maioria das fontes (OSM, IBGE, GEE) — não mexer

# Período de referência para a temperatura de superfície (LST)
LST_PERIODO = ("2020-01-01", "2025-01-01")

# ----------------------------------------------------------------------
# Edificações (Overture Maps) — usado no overture_edificacoes.py
# ----------------------------------------------------------------------
OVERTURE_CONF_MIN = 0.75

# ----------------------------------------------------------------------
# APP de córregos (Código Florestal) — usado no app_corregos.py
# ----------------------------------------------------------------------
# Largura mínima de Área de Preservação Permanente (Lei 12.651/2012, Art. 4º,
# inciso I). 30 m é a faixa para cursos d'água com menos de 10 m de largura
# — ajuste se souber a largura real do curso d'água do seu projeto
# (10-50m -> 50m, 50-200m -> 100m, 200-600m -> 200m, >600m -> 500m).
APP_LARGURA_MIN = 30  # metros

# ----------------------------------------------------------------------
# Mapa síntese (H3) — usado nos scripts h3_dasimetrico.py e analises.py
# ----------------------------------------------------------------------
H3_RESOLUCAO = 10  # ~15.000 m² por hexágono, ~123 m de lado

# Pesos do score de prioridade (devem somar 1.0). Valores padrão iguais aos
# do projeto de referência (Campinas) — reavalie se fazem sentido pro seu
# território antes de rodar de verdade.
H3_PESOS = {
    "lst_mean":        0.30,  # exposição térmica
    "deficit_verde":   0.30,  # déficit de cobertura vegetal
    "pct_impermeavel": 0.15,  # impermeabilização do solo
    "vuln_social":     0.15,  # vulnerabilidade socioeconômica
    "deficit_arb":     0.10,  # domicílios sem arborização viária (IBGE)
}

# ----------------------------------------------------------------------
# Dados municipais (prefeitura) — usado no dados_municipais.py e no
# indicadores_municipais.py
# ----------------------------------------------------------------------
# Dict vazio por padrão: pipeline roda idêntico ao comportamento sem dados
# municipais (opt-in, nunca obrigatório). Preencha só depois de catalogar e
# baixar o portal da prefeitura (ver procedimento em CLAUDE.md, seção
# "Procedimento para catalogar/baixar o portal de uma NOVA cidade").
MUNICIPIO_SLUG = _slugificar(MUNICIPIO)

CAMADAS_MUNICIPAIS = {}

# ----------------------------------------------------------------------
# Diretórios — NUNCA editar à mão (resolvidos por código)
# ----------------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent


def _find_repo_root(start):
    """Sobe a partir de `start` até achar a raiz do repo (pasta que contém
    config/config.local.json). Robusto a mudanças na profundidade da pasta
    do projeto — não depende de um índice fixo de parents."""
    for parent in (start, *start.parents):
        if (parent / "config" / "config.local.json").exists():
            return parent
    raise FileNotFoundError(
        "Não encontrei config/config.local.json subindo a partir de "
        f"{start}. Copie config/config.example.json para "
        "config/config.local.json e preencha data_dir e raw_dir."
    )


REPO_ROOT = _find_repo_root(PROJECT_DIR)

with open(REPO_ROOT / "config" / "config.local.json", encoding="utf-8") as f:
    _paths = json.load(f)

RAW_CATALOG = Path(_paths["raw_dir"])
DATA_DIR = Path(_paths["data_dir"]) / MUNICIPIO_SLUG / PROJECT_NAME
MUNICIPAIS_RAW_DIR = RAW_CATALOG / "prefeituras_municipais" / MUNICIPIO_SLUG / "t0"
LOCAL_DATA_DIR = DATA_DIR / "raw" / "local"
SOLICITADOS_DATA_DIR = DATA_DIR / "raw" / "solicitados"
PROCESSED_DIR = DATA_DIR / "processed"
GPKG_PATH = DATA_DIR / f"{PROJECT_NAME}.gpkg"
REPORT_DIR = DATA_DIR / "report"

for _dir in (DATA_DIR, LOCAL_DATA_DIR, SOLICITADOS_DATA_DIR, PROCESSED_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
