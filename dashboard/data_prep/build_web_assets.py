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
    LOCAL_DATA_DIR,
    MUNICIPIO,
    REPORT_DIR,
)

SCRIPT_DIR = Path(__file__).resolve().parent
DASHBOARD_DIR = SCRIPT_DIR.parent
PUBLIC_DATA_DIR = DASHBOARD_DIR / "public" / "data"

ANALISE_AREA_MD = LOCAL_DATA_DIR / "analise_area.md"

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
         cores=["#ffffb2", "#fecc5c", "#fd8d3c", "#e31a1c"],
         descricao="Síntese: cruzamento de calor, déficit de verde, impermeabilização e "
                   "vulnerabilidade social por hexágono. Vermelho = maior prioridade."),
    dict(id="score", titulo="Score de prioridade", kind="continuo",
         col="score_prioridade", cmap="YlOrRd",
         descricao="Score contínuo [0–1] que embasa a classificação acima."),
    dict(id="lst", titulo="Temperatura de superfície (LST)", kind="continuo",
         col="ccl_lst", cmap="inferno",
         descricao="Temperatura de superfície média (°C). Fonte: Cool Cities Lab."),
    dict(id="vegetacao", titulo="Cobertura vegetal", kind="continuo",
         col="ccl_frac_veg", cmap="Greens",
         descricao="Fração de vegetação (%). Fonte: Cool Cities Lab."),
    dict(id="utci", titulo="Conforto térmico (UTCI)", kind="continuo",
         col="ccl_utci_base", cmap="inferno",
         descricao="Índice de conforto térmico universal na linha de base (°C)."),
    dict(id="renda", titulo="Renda média domiciliar", kind="continuo",
         col="renda_media", cmap="viridis",
         descricao="Renda média do responsável (R$), interpolada por ponderação "
                   "dasimétrica do Censo 2022."),
    dict(id="arborizacao", titulo="Déficit de arborização", kind="continuo",
         col="pct_sem_arb", cmap="OrRd",
         descricao="% de domicílios em face sem arborização (Censo 2022)."),
    dict(id="impermeavel", titulo="Impermeabilização", kind="continuo",
         col="pct_construido", cmap="pink_r",
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
    return hexg, contexto


def base_ax(hexg, contexto):
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_axis_off()
    if contexto.get("viario") is not None:
        contexto["viario"].plot(ax=ax, color="#bbbbbb", linewidth=0.3, zorder=1)
    # Contorno do bbox por cima do mapa (zorder alto) — contextualiza a área de
    # estudo mesmo quando a malha H3 não cobre o bbox inteiro (bordas rurais).
    BBOX_BOUNDARY.boundary.plot(ax=ax, color="#333333", linewidth=0.9, linestyle="--", zorder=3)
    return fig, ax


def render_continuo(hexg, contexto, m, out_png):
    if m["col"] not in hexg.columns or hexg[m["col"]].notna().sum() == 0:
        return None
    fig, ax = base_ax(hexg, contexto)
    hexg.plot(
        ax=ax, column=m["col"], cmap=m["cmap"], linewidth=0.1, edgecolor="white",
        alpha=0.85, legend=True, scheme="quantiles", k=5, zorder=2,
        legend_kwds=dict(loc="lower right", fontsize=7, frameon=False, title=""),
        missing_kwds=dict(color="#eeeeee", label="sem dado"),
    )
    ax.set_title(m["titulo"], fontsize=13, loc="left")
    fig.savefig(out_png, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return m["col"]


def render_categorico(hexg, contexto, m, out_png):
    if m["col"] not in hexg.columns:
        return None
    from matplotlib.colors import ListedColormap
    import matplotlib.patches as mpatches

    cats = m["ordem"]
    cmap = ListedColormap(m["cores"])
    cat_idx = hexg[m["col"]].astype("category").cat.set_categories(cats)
    fig, ax = base_ax(hexg, contexto)
    hexg.assign(_i=cat_idx.cat.codes).plot(
        ax=ax, column="_i", cmap=cmap, vmin=0, vmax=len(cats) - 1,
        linewidth=0.1, edgecolor="white", alpha=0.85, zorder=2,
    )
    ax.legend(handles=[mpatches.Patch(color=c, label=l) for c, l in zip(m["cores"], cats)],
              loc="lower right", fontsize=8, frameon=False, title="prioridade")
    ax.set_title(m["titulo"], fontsize=13, loc="left")
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
    hexg, contexto = carregar()
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
        ok = render(hexg, contexto, m, out_png)
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
    dist = (hexg["prioridade"].value_counts().reindex(["muito alta", "alta", "média", "baixa"])
            if "prioridade" in hexg.columns else None)

    report = dict(
        cidade=MUNICIPIO,
        data=date.today().isoformat(),
        n_hex=n_hex,
        n_pop=n_pop,
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
