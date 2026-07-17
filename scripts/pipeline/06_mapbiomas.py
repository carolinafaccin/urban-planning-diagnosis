"""
06_mapbiomas.py
---------------
O que faz   : Calcula a composição de cobertura do solo (MapBiomas) por
              hexágono da malha H3, via estatística zonal categórica, e deriva
              percentuais semânticos (verde, impermeável, água...).
Saída       : {DATA_DIR}/processed/h3_mapbiomas.parquet (h3_id → pct_*)
              (o 09_build_geopackage.py junta isto à geometria da malha)
Fonte       : raw_dir/mapbiomas/uso-e-cobertura_colecao-10/brazil_coverage_2024.tif
              (Coleção 10, uso e cobertura 2024; raster nacional EPSG:4326,
              ~30 m, uint8 com o código da classe MapBiomas por pixel)
Requer      : 05_h3_dasimetrico.py já rodado (usa a geometria de h3_base).

Notas
-----
- O raster é lido em janela (rasterstats abre só a área sob os hexágonos), então
  não importa ser um .tif do Brasil inteiro.
- Res10 (~123 m) contém ~16 pixels de 30 m: os percentuais são aproximações
  razoáveis de composição, não contagem fina.
- A cobertura vegetal fina do diagnóstico vem do Cool Cities (07); aqui o
  MapBiomas dá a base morfológica de cobertura do solo (mapa 10).

Para adaptar: aponte MAPBIOMAS_TIF para a coleção/ano desejado. Os grupos
              semânticos (GRUPOS) seguem a legenda MapBiomas e podem ser
              ajustados sem tocar no resto.

Como rodar  : cd projetos/campinas
              python ../../scripts/pipeline/06_mapbiomas.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import rasterio
from rasterstats import zonal_stats

sys.path.insert(0, str(Path.cwd()))
from config import DATA_DIR, PROCESSED_DIR, RAW_CATALOG  # noqa: E402

H3_GPKG_PATH = DATA_DIR / "h3.gpkg"
OUT_PATH = PROCESSED_DIR / "h3_mapbiomas.parquet"
MAPBIOMAS_TIF = RAW_CATALOG / "mapbiomas" / "uso-e-cobertura_colecao-10" / "brazil_coverage_2024.tif"

# Grupos semânticos da legenda MapBiomas (códigos de classe → agregação).
# Referência: legenda da Coleção MapBiomas (mapbiomas.org).
GRUPOS = {
    "pct_floresta":     [1, 3, 4, 5, 6, 49],           # formações florestais
    "pct_veg_natural":  [10, 11, 12, 32, 29, 50, 13],  # campestre/úmida natural não-florestal
    "pct_agropecuaria": [14, 15, 18, 19, 39, 20, 40, 62, 41, 36, 46, 47, 35, 48, 9, 21],
    "pct_urbano":       [24],                           # área urbanizada
    "pct_outros_naoveg":[22, 23, 25, 30],               # praia/duna, mineração, outras não-veg.
    "pct_agua":         [26, 33, 31],                   # rios/lagos/aquicultura
}


def main():
    if not MAPBIOMAS_TIF.exists():
        raise FileNotFoundError(f"Raster MapBiomas não encontrado: {MAPBIOMAS_TIF}")

    hex_gdf = gpd.read_file(H3_GPKG_PATH, layer="h3_base")[["h3_id", "geometry"]]

    with rasterio.open(MAPBIOMAS_TIF) as src:
        raster_crs = src.crs
    hex_raster = hex_gdf.to_crs(raster_crs)

    print(f"Estatística zonal categórica em {len(hex_gdf)} hexágonos "
          f"({MAPBIOMAS_TIF.name})...")
    stats = zonal_stats(
        hex_raster, str(MAPBIOMAS_TIF), categorical=True, nodata=0, geojson_out=False
    )

    # stats: lista de dicts {codigo_classe: n_pixels}. Converte para % por grupo.
    linhas = []
    for h3_id, contagem in zip(hex_gdf["h3_id"], stats):
        total = sum(contagem.values())
        linha = {"h3_id": h3_id}
        for nome, codigos in GRUPOS.items():
            n = sum(contagem.get(c, 0) for c in codigos)
            linha[nome] = (100.0 * n / total) if total else None
        linhas.append(linha)

    df = pd.DataFrame(linhas)
    df.to_parquet(OUT_PATH)
    print(f"\n  [h3_mapbiomas] {len(df)} hexágonos → {OUT_PATH.name}")
    print("\nComposição média na área (% do hexágono):")
    print(df[list(GRUPOS)].describe().round(1).loc[["mean", "min", "max"]].to_string())


if __name__ == "__main__":
    main()
    print("\nConcluído.")
