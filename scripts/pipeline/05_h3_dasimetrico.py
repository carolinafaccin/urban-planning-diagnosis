"""
05_h3_dasimetrico.py
--------------------
O que faz   : Monta a malha H3 (res do config) sobre a área de estudo e é a
              espinha dorsal da síntese: recebe os indicadores do Censo por
              interpolação dasimétrica (peso = domicílios do CNEFE) e o uso do
              solo do CNEFE. Os scripts de raster (06 MapBiomas, 07 Cool Cities,
              queimadas, GEE) anexam suas colunas a esta mesma malha depois.
Camadas     : h3_base (no {DATA_DIR}/h3.gpkg)
Requer      : 02_download_ibge.py e 04_cnefe.py já rodados.
Fonte       : {DATA_DIR}/ibge.gpkg (valores por setor) + os parquets do 04.

Interpolação dasimétrica (setor → hexágono)
-------------------------------------------
As variáveis do Censo aqui (renda média, percentuais) são INTENSIVAS
(médias/taxas por domicílio), não contagens. A agregação correta é a MÉDIA
dos setores que o hexágono cruza, PONDERADA pelos domicílios do CNEFE em cada
parte:

    w(h,s)   = domicilios(h,s) / Σ_s domicilios(h,s)     # soma 1 por HEXÁGONO
    Valor(h) = Σ_s Valor(s) × w(h,s)

Isso difere da fórmula de variáveis extensivas do climate-injustice-index
(ValorHex = ValorSetor × domicilios(h,s)/total_setor), que distribui um TOTAL
de setor entre hexágonos e só vale para contagens — aplicá-la a uma média
per-domicílio subestima o valor (um hexágono tem só uma fração dos domicílios
do setor). Domicílios por setor são contados no setor INTEIRO (o 04 capturou
além do bbox), mas para média intensiva o que importa é o peso relativo dentro
do hexágono. Ver o cabeçalho do 04_cnefe.py.

Hexágonos sem domicílio (córrego, áreas verdes) são MANTIDOS na malha: os
indicadores sociais ficam nulos ali (não há a quem atribuir), mas eles seguem
recebendo os indicadores físicos (calor, verde, impermeável) dos scripts de
raster. O 11_analises.py trata esses nulos explicitamente ao compor o score —
são justamente onde algumas intervenções (ex.: parques lineares) podem se localizar.

Para adaptar: ajuste H3_RESOLUCAO no config.py. As variáveis interpoladas são
              detectadas por VARS_DASIMETRICAS abaixo.

Como rodar  : cd projetos/campinas
              python ../../scripts/pipeline/05_h3_dasimetrico.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import h3
import pandas as pd
from shapely.geometry import Polygon

sys.path.insert(0, str(Path.cwd()))
from config import (  # noqa: E402
    BBOX,
    CRS_PROJETO,
    CRS_WGS84,
    DATA_DIR,
    H3_RESOLUCAO,
    PROCESSED_DIR,
)

H3_GPKG_PATH = DATA_DIR / "h3.gpkg"
IBGE_GPKG_PATH = DATA_DIR / "ibge.gpkg"
USO_H3_PATH = PROCESSED_DIR / "cnefe_uso_h3.parquet"
DOM_H3_SETOR_PATH = PROCESSED_DIR / "cnefe_dom_h3_setor.parquet"

# Variáveis do Censo (camada setores_censitarios) que vão para os hexágonos por
# interpolação dasimétrica. São valores já por-domicílio/percentuais, logo a
# média ponderada por domicílios é a agregação correta.
VARS_DASIMETRICAS = [
    "renda_media",
    "renda_media_norm",
    "pct_sem_arb",
    "pct_sem_ilum",
    "pct_sem_calcada",
    "pct_sem_pavimento",
]


def malha_h3_do_bbox(bbox, resolucao):
    """Todos os hexágonos H3 cujo interior cobre o polígono do bbox."""
    poligono = h3.LatLngPoly(
        [
            (bbox["south"], bbox["west"]),
            (bbox["south"], bbox["east"]),
            (bbox["north"], bbox["east"]),
            (bbox["north"], bbox["west"]),
        ]
    )
    cells = h3.h3shape_to_cells(poligono, resolucao)
    geoms = [Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(c)]) for c in cells]
    return gpd.GeoDataFrame({"h3_id": list(cells)}, geometry=geoms, crs=CRS_WGS84).to_crs(CRS_PROJETO)


def interpolar_dasimetrico(setores, dom_h3_setor):
    """Média dos setores por hexágono, ponderada por domicílios do CNEFE.

    Retorna um DataFrame indexado por h3_id com as variáveis interpoladas e a
    contagem de domicílios (qtd_dom) por hexágono. Para cada variável, setores
    sem valor (NaN) são ignorados e o peso é renormalizado sobre os presentes.
    """
    valores = setores[["cd_setor", *VARS_DASIMETRICAS]].copy()
    m = dom_h3_setor.merge(valores, on="cd_setor", how="left")

    saida = {}
    for var in VARS_DASIMETRICAS:
        peso = m["qtd_dom"].where(m[var].notna())      # ignora setor sem o valor
        num = (m[var] * peso)
        g = m.assign(_num=num, _den=peso).groupby("h3_id")
        saida[var] = g["_num"].sum(min_count=1) / g["_den"].sum(min_count=1)

    resultado = pd.DataFrame(saida)
    resultado["qtd_dom"] = m.groupby("h3_id")["qtd_dom"].sum()
    return resultado.reset_index()


def main():
    print(f"Montando malha H3 res {H3_RESOLUCAO} sobre o bbox...")
    hex_gdf = malha_h3_do_bbox(BBOX, H3_RESOLUCAO)
    print(f"  {len(hex_gdf)} hexágonos cobrindo a área de estudo.")

    setores = gpd.read_file(IBGE_GPKG_PATH, layer="setores_censitarios")
    dom = pd.read_parquet(DOM_H3_SETOR_PATH)
    uso = pd.read_parquet(USO_H3_PATH)

    interp = interpolar_dasimetrico(setores, dom)
    hex_gdf = hex_gdf.merge(interp, on="h3_id", how="left")
    hex_gdf = hex_gdf.merge(uso, on="h3_id", how="left")

    # Hexágonos sem CNEFE: domicílios/uso = 0; variáveis sociais ficam NaN
    hex_gdf["qtd_dom"] = hex_gdf["qtd_dom"].fillna(0).astype(int)
    cat_cols = [c for c in hex_gdf.columns if c.startswith("cat_") or c == "total_enderecos"]
    hex_gdf[cat_cols] = hex_gdf[cat_cols].fillna(0).astype(int)

    habitados = int((hex_gdf["qtd_dom"] > 0).sum())
    print(f"  {habitados} de {len(hex_gdf)} hexágonos têm domicílios (o resto fica "
          f"com indicadores sociais nulos — esperado).")

    hex_gdf.to_file(H3_GPKG_PATH, layer="h3_base", driver="GPKG")
    print(f"\n  [h3_base] {len(hex_gdf)} hexágonos salvos em {H3_GPKG_PATH}")

    print("\nResumo dos indicadores interpolados (hexágonos habitados):")
    hab = hex_gdf[hex_gdf["qtd_dom"] > 0]
    print(hab[["qtd_dom", "renda_media", "pct_sem_arb", "pct_sem_ilum"]].describe().round(1).to_string())


if __name__ == "__main__":
    main()
    print("\nConcluído.")
