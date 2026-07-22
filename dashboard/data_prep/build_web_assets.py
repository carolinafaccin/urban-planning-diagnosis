"""
build_web_assets.py
--------------------
O que faz   : Gera os assets do site (dashboard/) a partir do GeoPackage final
              do projeto: os mesmos mapas PNG que o antigo generate_report.py
              produzia, mais um report.json com estatísticas e a análise
              descritiva da área. Depois sincroniza tudo para
              dashboard/public/data/ (limpando antes de copiar), de onde o
              Vite serve os arquivos em dev/build.
Saída       : {REPORT_DIR}/ (fora do git): report.json, imgs/*.png
              dashboard/public/data/ (gitignored): cópia do acima
Requer      : 13_build_geopackage.py e 14_analises.py já rodados.

Estilo dos mapas (título, norte, escala, inset de localização, tipografia
Inter) vem de estilo_mapa.py, neste mesmo diretório — ver esse arquivo para
a paleta de cores/tokens de design.

O site NÃO expõe o GeoPackage para download (removido — o arquivo passou de
25 MiB, limite por arquivo do Cloudflare Pages, com a adição das camadas de
localização país/UF/município). O entregável principal do diagnóstico
continua sendo o .gpkg em DATA_DIR (ver CLAUDE.md), compartilhado pelo
Google Drive do projeto.

A análise descritiva da área (texto específico do projeto, não genérico) vem
de {LOCAL_DATA_DIR}/analise_area.md — mesmo lugar de outros inputs manuais do
projeto (ver 12_dados_locais.py). Leitura tolerante: se não existir, o campo
fica vazio e o site mostra a seção só quando o texto existir.

Para adaptar: a lista MAPAS controla quais camadas/indicadores viram figura.
              Mapas cujo indicador não existe no GeoPackage são pulados.

Como rodar  : cd projetos/campinas
              python ../../dashboard/data_prep/build_web_assets.py
"""

import json
import shutil
import sys
import unicodedata
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import geopandas as gpd  # noqa: E402
from shapely.geometry import box  # noqa: E402

