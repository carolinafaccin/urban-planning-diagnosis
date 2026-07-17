"""
generate_report.py
-------------------
O que faz   : Gera um relatório estático (HTML + imagens PNG) a partir do
              GeoPackage final do projeto, para visualização rápida dos mapas
              antes de refinar a estética no QGIS/Python.
Saída       : {REPORT_DIR}/  (fora do git)
                index.html
                assets/style.css
                imgs/<cidade>/<mapa>.png
Requer      : 10_build_geopackage.py e 11_analises.py já rodados.

Deploy-agnóstico: gera arquivos estáticos com caminhos relativos. Aponte o
Cloudflare Pages (ou outro host) para {REPORT_DIR}. Como fica fora do git, não
entra em nenhum commit — publique por upload direto (ex.: `wrangler pages
deploy <REPORT_DIR>`), não por "servir do repositório".

Para adaptar: a lista MAPAS abaixo controla quais camadas/indicadores viram
              figura. Mapas cujo indicador não existe no GeoPackage são pulados.

Como rodar  : cd projetos/campinas
              python ../../scripts/report/generate_report.py
"""

import shutil
import sys
import unicodedata
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import geopandas as gpd  # noqa: E402
from jinja2 import Environment, FileSystemLoader  # noqa: E402

sys.path.insert(0, str(Path.cwd()))
from config import CRS_PROJETO, GPKG_PATH, MUNICIPIO, REPORT_DIR  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
TMPL_DIR = SCRIPT_DIR / "templates"
CSS_SRC = SCRIPT_DIR / "assets" / "style.css"

DPI = 140


def slug(texto):
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return t.lower().replace(" ", "_").replace("/", "-")


CIDADE_SLUG = slug(MUNICIPIO)

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


def main():
    hexg, contexto = carregar()
    imgs_dir = REPORT_DIR / "imgs" / CIDADE_SLUG
    imgs_dir.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copy(CSS_SRC, REPORT_DIR / "assets" / "style.css")

    cards = []
    for m in MAPAS:
        out_png = imgs_dir / f"{m['id']}.png"
        render = render_categorico if m["kind"] == "categorico" else render_continuo
        ok = render(hexg, contexto, m, out_png)
        if ok is None:
            print(f"  [pulado] {m['id']}: coluna '{m['col']}' ausente ou vazia.")
            continue
        cards.append(dict(titulo=m["titulo"],
                          img=f"imgs/{CIDADE_SLUG}/{m['id']}.png",
                          descricao=m["descricao"]))
        print(f"  [ok] {m['id']} → {out_png.name}")

    # estatísticas do cabeçalho
    n = len(hexg)
    n_pop = int(hexg["tem_populacao"].sum()) if "tem_populacao" in hexg.columns else None
    dist = (hexg["prioridade"].value_counts().reindex(["muito alta", "alta", "média", "baixa"])
            if "prioridade" in hexg.columns else None)

    env = Environment(loader=FileSystemLoader(str(TMPL_DIR)), autoescape=True)
    html = env.get_template("report.html").render(
        cidade=MUNICIPIO, data=date.today().isoformat(),
        n_hex=n, n_pop=n_pop,
        dist=(dist.to_dict() if dist is not None else {}),
        cards=cards,
    )
    (REPORT_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"\n  Relatório: {REPORT_DIR / 'index.html'}  ({len(cards)} mapas)")


if __name__ == "__main__":
    main()
    print("\nConcluído.")
