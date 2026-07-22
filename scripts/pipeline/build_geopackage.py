"""
build_geopackage.py
----------------------
O que faz   : Consolida tudo no GeoPackage final do projeto. Junta os
              enriquecimentos por hexágono (Censo dasimétrico + uso do solo +
              MapBiomas + Cool Cities + queimadas + GEE, quando houver) na
              malha H3, calcula a fração construída por hexágono a partir das
              edificações do Overture, e copia as camadas vetoriais para um
              único .gpkg pronto para o QGIS.
Camadas     : h3_indicadores (hexágonos com todos os indicadores, sem score)
              + viario, edificacoes, setores_censitarios, pontos_onibus,
                ciclovia, parques_osm, app_corregos, pais/uf/municipios_uf
                (mapa de localização, ver download_ibge.py), as camadas
                municipais e locais que existirem
              + _metadados
Saída       : {DATA_DIR}/{PROJECT_NAME}.gpkg
Requer      : 07 (h3_base) e, idealmente, 08/10/11/03/04/05/09.
              Enriquecimentos ausentes são só avisados — o build segue com
              o que existe.

Viário: se {DATA_DIR}/viario_enriquecido.gpkg existir (gerado pelo
dados_municipais.py quando há classificacao_viaria municipal), ele é
usado no lugar do viário puro do osm.gpkg — mesma topologia OSM, com a coluna
extra pmc_classifica anexada (primeira fonte existente vence, mesmo
mecanismo do analises.py::INDICADORES). A camada municipal nunca substitui
a topologia, só a enriquece.

O score de prioridade e as análises derivadas ficam no analises.py, que lê
h3_indicadores e grava h3_sintese neste mesmo .gpkg.

Para adaptar: nada. Descobre as fontes pelos caminhos do config.py.

Como rodar  : cd projetos/campinas
              python ../../scripts/pipeline/build_geopackage.py
"""

import sys
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd

# Preenchidos por main(cfg) — usados como globais por fracao_construida(),
# chamada de dentro de main.
CRS_PROJETO = None
EDIF_GPKG_PATH = None


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


def main(cfg):
    global CRS_PROJETO, EDIF_GPKG_PATH

    CRS_PROJETO = cfg.CRS_PROJETO
    DATA_DIR = cfg.DATA_DIR
    PROCESSED_DIR = cfg.PROCESSED_DIR
    GPKG_PATH = cfg.GPKG_PATH

    h3_gpkg_path = DATA_DIR / "h3.gpkg"
    EDIF_GPKG_PATH = DATA_DIR / "edificacoes.gpkg"
    viario_enriquecido_path = DATA_DIR / "viario_enriquecido.gpkg"
    municipais_gpkg_path = DATA_DIR / "municipais.gpkg"

    # Enriquecimentos por hexágono (parquet, chaveados por h3_id)
    enriquecimentos = [
        PROCESSED_DIR / "h3_mapbiomas.parquet",
        PROCESSED_DIR / "h3_cool_cities.parquet",
        PROCESSED_DIR / "h3_queimadas.parquet",
        PROCESSED_DIR / "h3_gee.parquet",  # opcional (fallback GEE)
        PROCESSED_DIR / "h3_municipal.parquet",  # opcional (fallback municipal)
    ]

    # Camadas vetoriais a copiar: (gpkg de origem, nome da camada). O viário
    # prefere a versão enriquecida com classificação municipal, se existir
    # (primeira fonte existente vence — nunca as duas ao mesmo tempo).
    vetores = [
        (viario_enriquecido_path if viario_enriquecido_path.exists() else DATA_DIR / "osm.gpkg", "viario"),
        (DATA_DIR / "osm.gpkg", "parques_osm"),
        (DATA_DIR / "osm.gpkg", "ciclovia"),
        (DATA_DIR / "osm.gpkg", "pontos_onibus"),
        (DATA_DIR / "ibge.gpkg", "setores_censitarios"),
        (EDIF_GPKG_PATH, "edificacoes"),
        (DATA_DIR / "app_corregos.gpkg", "app_corregos"),  # opcional (05)
        # mapa de localização (país/UF/município) — ver nota no download_ibge.py:
        # únicas camadas do pipeline que NÃO são recortadas pelo BBOX do projeto.
        (DATA_DIR / "localizacao.gpkg", "pais"),
        (DATA_DIR / "localizacao.gpkg", "uf"),
        (DATA_DIR / "localizacao.gpkg", "municipios_uf"),
    ]

    print("Montando hexágonos com todos os indicadores...")
    hex_gdf = gpd.read_file(h3_gpkg_path, layer="h3_base")

    for caminho in enriquecimentos:
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

    for origem, camada in vetores:
        if not origem.exists():
            print(f"  [aviso] {origem.name}::{camada} não existe — pulado.")
            continue
        gdf = gpd.read_file(origem, layer=camada).to_crs(CRS_PROJETO)
        gdf.to_file(GPKG_PATH, layer=camada, driver="GPKG")
        metadados.append({"camada": camada, "n_feicoes": len(gdf),
                          "fonte": origem.name, "gerado_em": str(date.today())})
        print(f"  [{camada}] {len(gdf)} feições copiadas")

    # Camadas municipais (o que o 04 tiver produzido) — 'viario' fica de fora
    # daqui porque já foi resolvido em vetores (enriquecido ou não).
    if municipais_gpkg_path.exists():
        import pyogrio
        for camada in pyogrio.list_layers(municipais_gpkg_path)[:, 0]:
            gdf = gpd.read_file(municipais_gpkg_path, layer=camada).to_crs(CRS_PROJETO)
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

    print(f"\nConcluído. GeoPackage final: {GPKG_PATH}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from _projeto import carregar_config
    main(carregar_config())
