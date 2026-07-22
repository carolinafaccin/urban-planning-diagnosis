"""
estilo_mapa.py
--------------
O que faz   : Módulo de estilo compartilhado para os mapas PNG gerados por
              build_web_assets.py — layout de duas colunas (sidebar de texto
              à esquerda: título logo acima da legenda, descrição, norte+
              escala, mapa de localização e fonte dos dados — mapa "limpo" à
              direita, sem NADA sobreposto além do próprio choropleth),
              tipografia Inter com hierarquia de cinzas. Inspirado em
              referências de cartografia editorial (mapas estáticos, não
              interativos) — título grudado na legenda (não no topo do
              mapa), símbolo de norte minimalista (círculo + haste) e escala
              gráfica em linha fina, todos empilhados na mesma coluna
              lateral em vez de flutuando por cima do mapa.
Uso         : aplicar_estilo() uma vez no início do script; depois
              criar_figura_mapa() no lugar de plt.subplots() direto —
              devolve (fig, ax_mapa, ax_sidebar). Os blocos da sidebar
              (título, legenda, norte/escala, inset, fonte) são empilhados
              de cima pra baixo — cada função devolve o "y" onde parou, que
              vira o y_topo do próximo bloco (ver build_web_assets.py).
Fonte       : Inter (SIL Open Font License) embutida em dashboard/data_prep/
              fonts/ — carregada via matplotlib.font_manager.addfont() para
              não depender de fontes instaladas na máquina (reprodutível em
              qualquer SO, diferente de usar "Avenir"/"Helvetica Neue" que só
              existem no macOS).
Adaptar     : cores/paleta de cinza em CORES; LARGURA_SIDEBAR controla a
              proporção sidebar/mapa. legenda_continua_sidebar/
              legenda_categorica_sidebar desenham a legenda manualmente (em
              vez do ax.legend do geopandas) pra poder ficar na sidebar.
"""

import math
import textwrap
from pathlib import Path

import matplotlib as mpl
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import mapclassify

FONTS_DIR = Path(__file__).resolve().parent / "fonts"

CORES = dict(
    titulo="#2b2b2b",
    texto="#8c8c8c",
    linha="#595959",
    fundo_inset="#e6e6e6",
    destaque_inset="#e31a1c",
)

LARGURA_SIDEBAR = 0.30
MARGEM_X = 0.09  # recuo esquerdo comum a todos os blocos da sidebar


def aplicar_estilo():
    """Registra a fonte Inter (bundled) e define os rcParams globais.
    Chamar uma vez, antes de qualquer plt.subplots()/figure()."""
    for arquivo in FONTS_DIR.glob("*.ttf"):
        fm.fontManager.addfont(str(arquivo))
    plt.rcParams.update({
        "font.family": "Inter",
        "text.color": CORES["titulo"],
        "axes.edgecolor": CORES["texto"],
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    })


def criar_figura_mapa(figsize=(10, 7.2)):
    """Layout de duas colunas: sidebar de texto (0 a LARGURA_SIDEBAR da
    figura) e área do mapa (resto), cada uma seu próprio eixo. A sidebar usa
    coordenadas de dados 0–1 (equivalentes a fração do eixo, já que xlim/
    ylim = (0,1) e o eixo ocupa a figura inteira em altura) — isso permite
    converter uma posição da sidebar em fração de figura sem contas: a
    fração em x é y_dado * LARGURA_SIDEBAR, a fração em y é o próprio
    y_dado (usado por inset_localizacao_sidebar)."""
    fig = plt.figure(figsize=figsize)
    ax_side = fig.add_axes((0.0, 0.0, LARGURA_SIDEBAR, 1.0))
    ax_side.set_axis_off()
    ax_side.set_xlim(0, 1)
    ax_side.set_ylim(0, 1)
    ax_mapa = fig.add_axes((LARGURA_SIDEBAR + 0.015, 0.03, 1 - LARGURA_SIDEBAR - 0.045, 0.94))
    ax_mapa.set_axis_off()
    return fig, ax_mapa, ax_side


