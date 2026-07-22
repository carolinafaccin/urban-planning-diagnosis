"""
paletas.py
----------
O que faz   : Biblioteca de paletas de cores para os mapas PNG do dashboard,
              extraídas de dois mapas de referência do Guilherme (WRI Brasil)
              — mesmo "olhar" cartográfico que o resto do projeto busca
              copiar (ver estilo_mapa.py). Registra colormaps contínuos no
              matplotlib (mpl.colormaps) para serem usados por nome, como
              qualquer colormap nativo ("viridis", "inferno" etc.), em
              hexg.plot(cmap=...).
Motivação   : colormaps nativos usados antes (inferno, viridis, Greens,
              OrRd, pink_r) têm uma ponta perto do preto ou perto do branco
              — funde com contorno/texto ou com áreas "sem dado" no mapa.
              As paletas do Guilherme evitam os dois extremos.
Fonte       : cores extraídas por amostragem de pixel dos swatches de
              legenda em dois mapas enviados pela usuária (LinkedIn,
              2026-07-22): "% de pessoas com mais de 60 anos" (paleta
              diverging quente/frio) e "Domicílios compostos por casais +
              filho(s)" (paleta multi-hue quente→frio). Não são as cores
              "oficiais" de nenhuma marca — são uma extração visual.
Adaptar     : para adicionar uma paleta nova, siga o padrão de
              GUILHERME_QUENTE_FRIO/GUILHERME_MULTI abaixo (lista de hex, da
              origem dos swatches) e derive um colormap contínuo com
              _registrar().
"""

import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap

# Swatches originais (top a baixo na legenda dos mapas de referência), como
# ponto de partida — não usados diretamente nos mapas deste projeto, mas
# preservados aqui como a fonte de onde as paletas abaixo foram derivadas.
GUILHERME_QUENTE_FRIO = ["#a6311f", "#dd432b", "#f57840", "#bedfee", "#62b8c5", "#014546"]
GUILHERME_MULTI = ["#eabc66", "#f9a05e", "#ec6c51", "#83ad7b", "#278680", "#214754"]


def _registrar(nome, cores):
    cmap = LinearSegmentedColormap.from_list(nome, cores)
    if nome in mpl.colormaps:
        mpl.colormaps.unregister(nome)
    mpl.colormaps.register(cmap, name=nome)
    return nome


# Sequencial "quente" (dourado → laranja → vermelho): calor, déficits e
# indicadores onde "mais" = pior. Usada em vez de inferno/OrRd (que vão a
# preto ou a branco numa das pontas).
PALETA_CALOR = _registrar("paleta_calor", ["#eabc66", "#f9a05e", "#ec6c51", "#a6311f"])

# Sequencial "verde" (verde claro → verde-azulado → azul-petróleo escuro):
# cobertura vegetal. Usada em vez de Greens (ponta clara quase branca).
PALETA_VERDE = _registrar("paleta_verde", ["#eabc66", "#83ad7b", "#278680", "#214754"])

# Diverging quente/frio (vermelho-tijolo → laranja → azul-petróleo escuro):
# indicadores com leitura direcional (ex.: renda). Usada em vez de viridis
# (ponta escura quase preta).
PALETA_DIVERGENTE = _registrar(
    "paleta_divergente_calor_frio",
    ["#a6311f", "#dd432b", "#f57840", "#62b8c5", "#014546"],
)

# 4 cores discretas (mesma progressão de PALETA_CALOR) para mapas
# categóricos de 4 classes, ex. "prioridade" — mantém a mesma família de
# cor do score contínuo que embasa a classificação.
CORES_CALOR_4 = ["#eabc66", "#f9a05e", "#ec6c51", "#a6311f"]
