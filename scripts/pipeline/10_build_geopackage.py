"""
10_build_geopackage.py
----------------------
O que faz   : Consolida tudo no GeoPackage final do projeto. Junta os
              enriquecimentos por hexágono (Censo dasimétrico + uso do solo +
              MapBiomas + Cool Cities + queimadas + GEE, quando houver) na
              malha H3, calcula a fração construída por hexágono a partir das
              edificações do Overture, e copia as camadas vetoriais para um
              único .gpkg pronto para o QGIS.
Camadas     : h3_indicadores (hexágonos com todos os indicadores, sem score)
              + viario, edificacoes, setores_censitarios, pontos_onibus,
                ciclovia, parques_osm, as camadas municipais e locais que
                existirem
              + _metadados
Saída       : {DATA_DIR}/{PROJECT_NAME}.gpkg
Requer      : 05 (h3_base) e, idealmente, 06/07/08/03/03b/06b. Enriquecimentos
              ausentes são só avisados — o build segue com o que existe.

Viário: se {DATA_DIR}/viario_enriquecido.gpkg existir (gerado pelo
03b_dados_municipais.py quando há classificacao_viaria municipal), ele é
usado no lugar do viário puro do osm.gpkg — mesma topologia OSM, com a coluna
extra pmc_classifica anexada (primeira fonte existente vence, mesmo
mecanismo do 11_analises.py::INDICADORES). A camada municipal nunca substitui
a topologia, só a enriquece.

O score de prioridade e as análises derivadas ficam no 11_analises.py, que lê
h3_indicadores e grava h3_sintese neste mesmo .gpkg.

Para adaptar: nada. Descobre as fontes pelos caminhos do config.py.

Como rodar  : cd projetos/campinas
              python ../../scripts/pipeline/10_build_geopackage.py
"""

import sys
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path.cwd()))
from config import (  # noqa: E402
    CRS_PROJETO,
    DATA_DIR,
    GPKG_PATH,
    PROCESSED_DIR,
    PROJECT_NAME,
)

H3_GPKG_PATH = DATA_DIR / "h3.gpkg"
EDIF_GPKG_PATH = DATA_DIR / "edificacoes.gpkg"
VIARIO_ENRIQUECIDO_PATH = DATA_DIR / "viario_enriquecido.gpkg"
MUNICIPAIS_GPKG_PATH = DATA_DIR / "municipais.gpkg"

# Enriquecimentos por hexágono (parquet, chaveados por h3_id)
ENRIQUECIMENTOS = [
    PROCESSED_DIR / "h3_mapbiomas.parquet",
    PROCESSED_DIR / "h3_cool_cities.parquet",
    PROCESSED_DIR / "h3_queimadas.parquet",
    PROCESSED_DIR / "h3_gee.parquet",  # opcional (fallback GEE)
    PROCESSED_DIR / "h3_municipal.parquet",  # opcional (fallback municipal)
]

# Camadas vetoriais a copiar: (gpkg de origem, nome da camada). O viário
# prefere a versão enriquecida com classificação municipal, se existir
# (primeira fonte existente vence — nunca as duas ao mesmo tempo).
VETORES = [
    (VIARIO_ENRIQUECIDO_PATH if VIARIO_ENRIQUECIDO_PATH.exists() else DATA_DIR / "osm.gpkg", "viario"),
    (DATA_DIR / "osm.gpkg", "parques_osm"),
    (DATA_DIR / "osm.gpkg", "ciclovia"),
    (DATA_DIR / "osm.gpkg", "pontos_onibus"),
    (DATA_DIR / "ibge.gpkg", "setores_censitarios"),
    (EDIF_GPKG_PATH, "edificacoes"),
]