def descricao_sidebar(ax_side, texto, y, largura=36):
    ax_side.text(MARGEM_X, y, "\n".join(textwrap.wrap(texto, width=largura)), fontsize=8.5,
                 color=CORES["texto"], ha="left", va="top", linespacing=1.5)
    n_linhas = texto and len(textwrap.wrap(texto, width=largura)) or 0
    return y - n_linhas * 0.028 - 0.03


def fonte_dados_sidebar(ax_side, texto, y, largura=36):
    ax_side.text(MARGEM_X, y, "\n".join(textwrap.wrap(texto, width=largura)), fontsize=7,
                 color=CORES["texto"], ha="left", va="top", linespacing=1.4)


def _nice_round(valor):
    """Arredonda para 1/2/5 × 10^n mais próximo abaixo — a escala gráfica
    deve representar um número redondo de metros/km, não um valor
    arbitrário."""
    if valor <= 0:
        return 1
    exp = math.floor(math.log10(valor))
    base = valor / (10 ** exp)
    nice = 5 if base >= 5 else (2 if base >= 2 else 1)
    return nice * (10 ** exp)


def norte_escala_sidebar(ax_side, ax_mapa, y_topo):
    """Norte (círculo + haste, sem seta) e escala gráfica (linha fina) lado
    a lado, no mesmo eixo de base — estilo minimalista (não a seta digital
    de antes). A distância real vem da extensão do mapa (ax_mapa, CRS em
    metros); o desenho em si fica todo na sidebar. Tudo é posicionado
    relativo a `y_topo` e só desce a partir dali (nada é desenhado acima),
    pra nunca sobrepor o último item da legenda."""
    cor = CORES["linha"]

    # Norte: "N" + círculo vazado + haste, empilhados de cima pra baixo
    xn = MARGEM_X + 0.02
    y_label = y_topo - 0.012
    y_circulo = y_label - 0.026
    y_circulo_base = y_circulo - 0.013
    y_haste_fim = y_circulo_base - 0.045
    ax_side.text(xn, y_label, "N", fontsize=8, color=cor, ha="center", va="top")
    ax_side.add_patch(plt.Circle((xn, y_circulo), 0.013, facecolor="white", edgecolor=cor, linewidth=1.0))
    ax_side.plot([xn, xn], [y_haste_fim, y_circulo_base], color=cor, linewidth=1.0, solid_capstyle="round")

    # Escala: linha fina alinhada com o círculo, marcas de topo nas duas
    # pontas, rótulo embaixo
    xmin, xmax = ax_mapa.get_xlim()
    distancia_m = _nice_round((xmax - xmin) * 0.22)
    rotulo = f"{distancia_m / 1000:g} km" if distancia_m >= 1000 else f"{distancia_m:g} m"

    x0, x1 = MARGEM_X + 0.14, MARGEM_X + 0.50
    y_linha = y_circulo
    ax_side.plot([x0, x1], [y_linha, y_linha], color=cor, linewidth=1.0)
    ax_side.plot([x0, x0], [y_linha, y_linha + 0.014], color=cor, linewidth=1.0)
    ax_side.plot([x1, x1], [y_linha, y_linha + 0.014], color=cor, linewidth=1.0)
    ax_side.text((x0 + x1) / 2, y_linha - 0.018, rotulo, fontsize=7.5, color=cor, ha="center", va="top")

    return y_haste_fim - 0.04


