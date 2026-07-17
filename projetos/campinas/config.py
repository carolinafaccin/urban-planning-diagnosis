"""
config.py — parâmetros do projeto Campinas (área de estudo em Campinas/SP)
-------------------------------------------------------------------------
Produto: diagnóstico territorial urbanístico. Os scripts em ../../scripts/
são genéricos: nenhuma coordenada, nome de município ou CRS deve ficar
hard-coded neles — tudo referencia este arquivo. Único arquivo a editar
para replicar o diagnóstico em outra cidade/bairro.

Para um novo projeto (outra cidade, bairro ou loteamento): copie esta
pasta para projetos/<cidade>/, ajuste os valores abaixo e rode os scripts a
partir do diretório do novo projeto, ex.:

    cd projetos/<cidade>
    python ../../scripts/pipeline/01_download_osm.py
"""

import json
from pathlib import Path

# ----------------------------------------------------------------------
# Identificação do projeto
# ----------------------------------------------------------------------
PROJECT_NAME = "bassoli_campinas"
MUNICIPIO    = "Campinas"
UF           = "SP"
IBGE_COD_MUN = "3509502"

# ----------------------------------------------------------------------
# Área de estudo
# ----------------------------------------------------------------------
# Área de estudo em Campinas/SP. Delimitada à mão no Mapbox Location Helper
# (labs.mapbox.com/location-helper), cobrindo ~2,0 km (L-O) x ~2,2 km (N-S).
BBOX = {
    "north": -22.95058,
    "south": -22.97025,
    "east":  -47.18615,
    "west":  -47.20624,
}

CRS_PROJETO = "EPSG:31983"  # SIRGAS 2000 / UTM zona 23S — CRS de saída do projeto
CRS_WGS84   = "EPSG:4326"   # CRS de entrada da maioria das fontes (OSM, IBGE, GEE)

# Período de referência para a temperatura de superfície (LST)
LST_PERIODO = ("2020-01-01", "2025-01-01")

# Ponto-âncora para análises de caminhabilidade (equipamento de referência).
# TODO: ESTE VALOR ESTÁ ERRADO — cai fora do BBOX acima (chute antigo, feito
# junto com a bbox anterior que estava deslocada ~7 km). Precisa da coordenada
# real da âncora antes de rodar o 11_analises.py. Usado só lá; não afeta 01-10.
ANCORA_NOME  = "âncora"
ANCORA_COORD = (-22.888, -47.163)  # (lat, lon), WGS84
RAIO_ANCORA  = 450  # metros — referência de caminhabilidade

# ----------------------------------------------------------------------
# Edificações (Overture Maps) — usado no 03_overture_edificacoes.py
# ----------------------------------------------------------------------
# Confiança mínima de detecção para manter uma edificação de fonte ML
# (Google/Microsoft Open Buildings). Edificações do OpenStreetMap são
# mantidas independentemente (mapeamento humano, sem score de ML).
OVERTURE_CONF_MIN = 0.75

# ----------------------------------------------------------------------
# Mapa síntese (H3) — usado nos scripts 05_h3_dasimetrico.py e 11_analises.py
# ----------------------------------------------------------------------
H3_RESOLUCAO = 10  # ~15.000 m² por hexágono, ~123 m de lado

# Pesos do score de prioridade (devem somar 1.0)
H3_PESOS = {
    "lst_mean":        0.30,  # exposição térmica
    "deficit_verde":   0.30,  # déficit de cobertura vegetal
    "pct_impermeavel": 0.15,  # impermeabilização do solo
    "vuln_social":     0.15,  # vulnerabilidade socioeconômica
    "deficit_arb":     0.10,  # domicílios sem arborização viária (IBGE)
}

# ----------------------------------------------------------------------
# Diretórios
# ----------------------------------------------------------------------
# O repositório git guarda só código (scripts + este config.py).
#
# raw_dir (RAW_CATALOG) é o catálogo GERAL de dados brutos do computador
# — organizado por FONTE (osm/, ibge/, gee/...), não por projeto, e
# compartilhado entre todos os projetos. Documentado em <raw_dir>/README.md
# e em um README.md por fonte. Os scripts LEEM desse catálogo; não criam
# pastas novas de projeto dentro dele. Quando algum script precisa
# cachear/gravar algo bruto (ex.: respostas da API Overpass), usa a
# subpasta que a própria fonte já convenciona (ex.: osm/overpass_cache/),
# nunca uma pasta nova nomeada com o projeto.
#
# data_dir (DATA_DIR) é onde ficam os OUTPUTS de cada projeto — geojsons
# desenhados à mão, arquivos fornecidos pela prefeitura, dados processados e o
# GeoPackage final. Aqui sim é namespaced por projeto.
#
# Ambos os caminhos vêm de config/config.local.json (fora do git).

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

# Catálogo geral de dados brutos (leitura) — NÃO criar pastas de projeto aqui
RAW_CATALOG = Path(_paths["raw_dir"])

# Raiz de todos os dados deste projeto (escrita) — fora do git
DATA_DIR = Path(_paths["data_dir"]) / MUNICIPIO.lower() / PROJECT_NAME

# Geojsons desenhados à mão (área do projeto, camadas locais...)
LOCAL_DATA_DIR = DATA_DIR / "raw" / "local"
# Arquivos fornecidos pela prefeitura (camadas solicitadas)
SOLICITADOS_DATA_DIR = DATA_DIR / "raw" / "solicitados"
# Saídas processadas (rasters de LST, cobertura do solo, estatísticas...)
PROCESSED_DIR = DATA_DIR / "processed"

GPKG_PATH = DATA_DIR / f"{PROJECT_NAME}.gpkg"

# Saída do relatório estático (HTML + imagens) — fora do git, deploy-agnóstico.
# Aponte o Cloudflare/host para esta pasta. Se um dia usar GitHub Pages, mude
# para uma pasta docs/ dentro do repo.
REPORT_DIR = DATA_DIR / "report"

for _dir in (DATA_DIR, LOCAL_DATA_DIR, SOLICITADOS_DATA_DIR, PROCESSED_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
