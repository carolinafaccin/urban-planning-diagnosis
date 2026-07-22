"""
estilo_mapa.py
--------------
O que faz   : Módulo de estilo compartilhado para os mapas PNG gerados por
              build_web_assets.py — título/legenda/notas em Inter com
              hierarquia de cinzas, norte e escala gráfica desenhados por
              código (sem depender de símbolos default do matplotlib) e um
              mapa de localização (inset) mostrando onde a área de estudo
              fica dentro do município/UF.
Uso         : aplicar_estilo() uma vez no início do script; depois
              criar_figura_mapa(...) no lugar de plt.subplots() direto.
Fonte       : Inter (SIL Open Font License) embutida em dashboard/data_prep/
              fonts/ — carregada via matplotlib.font_manager.addfont() para
              não depender de fontes instaladas na máquina (reprodutível em
              qualquer SO, diferente de usar "Avenir"/"Helvetica Neue" que só
              existem no macOS).
Adaptar     : cores/paleta de cinza em CORES abaixo; a lógica de escala
              gráfica (nice_round) e do inset de localização são genéricas —
              não precisam de config por projeto além do que já é passado
              como argumento.
"""

from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

FONTS_DIR = Path(__file__).resolve().parent / "fonts"

CORES = dict(
    titulo="#2b2b2b",
    texto="#8c8c8c",
    linha_norte="#2b2b2b",
    contorno_bbox="#333333",
    fundo_inset="#f4f4f4",
    destaque_inset="#e31a1c",
)


def aplicar_estilo():
    """Registra a fonte Inter (bundled) e define os rcParams globais.
    Chamar uma vez, antes de qualquer plt.subplots()."""
    for arquivo in FONTS_DIR.glob("*.ttf"):
        fm.fontManager.addfont(str(arquivo))
    plt.rcParams.update({
        "font.family": "Inter",
        "text.color": CORES["titulo"],
        "axes.edgecolor": CORES["texto"],
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    })


def _nice_round(valor):
    """Arredonda `valor` para 1/2/5 × 10^n mais próximo abaixo — usado pela
    escala gráfica (mesma lógica de bibliotecas de cartografia: a barra deve
    representar um número redondo de metros/km, não um valor arbitrário)."""
    import math
    if valor <= 0:
        return 1
    exp = math.floor(math.log10(valor))
    base = valor / (10 ** exp)
    if base >= 5:
        nice = 5
    elif base >= 2:
        nice = 2
    else:
        nice = 1
    return nice * (10 ** exp)


def desenhar_escala(ax, cor=None):
    """Escala gráfica desenhada nos dados (CRS em metros, ex. EPSG:31983) —
    calcula um valor redondo (~20% da largura do mapa) e desenha uma barra
    com dois segmentos (preto/branco alternados) mais o rótulo em km ou m."""
    cor = cor or CORES["titulo"]
    xmin, xmax = ax.get_xlim()
    largura = xmax - xmin
    alvo = largura * 0.2
    distancia_m = _nice_round(alvo)
    rotulo = f"{distancia_m / 1000:g} km" if distancia_m >= 1000 else f"{distancia_m:g} m"

    ymin, ymax = ax.get_ylim()
    y0 = ymin + (ymax - ymin) * 0.035
    x0 = xmin + largura * 0.05
    altura = (ymax - ymin) * 0.006

    # dois segmentos preto/branco (padrão de escala gráfica cartográfica)
    metade = distancia_m / 2
    ax.add_patch(plt.Rectangle((x0, y0), metade, altura, facecolor=cor, edgecolor="none", zorder=5))
    ax.add_patch(plt.Rectangle((x0 + metade, y0), metade, altura, facecolor="white",
                                edgecolor=cor, linewidth=0.6, zorder=5))
    ax.plot([x0, x0 + distancia_m], [y0, y0], color=cor, linewidth=0.6, zorder=5)
    ax.text(x0, y0 + altura * 2.2, "0", fontsize=6, color=cor, ha="center", va="bottom", zorder=5)
    ax.text(x0 + distancia_m, y0 + altura * 2.2, rotulo, fontsize=6, color=cor,
            ha="center", va="bottom", zorder=5)


