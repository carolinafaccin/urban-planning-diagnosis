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

# Cloudflare Pages: um único project "guarda-chuva" (produto) com um branch
# por projeto/bbox. Branch deploys viram <PAGES_BRANCH>.<PAGES_PROJECT>.pages.dev
# — não precisa criar um Pages project novo a cada cidade/bairro.
# Usado por scripts/report/deploy.sh.
PAGES_PROJECT = "diagnostico-urbanistico"
PAGES_BRANCH  = "bassoli"

# ----------------------------------------------------------------------
# Área de estudo
# ----------------------------------------------------------------------
# Área de estudo em Campinas/SP. Redesenhada em 2026-07-21 (2ª versão) para
# conter `area_de_projeto.geojson` com folga em todos os lados — a bbox
# anterior cortava ~77 m da borda sul da área de projeto. Cobre ~2,4 km (L-O)
# x ~2,6 km (N-S). Vértices em raw/local/bouding-box_vertices.geojson.
BBOX = {
    "north": -22.950285,
    "south": -22.973754,
    "east":  -47.185533,
    "west":  -47.212916,
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
# APP de córregos (Código Florestal) — usado no 03c_app_corregos.py
# ----------------------------------------------------------------------
# Largura mínima de Área de Preservação Permanente (Lei 12.651/2012, Art. 4º,
# inciso I), medida a partir da hidrografia disponível (municipal, senão
# OSM). 30 m é a faixa para cursos d'água com menos de 10 m de largura — o
# caso mais comum em córregos urbanos como o Itajaí. Ajuste se souber a
# largura real do curso d'água do seu projeto (10-50m -> 50m, 50-200m ->
# 100m, 200-600m -> 200m, >600m -> 500m).
APP_LARGURA_MIN = 30  # metros

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
# Dados municipais (prefeitura) — usado no 03b_dados_municipais.py e no
# 06b_indicadores_municipais.py
# ----------------------------------------------------------------------
# Preferir dado municipal quando existir e for mais preciso; fallback para
# nacional/global quando faltar ou tiver baixa qualidade (ver seção
# "Convenções de dados municipais" no CLAUDE.md). Edificações, viário
# (topologia) e censo NUNCA entram aqui — são sempre nacionais/globais.
#
# MUNICIPIO_SLUG localiza a pasta deste município dentro do catálogo geral
# raw_dir/prefeituras_municipais/<slug>/t0/ (mesma convenção de osm/, ibge/...
# — catalogado por FONTE, não por projeto).
MUNICIPIO_SLUG = MUNICIPIO.lower()

# generic_name -> {"arquivo": stem do shapefile em
# raw_dir/prefeituras_municipais/<slug>/t0/, "indicador_score": None ou a
# chave de H3_PESOS que esta camada alimenta como fallback (1ª fonte
# existente vence, resolvida em 11_analises.py::INDICADORES)}.
# Dict vazio (cidade sem portal municipal utilizável) faz o pipeline seguir
# idêntico ao comportamento sem dados municipais — nada aqui é obrigatório.
#
# Fonte: raw_dir/prefeituras_municipais/campinas/README.md (proveniência
# completa, datasets sem link de download e falhas de servidor conhecidas).
CAMADAS_MUNICIPAIS = {
    # --- categoria 2: fallback de indicador do score ---
    "areas_verdes":       dict(arquivo="areas_verdes", indicador_score="deficit_verde"),
    "bosques_parques":    dict(arquivo="bosques_parques", indicador_score="deficit_verde"),
    "vegetacao_natural":  dict(arquivo="vegetacao_natural", indicador_score="deficit_verde"),

    # --- categoria 1: enriquecimento de atributo sobre camada global (nunca
    # substitui a topologia OSM do viário) ---
    "classificacao_viaria": dict(arquivo="classificacao_viaria", indicador_score=None),

    # --- categoria 3: aditivo, sem equivalente global no pipeline hoje ---
    "administracoes_regionais":    dict(arquivo="administracoes_regionais", indicador_score=None),
    "bacias_hidrograficas":        dict(arquivo="bacias_hidrograficas", indicador_score=None),
    "hidrografia":                 dict(arquivo="hidrografia_igc_adaptada", indicador_score=None),
    "hidrografia_lagos":           dict(arquivo="hidrografia_lagos_igc_adaptada", indicador_score=None),
    "mananciais":                  dict(arquivo="mananciais", indicador_score=None),
    "limite_municipal":            dict(arquivo="limite_municipal", indicador_score=None),
    "distritos":                   dict(arquivo="distritos", indicador_score=None),
    "loteamentos":                 dict(arquivo="loteamentos", indicador_score=None),
    "eixos_logradouros":           dict(arquivo="eixos_logradouros", indicador_score=None),
    "unidades_conservacao":        dict(arquivo="unidades_conservacao", indicador_score=None),
    "zonas_amortecimento_uc":      dict(arquivo="zonas_amortecimento_unidades_conservacao", indicador_score=None),
    "corredores_ecologicos":       dict(arquivo="corredores_ecologicos", indicador_score=None),
    "parques_lineares_plano_verde": dict(arquivo="parques_lineares_plano_verde", indicador_score=None),
    "programa_sbn_infraestrutura_verde": dict(arquivo="programa_sbn_infraestrutura_verde", indicador_score=None),
    "permeabilidade_lei_207_2018": dict(arquivo="permeabilidade_lei_207_2018", indicador_score=None),
    "equipamentos_saude":          dict(arquivo="equipamentos_saude", indicador_score=None),
    "equipamentos_educacao":       dict(arquivo="equipamentos_educacao", indicador_score=None),
    "equipamentos_assistencia_social": dict(arquivo="equipamentos_assistencia_social", indicador_score=None),
    "equipamentos_cultura":        dict(arquivo="equipamentos_cultura", indicador_score=None),
    "area_abrangencia_centros_saude": dict(arquivo="area_abrangencia_centros_saude", indicador_score=None),
    "nomenclatura_pracas":         dict(arquivo="nomenclatura_pracas", indicador_score=None),
    "lotes_sim":                   dict(arquivo="lotes_SIM", indicador_score=None),
    # risco/suscetibilidade (candidato a virar dimensão própria do score no futuro — ver CLAUDE.md)
    "suscetibilidade_inundacoes":  dict(arquivo="suscetibilidade_inundacoes_cprm_ipt", indicador_score=None),
    "suscetibilidade_movimentos_gravitacionais": dict(arquivo="suscetibilidade_movimentos_gravitacionais_cprm_ipt", indicador_score=None),
    "pd2018_pontos_criticos_alagamento": dict(arquivo="pd2018_pontos_criticos_alagamento", indicador_score=None),
    "pd2018_pontos_criticos_inundacao": dict(arquivo="pd2018_pontos_criticos_inundacao", indicador_score=None),
    "area_suscetivel_inundacao_recanto_dourados": dict(arquivo="area_suscetivel_inundacao_recanto_dourados", indicador_score=None),
    "planicie_inundacao_bacia_capivari_2023": dict(arquivo="planicie_inundacao_bacia_rio_capivari_2023", indicador_score=None),
    "suscetibilidade_inundacao_bacia_capivari_2023": dict(arquivo="suscetibilidade_inundacao_bacia_rio_capivari_2023", indicador_score=None),
    "area_inundavel_tr5_2020_capivari":  dict(arquivo="area_inundavel_tr5_2020_bacia_capivari", indicador_score=None),
    "area_inundavel_tr5_2050_capivari":  dict(arquivo="area_inundavel_tr5_2050_bacia_capivari", indicador_score=None),
    "area_inundavel_tr25_2020_capivari": dict(arquivo="area_inundavel_tr25_2020_bacia_capivari", indicador_score=None),
    "area_inundavel_tr25_2050_capivari": dict(arquivo="area_inundavel_tr25_2050_bacia_capivari", indicador_score=None),
    "area_inundavel_tr100_2020_capivari": dict(arquivo="area_inundavel_tr100_2020_bacia_capivari", indicador_score=None),
    "area_inundavel_tr100_2050_capivari": dict(arquivo="area_inundavel_tr100_2050_bacia_capivari", indicador_score=None),
    # mobilidade/planejamento (Plano Diretor 2018) e conectividade/habitação
    "mzdo2018_perimetro_urbano":    dict(arquivo="mzdo2018_perimetro_urbano", indicador_score=None),
    "pd2018_mobilidade_rede_estrutural": dict(arquivo="pd2018_mobilidade_rede_estrutural", indicador_score=None),
    "pd2018_mobilidade_terminais_estacoes": dict(arquivo="pd2018_mobilidade_terminais_estacoes", indicador_score=None),
    "pd2018_projetos_urbanos":     dict(arquivo="pd2018_projetos_urbanos", indicador_score=None),
    "pd2018_regularizacao_fundiaria": dict(arquivo="pd2018_regularizacao_fundiaria", indicador_score=None),
    "pd2018_utb_utr":               dict(arquivo="pd2018_utb_utr", indicador_score=None),
    "poligono_prioritario_intervencao_area_central": dict(arquivo="poligono_prioritario_intervencao_area_central", indicador_score=None),
    "linha_conectividade":          dict(arquivo="linha_conectividade", indicador_score=None),
    "linha_conectividade_area_influencia": dict(arquivo="linha_conectividade_area_influencia", indicador_score=None),
    "nucleos_conectividade":        dict(arquivo="nucleos_conectividade", indicador_score=None),
    "nucleos_urbanos_sehab":        dict(arquivo="nucleos_urbanos_sehab", indicador_score=None),
    "area_conectividade_reconecta_rmc": dict(arquivo="area_conectividade_reconecta_rmc", indicador_score=None),
    "programas_habitacionais_historico1_loteamentos": dict(arquivo="programas_habitacionais_historico1_loteamentos", indicador_score=None),
    "programas_habitacionais_historico2_producao": dict(arquivo="programas_habitacionais_historico2_producao", indicador_score=None),
    "programas_habitacionais_historico3_producao_construcoes": dict(arquivo="programas_habitacionais_historico3_producao_construcoes", indicador_score=None),
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
DATA_DIR = Path(_paths["data_dir"]) / MUNICIPIO_SLUG / PROJECT_NAME

# Catálogo de dados municipais (leitura) — raw_dir/prefeituras_municipais/<slug>/t0/
MUNICIPAIS_RAW_DIR = RAW_CATALOG / "prefeituras_municipais" / MUNICIPIO_SLUG / "t0"

# Geojsons desenhados à mão (área do projeto, camadas locais...)
LOCAL_DATA_DIR = DATA_DIR / "raw" / "local"
# Arquivos fornecidos pela prefeitura (camadas solicitadas)
SOLICITADOS_DATA_DIR = DATA_DIR / "raw" / "solicitados"
# Saídas processadas (rasters de LST, cobertura do solo, estatísticas...)
PROCESSED_DIR = DATA_DIR / "processed"

GPKG_PATH = DATA_DIR / f"{PROJECT_NAME}.gpkg"

# Saída do dashboard/data_prep/build_web_assets.py (report.json + imgs/*.png)
# — fora do git. Sincronizada para dashboard/public/data/ antes do build do
# site (ver dashboard/data_prep/build_web_assets.py).
REPORT_DIR = DATA_DIR / "report"

for _dir in (DATA_DIR, LOCAL_DATA_DIR, SOLICITADOS_DATA_DIR, PROCESSED_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