def legenda_continua_sidebar(ax_side, serie, cmap_nome, y_topo, titulo=None, k=5, fmt="{:.1f}",
                              cor_sem_dado="#eeeeee"):
    """Legenda vertical de swatches (retângulo + rótulo) computada com a
    mesma classificação de quantis usada no mapa (mapclassify.Quantiles),
    para os intervalos baterem com as cores desenhadas nos hexágonos."""
    valores = serie.dropna()
    k_efetivo = min(k, valores.nunique()) or 1
    bins = list(mapclassify.Quantiles(valores, k=k_efetivo).bins)
    cmap = mpl.colormaps[cmap_nome].resampled(len(bins))

    y = y_topo
    if titulo:
        ax_side.text(MARGEM_X, y, titulo, fontsize=9.5, fontweight="600", color=CORES["titulo"],
                     ha="left", va="top")
        y -= 0.038
    lower = valores.min()
    for i, upper in enumerate(bins):
        ax_side.add_patch(plt.Rectangle((MARGEM_X, y - 0.022), 0.05, 0.022, facecolor=cmap(i),
                                          edgecolor="none"))
        ax_side.text(MARGEM_X + 0.08, y - 0.011, f"{fmt.format(lower)} – {fmt.format(upper)}", fontsize=8,
                     color=CORES["linha"], ha="left", va="center")
        lower = upper
        y -= 0.032
    if serie.isna().any():
        ax_side.add_patch(plt.Rectangle((MARGEM_X, y - 0.022), 0.05, 0.022, facecolor=cor_sem_dado,
                                          edgecolor="none"))
        ax_side.text(MARGEM_X + 0.08, y - 0.011, "sem dado", fontsize=8, color=CORES["linha"],
                     ha="left", va="center")
        y -= 0.032
    return y


def legenda_categorica_sidebar(ax_side, cores, labels, y_topo, titulo=None):
    y = y_topo
    if titulo:
        ax_side.text(MARGEM_X, y, titulo, fontsize=9.5, fontweight="600", color=CORES["titulo"],
                     ha="left", va="top")
        y -= 0.038
    for cor, label in zip(cores, labels):
        ax_side.add_patch(plt.Rectangle((MARGEM_X, y - 0.022), 0.05, 0.022, facecolor=cor, edgecolor="none"))
        ax_side.text(MARGEM_X + 0.08, y - 0.011, label, fontsize=8, color=CORES["linha"],
                     ha="left", va="center")
        y -= 0.032
    return y


def titulo_acima_legenda(ax_side, titulo, y_topo, largura=26):
    """Título grudado bem acima da legenda (não no topo do mapa) — mesmo
    padrão do autor de referência: o bloco título+legenda funciona como uma
    unidade visual só, a parte de cima da sidebar fica livre para a
    descrição/inset."""
    ax_side.text(MARGEM_X, y_topo, "\n".join(textwrap.wrap(titulo, width=largura)), fontsize=13,
                 fontweight="700", color=CORES["titulo"], ha="left", va="top", linespacing=1.2)
    n_linhas = len(textwrap.wrap(titulo, width=largura))
    return y_topo - n_linhas * 0.045 - 0.025


def inset_localizacao_sidebar(fig, ax_side, gdf_municipio, gdf_bbox, titulo, y_topo, altura=0.14):
    """Mapa de localização (inset) DENTRO da sidebar (não sobreposto ao
    mapa principal): limite municipal em cinza claro, com o bbox do projeto
    destacado — responde "onde fica essa área de estudo dentro da cidade".
    `titulo` (ex. "Localização em Campinas") vai como texto logo acima do
    inset, na mesma coluna. `y_topo` é a coordenada de dados (0–1) da
    sidebar; como a sidebar ocupa a figura inteira em altura e começa em
    x=0, a conversão pra fração de figura é direta (ver criar_figura_mapa)."""
    ax_side.text(MARGEM_X, y_topo, titulo, fontsize=8.5, fontweight="600",
                 color=CORES["titulo"], ha="left", va="top")
    y_topo -= 0.045

    x0_fig = MARGEM_X * LARGURA_SIDEBAR
    largura_fig = 0.75 * LARGURA_SIDEBAR
    y0_fig = y_topo - altura
    ax_inset = fig.add_axes((x0_fig, y0_fig, largura_fig, altura))
    ax_inset.set_axis_off()
    gdf_municipio.plot(ax=ax_inset, facecolor=CORES["fundo_inset"], edgecolor="white",
                        linewidth=0.6, zorder=1)
    gdf_bbox.plot(ax=ax_inset, facecolor=CORES["destaque_inset"], edgecolor="none",
                  alpha=0.9, zorder=2)
    for spine in ax_inset.spines.values():
        spine.set_visible(False)
    return y0_fig - 0.03