def desenhar_norte(ax, cor=None):
    """Seta de norte simples (triângulo + N) no canto superior direito,
    em coordenadas de eixo (transAxes) — não se move com o zoom/extensão
    do mapa."""
    cor = cor or CORES["titulo"]
    x, y = 0.94, 0.90
    ax.annotate(
        "", xy=(x, y), xytext=(x, y - 0.07),
        xycoords="axes fraction",
        arrowprops=dict(arrowstyle="-|>", color=cor, linewidth=1.4, mutation_scale=14),
        zorder=6,
    )
    ax.text(x, y + 0.015, "N", transform=ax.transAxes, fontsize=9, fontweight="600",
            color=cor, ha="center", va="bottom", zorder=6)


def desenhar_inset_localizacao(fig, gdf_uf, gdf_municipio_alvo, gdf_municipios_uf=None,
                                bbox_geom=None, posicao=(0.03, 0.72, 0.24, 0.22)):
    """Mapa de localização (inset): UF em cinza claro, município do projeto
    destacado, e um marcador/retângulo indicando onde fica a área de estudo
    dentro do município. `posicao` são frações da figura (left, bottom,
    width, height) — canto superior esquerdo por padrão (o inferior direito
    já é ocupado pela legenda, e o inferior esquerdo pela escala gráfica)."""
    ax_inset = fig.add_axes(posicao)
    ax_inset.set_axis_off()
    gdf_uf.plot(ax=ax_inset, facecolor=CORES["fundo_inset"], edgecolor="white", linewidth=0.5, zorder=1)
    if gdf_municipios_uf is not None:
        gdf_municipios_uf.plot(ax=ax_inset, facecolor="none", edgecolor="white", linewidth=0.2, zorder=2)
    gdf_municipio_alvo.plot(ax=ax_inset, facecolor=CORES["destaque_inset"], edgecolor="none",
                             alpha=0.85, zorder=3)
    if bbox_geom is not None:
        cx, cy = bbox_geom.union_all().centroid.coords[0] if hasattr(bbox_geom, "union_all") \
            else bbox_geom.unary_union.centroid.coords[0]
        ax_inset.plot(cx, cy, marker="o", markersize=4, markerfacecolor="white",
                      markeredgecolor=CORES["destaque_inset"], markeredgewidth=1.2, zorder=4)
    for spine in ax_inset.spines.values():
        spine.set_visible(False)
    return ax_inset


def criar_figura_mapa(figsize=(7, 7)):
    """Substitui plt.subplots() puro — já aplica a mesma figura/eixo base
    usados por todos os mapas do projeto."""
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_axis_off()
    return fig, ax


def estilizar_titulo(ax, titulo, subtitulo=None):
    ax.set_title(titulo, fontsize=14, fontweight="600", color=CORES["titulo"],
                 loc="left", pad=10)
    if subtitulo:
        ax.text(0, 1.02, subtitulo, transform=ax.transAxes, fontsize=8.5,
                 color=CORES["texto"], ha="left", va="bottom")


def estilizar_fonte_dados(ax, texto, largura=95):
    """Nota de fonte/descrição sob o mapa. Quebra de linha manual (textwrap)
    em vez de wrap=True do matplotlib — este não respeita a largura real da
    figura e corta o texto (visto ao renderizar sem isso)."""
    import textwrap
    texto_quebrado = "\n".join(textwrap.wrap(texto, width=largura))
    ax.text(0, -0.035, texto_quebrado, transform=ax.transAxes, fontsize=7,
             color=CORES["texto"], ha="left", va="top", linespacing=1.4)
