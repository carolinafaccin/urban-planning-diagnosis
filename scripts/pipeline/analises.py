"""
analises.py
--------------
O que faz   : Calcula o score de prioridade por hexágono (mapas 16 e 17) e as
              análises derivadas de acesso. Lê h3_indicadores do GeoPackage
              final e grava h3_sintese (com score e classe de prioridade) +
              cobertura de transporte no mesmo .gpkg.
Camadas     : h3_sintese, cobertura_onibus (e raio_ancora, se a âncora existir)
Requer      : build_geopackage.py já rodado.

Score de prioridade
-------------------
Cada indicador é normalizado [0,1] DENTRO da área (min-max) e combinado pelos
pesos de H3_PESOS (config.py). Direção: maior = mais prioritário (mais calor,
mais déficit de verde, mais impermeável, mais vulnerável, mais déficit de
arborização).

Hexágonos SEM domicílio (córrego, áreas verdes — onde algumas intervenções se
localizam) não têm indicadores sociais. Em vez de virarem NaN ou zero, o score
é calculado sobre os indicadores disponíveis (os físicos), com os pesos
renormalizados. A coluna `tem_populacao` distingue os dois casos, e
`score_social`/`score_fisico` ficam separados para leitura no QGIS.

Cada indicador aceita mais de uma fonte (ex.: LST do Cool Cities OU do GEE),
então o mesmo script serve a cidades com e sem Cool Cities. Mesmo mecanismo
usado para preferir dado MUNICIPAL sobre nacional/global quando disponível
(ver `deficit_verde`: `municipal_pct_verde`, do indicadores_municipais.py,
vem primeiro — cidade sem dado municipal cai para Cool Cities/GEE igual a
antes). Ver framework de 3 categorias no CLAUDE.md.

Para adaptar: ajuste H3_PESOS no config.py. As fontes de cada indicador estão
              em INDICADORES abaixo (primeira coluna existente vence).

Como rodar  : cd projetos/campinas
              python ../../scripts/pipeline/analises.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

# Preenchidos por main(cfg) — usados como globais pelas funções auxiliares
# abaixo (calcular_score, cobertura_onibus, raio_ancora), chamadas de dentro
# de main.
ANCORA_COORD = BBOX = CRS_PROJETO = CRS_WGS84 = GPKG_PATH = H3_PESOS = RAIO_ANCORA = None

# indicador (chave de H3_PESOS) → definição de como obtê-lo.
#   fontes    : colunas candidatas, em ordem de preferência (1ª existente vence)
#   transform : função col->série normalizável (maior = pior). None = usa direto.
#   social    : True se depende de população (nulo em hexágono sem domicílio)
INDICADORES = {
    "lst_mean":        dict(fontes=["ccl_lst", "gee_lst"], transform=None, social=False),
    "deficit_verde":   dict(fontes=["municipal_pct_verde", "ccl_frac_veg", "gee_ndvi_pct"],
                            transform=lambda s: 100 - s, social=False),
    "pct_impermeavel": dict(fontes=["pct_construido", "pct_urbano"], transform=None, social=False),
    "vuln_social":     dict(fontes=["renda_media_norm"], transform=None, social=True),
    "deficit_arb":     dict(fontes=["pct_sem_arb"], transform=None, social=True),
}

BUFFER_ONIBUS = 400  # m — cobertura de caminhada até ponto de ônibus


def normalizar(serie):
    """Min-max para [0,1]. Série constante/vazia → zeros."""
    s = pd.to_numeric(serie, errors="coerce")
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or hi == lo:
        return pd.Series(0.0, index=s.index)
    return (s - lo) / (hi - lo)


def resolver_fonte(hexg, fontes):
    for col in fontes:
        if col in hexg.columns:
            return col
    return None


def calcular_score(hexg):
    norm_cols, sociais = {}, {}
    for ind, cfg in INDICADORES.items():
        peso = H3_PESOS.get(ind, 0)
        if peso == 0:
            continue
        col = resolver_fonte(hexg, cfg["fontes"])
        if col is None:
            print(f"  [aviso] indicador '{ind}' sem fonte disponível — ignorado no score.")
            continue
        valores = hexg[col]
        if cfg["transform"]:
            valores = cfg["transform"](pd.to_numeric(valores, errors="coerce"))
        norm_cols[ind] = normalizar(valores)
        sociais[ind] = cfg["social"]

    normdf = pd.DataFrame(norm_cols, index=hexg.index)
    pesos = pd.Series({k: H3_PESOS[k] for k in norm_cols})

    # score físico e social separados (para leitura), depois o composto com
    # pesos renormalizados sobre os indicadores disponíveis por hexágono.
    fis = [k for k in norm_cols if not sociais[k]]
    soc = [k for k in norm_cols if sociais[k]]

    def combinar(cols, linha_valida):
        if not cols:
            return pd.Series(np.nan, index=hexg.index)
        sub = normdf[cols]
        w = pesos[cols]
        num = (sub * w).sum(axis=1, min_count=1)
        den = sub.notna().mul(w).sum(axis=1)
        return (num / den).where(den > 0)

    hexg["score_fisico"] = combinar(fis, None)
    hexg["score_social"] = combinar(soc, None)

    # Composto: média ponderada de TODOS os indicadores presentes na linha;
    # onde o social falta (hexágono sem população), sobram só os físicos e os
    # pesos se renormalizam automaticamente (den = soma dos pesos presentes).
    num = (normdf * pesos).sum(axis=1, min_count=1)
    den = normdf.notna().mul(pesos).sum(axis=1)
    hexg["score_prioridade"] = (num / den).where(den > 0)
    return hexg


def classificar(score):
    return pd.cut(
        score, bins=[-0.001, 0.25, 0.50, 0.75, 1.001],
        labels=["baixa", "média", "alta", "muito alta"],
    )


def cobertura_onibus(hexg):
    """Buffer de 400 m nos pontos de ônibus → área com acesso a transporte."""
    try:
        pontos = gpd.read_file(GPKG_PATH, layer="pontos_onibus").to_crs(CRS_PROJETO)
    except Exception:
        print("  [aviso] sem camada pontos_onibus — cobertura de ônibus pulada.")
        return None
    if pontos.empty:
        return None
    cobertura = pontos.buffer(BUFFER_ONIBUS).union_all()
    return gpd.GeoDataFrame({"raio_m": [BUFFER_ONIBUS]}, geometry=[cobertura], crs=CRS_PROJETO)


def raio_ancora(hexg):
    """Raio de caminhabilidade em torno da âncora, se ela cair dentro do bbox."""
    lat, lon = ANCORA_COORD
    if not (BBOX["south"] <= lat <= BBOX["north"] and BBOX["west"] <= lon <= BBOX["east"]):
        print(f"  [aviso] ANCORA_COORD {ANCORA_COORD} está fora do BBOX — raio_ancora "
              f"não gerado (confirme ANCORA_COORD no config.py).")
        return None
    ponto = gpd.GeoSeries.from_xy([lon], [lat], crs=CRS_WGS84).to_crs(CRS_PROJETO)
    return gpd.GeoDataFrame({"raio_m": [RAIO_ANCORA]},
                            geometry=[ponto.buffer(RAIO_ANCORA).iloc[0]], crs=CRS_PROJETO)


def main(cfg):
    global ANCORA_COORD, BBOX, CRS_PROJETO, CRS_WGS84, GPKG_PATH, H3_PESOS, RAIO_ANCORA

    ANCORA_COORD = cfg.ANCORA_COORD
    BBOX = cfg.BBOX
    CRS_PROJETO = cfg.CRS_PROJETO
    CRS_WGS84 = cfg.CRS_WGS84
    GPKG_PATH = cfg.GPKG_PATH
    H3_PESOS = cfg.H3_PESOS
    RAIO_ANCORA = cfg.RAIO_ANCORA

    hexg = gpd.read_file(GPKG_PATH, layer="h3_indicadores")
    hexg["tem_populacao"] = hexg["qtd_dom"].fillna(0) > 0

    hexg = calcular_score(hexg)
    hexg["prioridade"] = classificar(hexg["score_prioridade"])

    hexg.to_file(GPKG_PATH, layer="h3_sintese", driver="GPKG")
    print(f"  [h3_sintese] {len(hexg)} hexágonos com score → {GPKG_PATH.name}")

    dist = hexg["prioridade"].value_counts().reindex(["baixa", "média", "alta", "muito alta"])
    print("\nDistribuição de prioridade:")
    print(dist.to_string())

    cob = cobertura_onibus(hexg)
    if cob is not None:
        cob.to_file(GPKG_PATH, layer="cobertura_onibus", driver="GPKG")
        print(f"\n  [cobertura_onibus] buffer {BUFFER_ONIBUS} m salvo.")

    raio = raio_ancora(hexg)
    if raio is not None:
        raio.to_file(GPKG_PATH, layer="raio_ancora", driver="GPKG")
        print(f"  [raio_ancora] raio {RAIO_ANCORA} m salvo.")

    print("\nConcluído.")


if __name__ == "__main__":
    sys.path.insert(0, str(Path.cwd()))
    import config
    main(config)