def fracao_construida(hex_gdf):
    """Área de edificações (Overture) por hexágono → pct_construido, n_edificacoes."""
    if not EDIF_GPKG_PATH.exists():
        print("  [aviso] sem edificacoes.gpkg — pct_construido não calculado (rode o 03).")
        hex_gdf["pct_construido"] = None
        hex_gdf["n_edificacoes"] = 0
        return hex_gdf

    edif = gpd.read_file(EDIF_GPKG_PATH, layer="edificacoes").to_crs(CRS_PROJETO)
    inter = gpd.overlay(
        hex_gdf[["h3_id", "geometry"]], edif[["geometry"]], how="intersection"
    )
    inter["area"] = inter.geometry.area
    agg = inter.groupby("h3_id").agg(area_construida=("area", "sum"),
                                     n_edificacoes=("area", "size")).reset_index()
    hex_gdf = hex_gdf.merge(agg, on="h3_id", how="left")
    hex_gdf["area_construida"] = hex_gdf["area_construida"].fillna(0)
    hex_gdf["n_edificacoes"] = hex_gdf["n_edificacoes"].fillna(0).astype(int)
    hex_gdf["pct_construido"] = 100.0 * hex_gdf["area_construida"] / hex_gdf.geometry.area
    return hex_gdf


def main():
    print("Montando hexágonos com todos os indicadores...")
    hex_gdf = gpd.read_file(H3_GPKG_PATH, layer="h3_base")

    for caminho in ENRIQUECIMENTOS:
        if caminho.exists():
            df = pd.read_parquet(caminho)
            novas = [c for c in df.columns if c != "h3_id"]
            hex_gdf = hex_gdf.merge(df, on="h3_id", how="left")
            print(f"  + {caminho.stem}: {len(novas)} colunas")
        else:
            print(f"  [aviso] ausente: {caminho.name} (rode o script correspondente)")

    hex_gdf = fracao_construida(hex_gdf)

    # Grava a camada de indicadores + vetores no gpkg final
    hex_gdf.to_file(GPKG_PATH, layer="h3_indicadores", driver="GPKG")
    print(f"\n  [h3_indicadores] {len(hex_gdf)} hexágonos, "
          f"{len(hex_gdf.columns)-1} colunas → {GPKG_PATH.name}")

    metadados = [{"camada": "h3_indicadores", "n_feicoes": len(hex_gdf),
                  "fonte": "05+06+07+08+03", "gerado_em": str(date.today())}]

    for origem, camada in VETORES:
        if not origem.exists():
            print(f"  [aviso] {origem.name}::{camada} não existe — pulado.")
            continue
        gdf = gpd.read_file(origem, layer=camada).to_crs(CRS_PROJETO)
        gdf.to_file(GPKG_PATH, layer=camada, driver="GPKG")
        metadados.append({"camada": camada, "n_feicoes": len(gdf),
                          "fonte": origem.name, "gerado_em": str(date.today())})
        print(f"  [{camada}] {len(gdf)} feições copiadas")

    # Camadas municipais (o que o 03b tiver produzido) — 'viario' fica de fora
    # daqui porque já foi resolvido em VETORES (enriquecido ou não).
    if MUNICIPAIS_GPKG_PATH.exists():
        import pyogrio
        for camada in pyogrio.list_layers(MUNICIPAIS_GPKG_PATH)[:, 0]:
            gdf = gpd.read_file(MUNICIPAIS_GPKG_PATH, layer=camada).to_crs(CRS_PROJETO)
            gdf.to_file(GPKG_PATH, layer=camada, driver="GPKG")
            metadados.append({"camada": camada, "n_feicoes": len(gdf),
                              "fonte": "municipal (PMC)", "gerado_em": str(date.today())})
            print(f"  [{camada}] {len(gdf)} feições (municipal)")

    # Camadas locais (o que o 09 tiver produzido)
    locais = DATA_DIR / "locais.gpkg"
    if locais.exists():
        import pyogrio
        for camada in pyogrio.list_layers(locais)[:, 0]:
            gdf = gpd.read_file(locais, layer=camada).to_crs(CRS_PROJETO)
            gdf.to_file(GPKG_PATH, layer=camada, driver="GPKG")
            metadados.append({"camada": camada, "n_feicoes": len(gdf),
                              "fonte": "locais.gpkg", "gerado_em": str(date.today())})
            print(f"  [{camada}] {len(gdf)} feições (local)")

    pd.DataFrame(metadados).to_csv(DATA_DIR / "_metadados.csv", index=False)
    print(f"\n  _metadados: {len(metadados)} camadas registradas.")


if __name__ == "__main__":
    main()
    print(f"\nConcluído. GeoPackage final: {GPKG_PATH}")