sys.path.insert(0, str(Path.cwd()))
from config import (  # noqa: E402
    BBOX,
    CRS_PROJETO,
    CRS_WGS84,
    GPKG_PATH,
    IBGE_COD_MUN,
    LOCAL_DATA_DIR,
    MUNICIPIO,
    REPORT_DIR,
    TITULO_PROJETO,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estilo_mapa import (  # noqa: E402
    aplicar_estilo,
    criar_figura_mapa,
    fonte_dados_sidebar,
    inset_localizacao_sidebar,
    legenda_categorica_sidebar,
    legenda_continua_sidebar,
    norte_escala_sidebar,
    titulo_acima_legenda,
)
from paletas import PALETA_CALOR, PALETA_DIVERGENTE, PALETA_VERDE, CORES_CALOR_4  # noqa: E402,F401

aplicar_estilo()

SCRIPT_DIR = Path(__file__).resolve().parent
DASHBOARD_DIR = SCRIPT_DIR.parent
PUBLIC_DATA_DIR = DASHBOARD_DIR / "public" / "data"

ANALISE_AREA_MD = LOCAL_DATA_DIR / "analise_area.md"
COD_UF = IBGE_COD_MUN[:2]

DPI = 140


def slug(texto):
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return t.lower().replace(" ", "_").replace("/", "-")


CIDADE_SLUG = slug(MUNICIPIO)

# Contorno do BBOX do projeto (config.py, WGS84) reprojetado uma vez para o
# CRS do projeto — desenhado em todos os mapas para dar contexto de até onde
# vai a área de estudo (ver base_ax).
BBOX_BOUNDARY = (
    gpd.GeoSeries([box(BBOX["west"], BBOX["south"], BBOX["east"], BBOX["north"])], crs=CRS_WGS84)
    .to_crs(CRS_PROJETO)
)

# Mapas a renderizar. kind: "categorico" | "continuo".
#   col       : coluna de h3_sintese
#   cmap      : colormap matplotlib
#   descricao : texto curto sob o mapa
MAPAS = [
    dict(id="prioridade", titulo="Áreas prioritárias", kind="categorico",
         col="prioridade", ordem=["baixa", "média", "alta", "muito alta"],
         cores=CORES_CALOR_4,
         descricao="Síntese: cruzamento de calor, déficit de verde, impermeabilização e "
                   "vulnerabilidade social por hexágono. Vermelho = maior prioridade."),
    dict(id="score", titulo="Score de prioridade", kind="continuo",
         col="score_prioridade", cmap=PALETA_CALOR,
         descricao="Score contínuo [0–1] que embasa a classificação acima."),
    dict(id="lst", titulo="Temperatura de superfície (LST)", kind="continuo",
         col="ccl_lst", cmap=PALETA_CALOR,
         descricao="Temperatura de superfície média (°C). Fonte: Cool Cities Lab."),
    dict(id="vegetacao", titulo="Cobertura vegetal", kind="continuo",
         col="ccl_frac_veg", cmap=PALETA_VERDE,
         descricao="Fração de vegetação (%). Fonte: Cool Cities Lab."),
    dict(id="utci", titulo="Conforto térmico (UTCI)", kind="continuo",
         col="ccl_utci_base", cmap=PALETA_CALOR,
         descricao="Índice de conforto térmico universal na linha de base (°C)."),
    dict(id="renda", titulo="Renda média domiciliar", kind="continuo",
         col="renda_media", cmap=PALETA_DIVERGENTE,
         descricao="Renda média do responsável (R$), interpolada por ponderação "
                   "dasimétrica do Censo 2022."),
    dict(id="arborizacao", titulo="Déficit de arborização", kind="continuo",
         col="pct_sem_arb", cmap=PALETA_CALOR,
         descricao="% de domicílios em face sem arborização (Censo 2022)."),
    dict(id="impermeavel", titulo="Impermeabilização", kind="continuo",
         col="pct_construido", cmap=PALETA_CALOR,
         descricao="% do hexágono ocupado por edificações (Overture)."),
]


def carregar():
    hexg = gpd.read_file(GPKG_PATH, layer="h3_sintese").to_crs(CRS_PROJETO)
    contexto = {}
    for camada in ("viario", "edificacoes"):
        try:
            contexto[camada] = gpd.read_file(GPKG_PATH, layer=camada).to_crs(CRS_PROJETO)
        except Exception:
            contexto[camada] = None
    # Contorno da área de projeto e do loteamento — desenhados por cima dos
    # hexágonos pra dar referência de onde fica o recorte de intervenção
    # dentro da área de estudo (ver render_*).
    for camada in ("area_de_projeto", "loteamento-jardim-bassoli"):
        try:
            contexto[camada] = gpd.read_file(GPKG_PATH, layer=camada).to_crs(CRS_PROJETO)
        except Exception:
            contexto[camada] = None
    # Limite municipal inteiro (não recortado pelo bbox — ler_recorte de
    # 04_dados_municipais.py filtra por interseção mas mantém a feição
    # completa) — usado só pelo inset, para mostrar o bbox do projeto dentro
    # da cidade.
    try:
        municipio = gpd.read_file(GPKG_PATH, layer="limite_municipal").to_crs(CRS_PROJETO)
    except Exception:
        municipio = None
    return hexg, contexto, municipio


# Espessura da linha branca do viário por hierarquia (classificação OSM,
# coluna "highway") — via mais importante = linha mais grossa, como nos
# mapas de referência do Guilherme. Checado por substring porque algumas
# feições vêm com mais de uma tag (ex.: "['unclassified', 'residential']",
# ver cabeçalho do 01_download_osm.py) — a primeira classe que bater na
# lista abaixo (ordem = hierarquia, maior primeiro) decide a largura.
LARGURA_VIARIO = [
    (("motorway", "trunk", "primary"), 0.9),
    (("secondary",), 0.7),
    (("tertiary", "unclassified"), 0.5),
    (("residential", "service", "living_street"), 0.3),
]
LARGURA_VIARIO_PADRAO = 0.15  # footway/cycleway/path/track e classes não mapeadas


def _largura_via(highway):
    texto = str(highway)
    for chaves, largura in LARGURA_VIARIO:
        if any(chave in texto for chave in chaves):
            return largura
    return LARGURA_VIARIO_PADRAO


def desenhar_contexto_sobre_hex(ax_mapa, contexto):
    """Vias e contornos de referência (área de projeto, loteamento) por cima
    dos hexágonos (zorder maior) — o viário embaixo ficava invisível com o
    preenchimento opaco; por cima, funciona como as linhas brancas de rua
    que aparecem nos mapas coropléticos de referência. Espessura do viário
    por hierarquia (ver LARGURA_VIARIO); contorno da área de projeto fino e
    pontilhado (contexto, não o recorte de intervenção em si); contorno do
    loteamento Jardim Bassoli grosso, sólido e preto (o recorte de
    intervenção propriamente dito — precisa se destacar dos dois acima)."""
    viario = contexto.get("viario")
    if viario is not None:
        larguras = viario["highway"].apply(_largura_via) if "highway" in viario.columns else 0.3
        viario.plot(ax=ax_mapa, color="white", linewidth=larguras, alpha=0.9, zorder=3)
    if contexto.get("area_de_projeto") is not None:
        contexto["area_de_projeto"].boundary.plot(
            ax=ax_mapa, color="#2b2b2b", linewidth=0.7, linestyle=(0, (1, 1.6)), zorder=4)
    if contexto.get("loteamento-jardim-bassoli") is not None:
        contexto["loteamento-jardim-bassoli"].boundary.plot(
            ax=ax_mapa, color="#000000", linewidth=1.8, zorder=4)


TOPO_BLOCO_TITULO = 0.58  # onde o bloco título+legenda+norte/escala começa (de cima pra baixo)
# Folga suficiente pro pior caso: título de 2 linhas + legenda contínua de 5
# classes + "sem dado" + norte/escala + fonte, sem colidir — um valor menor
# deixava o "N" em cima do último item da legenda quando o mapa tinha
# valores nulos (mais linhas na legenda).


def base_ax(hexg, contexto, municipio=None):
    fig, ax_mapa, ax_side = criar_figura_mapa()
    # Inset de localização isolado, no alto da sidebar — o bloco
    # título+legenda+norte/escala fica agrupado mais abaixo (ver
    # TOPO_BLOCO_TITULO), com espaço em branco entre os dois, no mesmo
    # espírito das referências de cartografia editorial.
    if municipio is not None and len(municipio) > 0:
        inset_localizacao_sidebar(fig, ax_side, municipio, BBOX_BOUNDARY,
                                   titulo=f"Localização em {MUNICIPIO}", y_topo=0.97)
    return fig, ax_mapa, ax_side


def render_continuo(hexg, contexto, municipio, m, out_png):
    if m["col"] not in hexg.columns or hexg[m["col"]].notna().sum() == 0:
        return None
    fig, ax_mapa, ax_side = base_ax(hexg, contexto, municipio)
    hexg.plot(
        ax=ax_mapa, column=m["col"], cmap=m["cmap"], linewidth=0, edgecolor="none",
        antialiased=False, alpha=1.0, legend=False, scheme="quantiles", k=5, zorder=2,
        missing_kwds=dict(color="#eeeeee"),
    )
    desenhar_contexto_sobre_hex(ax_mapa, contexto)

    # Título encostado direto na legenda (não no topo do mapa) — mesmo
    # padrão do autor de referência.
    y = titulo_acima_legenda(ax_side, m["titulo"], y_topo=TOPO_BLOCO_TITULO)
    y = legenda_continua_sidebar(ax_side, hexg[m["col"]], m["cmap"], y_topo=y, fmt=m.get("fmt", "{:.1f}"))
    y = norte_escala_sidebar(ax_side, ax_mapa, y_topo=y)
    fonte_dados_sidebar(ax_side, m["descricao"], y=y - 0.02)
    fig.savefig(out_png, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return m["col"]


def render_categorico(hexg, contexto, municipio, m, out_png):
    if m["col"] not in hexg.columns:
        return None
    from matplotlib.colors import ListedColormap

    cats = m["ordem"]
    cmap = ListedColormap(m["cores"])
    cat_idx = hexg[m["col"]].astype("category").cat.set_categories(cats)
    fig, ax_mapa, ax_side = base_ax(hexg, contexto, municipio)
    hexg.assign(_i=cat_idx.cat.codes).plot(
        ax=ax_mapa, column="_i", cmap=cmap, vmin=0, vmax=len(cats) - 1,
        linewidth=0, edgecolor="none", antialiased=False, alpha=1.0, zorder=2,
    )
    desenhar_contexto_sobre_hex(ax_mapa, contexto)

    y = titulo_acima_legenda(ax_side, m["titulo"], y_topo=TOPO_BLOCO_TITULO)
    y = legenda_categorica_sidebar(ax_side, m["cores"], cats, y_topo=y, titulo="prioridade")
    y = norte_escala_sidebar(ax_side, ax_mapa, y_topo=y)
    fonte_dados_sidebar(ax_side, m["descricao"], y=y - 0.02)
    fig.savefig(out_png, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return m["col"]


def ler_analise_area():
    """Leitura tolerante: se o arquivo não existir, avisa e segue (mesmo
    padrão de 12_dados_locais.py) — o site mostra a seção só quando houver
    texto."""
    if not ANALISE_AREA_MD.exists():
        print(f"  [aviso] análise da área não encontrada: {ANALISE_AREA_MD}")
        return ""
    return ANALISE_AREA_MD.read_text(encoding="utf-8")


def sincronizar_public_data():
    """Copia REPORT_DIR para dashboard/public/data/, limpando antes (não
    overwrite silencioso) para não vazar PNGs de um projeto anterior testado
    na mesma máquina."""
    if PUBLIC_DATA_DIR.exists():
        shutil.rmtree(PUBLIC_DATA_DIR)
    shutil.copytree(REPORT_DIR, PUBLIC_DATA_DIR)


def main():
    hexg, contexto, localizacao = carregar()
    # Limpa REPORT_DIR antes de escrever — evita misturar com resíduos de
    # formatos antigos (ex.: imgs/<cidade>/ do generate_report.py aposentado).
    if REPORT_DIR.exists():
        shutil.rmtree(REPORT_DIR)
    imgs_dir = REPORT_DIR / "imgs"
    imgs_dir.mkdir(parents=True, exist_ok=True)

    cards = []
    for m in MAPAS:
        out_png = imgs_dir / f"{m['id']}.png"
        render = render_categorico if m["kind"] == "categorico" else render_continuo
        ok = render(hexg, contexto, localizacao, m, out_png)
        if ok is None:
            print(f"  [pulado] {m['id']}: coluna '{m['col']}' ausente ou vazia.")
            continue
        cards.append(dict(id=m["id"], titulo=m["titulo"],
                          img=f"imgs/{m['id']}.png",
                          descricao=m["descricao"]))
        print(f"  [ok] {m['id']} → {out_png.name}")

    # estatísticas do cabeçalho
    n_hex = len(hexg)
    n_pop = int(hexg["tem_populacao"].sum()) if "tem_populacao" in hexg.columns else None
    area_km2 = round(hexg.geometry.area.sum() / 1e6, 1)
    pop_total = int(round(hexg["ccl_pop"].sum())) if "ccl_pop" in hexg.columns else None
    dist = (hexg["prioridade"].value_counts().reindex(["muito alta", "alta", "média", "baixa"])
            if "prioridade" in hexg.columns else None)

    report = dict(
        cidade=MUNICIPIO,
        titulo=TITULO_PROJETO,
        data=date.today().isoformat(),
        n_hex=n_hex,
        n_pop=n_pop,
        area_km2=area_km2,
        pop_total=pop_total,
        dist=(dist.dropna().astype(int).to_dict() if dist is not None else {}),
        cards=cards,
        analise_md=ler_analise_area(),
    )
    (REPORT_DIR / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n  report.json: {REPORT_DIR / 'report.json'}  ({len(cards)} mapas)")

    sincronizar_public_data()
    print(f"  Sincronizado para {PUBLIC_DATA_DIR}")


if __name__ == "__main__":
    main()
    print("\nConcluído.")
