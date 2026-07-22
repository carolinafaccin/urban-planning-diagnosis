"""
09_indicadores_municipais.py
----------------------------
O que faz   : Para as camadas municipais de CAMADAS_MUNICIPAIS com
              `indicador_score` preenchido (categoria 2 — fallback de
              indicador do score, ver CLAUDE.md), calcula o % de cobertura
              por hexágono da malha H3 (estatística de área, mesmo espírito
              do 08_mapbiomas.py) e grava colunas prefixadas `municipal_*`
              que o 14_analises.py passa a aceitar como PRIMEIRA opção de
              fonte (fallback: municipal → Cool Cities/GEE).
Saída       : {DATA_DIR}/processed/h3_municipal.parquet (h3_id → municipal_*)
Fonte       : {DATA_DIR}/municipais.gpkg (gerado pelo 04_dados_municipais.py)
Requer      : 04_dados_municipais.py e 07_h3_dasimetrico.py já rodados.

Camadas com o mesmo `indicador_score` são UNIDAS antes da estatística de
área (ex.: areas_verdes + bosques_parques + vegetacao_natural → um único
polígono "verde municipal" por hexágono) — evita contar a mesma área verde
duas vezes onde as camadas se sobrepõem (ver aviso de duplicidade no
README.md do raw_dir municipal).

Tolerante: sem municipais.gpkg, ou sem nenhuma camada com indicador_score
preenchido, este script não grava nada — o 14_analises.py cai para as
fontes nacionais/globais (Cool Cities/GEE) normalmente.

Para adaptar: nada. Descobre as camadas pelo CAMADAS_MUNICIPAIS do config.py.

Como rodar  : cd projetos/campinas
              python ../../scripts/pipeline/09_indicadores_municipais.py
"""

import sys
from collections import defaultdict
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio

sys.path.insert(0, str(Path.cwd()))
from config import CAMADAS_MUNICIPAIS, DATA_DIR, PROCESSED_DIR  # noqa: E402

H3_GPKG_PATH = DATA_DIR / "h3.gpkg"
MUNICIPAIS_GPKG_PATH = DATA_DIR / "municipais.gpkg"
OUT_PATH = PROCESSED_DIR / "h3_municipal.parquet"

# indicador_score -> nome da coluna de saída (% de cobertura por hexágono)
COLUNA_POR_INDICADOR = {
    "deficit_verde": "municipal_pct_verde",
}


def camadas_por_indicador():
    """indicador_score -> lista de nomes de camada (chaves de CAMADAS_MUNICIPAIS)."""
    grupos = defaultdict(list)
    for nome, cfg in CAMADAS_MUNICIPAIS.items():
        if cfg.get("indicador_score"):
            grupos[cfg["indicador_score"]].append(nome)
    return grupos


def pct_cobertura(hex_gdf, camadas_presentes):
    """% da área do hexágono coberta pela união GEOMÉTRICA das camadas dadas
    (dissolve antes da estatística de área — evita contar duas vezes onde
    camadas municipais se sobrepõem, ex.: areas_verdes × vegetacao_natural,
    já sinalizado como possível no README.md do raw_dir municipal)."""
    partes = [gpd.read_file(MUNICIPAIS_GPKG_PATH, layer=c)[["geometry"]] for c in camadas_presentes]
    concat = pd.concat(partes, ignore_index=True) if len(partes) > 1 else partes[0]
    dissolvido = gpd.GeoSeries([concat.geometry.union_all()], crs=hex_gdf.crs)
    uniao = gpd.GeoDataFrame(geometry=dissolvido)

    inter = gpd.overlay(hex_gdf[["h3_id", "geometry"]], uniao, how="intersection")
    if inter.empty:
        return pd.Series(0.0, index=hex_gdf["h3_id"])
    inter["area"] = inter.geometry.area
    agg = inter.groupby("h3_id")["area"].sum()

    area_hex = hex_gdf.set_index("h3_id").geometry.area
    pct = (100.0 * agg / area_hex).reindex(hex_gdf["h3_id"]).fillna(0.0)
    return pct


def main():
    grupos = camadas_por_indicador()
    if not grupos:
        print("Nenhuma camada municipal com indicador_score no config.py — nada a fazer.")
        return
    if not MUNICIPAIS_GPKG_PATH.exists():
        print(f"[aviso] {MUNICIPAIS_GPKG_PATH.name} não encontrado — rode o "
              "04_dados_municipais.py antes. Nada será gravado.")
        return

    camadas_no_gpkg = set(pyogrio.list_layers(MUNICIPAIS_GPKG_PATH)[:, 0])
    hex_gdf = gpd.read_file(H3_GPKG_PATH, layer="h3_base")[["h3_id", "geometry"]]

    resultado = pd.DataFrame({"h3_id": hex_gdf["h3_id"]})
    for indicador, camadas in grupos.items():
        presentes = [c for c in camadas if c in camadas_no_gpkg]
        if not presentes:
            print(f"  [pulado] '{indicador}': nenhuma das camadas {camadas} "
                  "está em municipais.gpkg (não baixada ou fora do bbox).")
            continue
        coluna = COLUNA_POR_INDICADOR.get(indicador, f"municipal_{indicador}")
        resultado[coluna] = pct_cobertura(hex_gdf, presentes).values
        print(f"  [{coluna}] de {presentes} — média {resultado[coluna].mean():.1f}% "
              f"de cobertura por hexágono")

    if len(resultado.columns) == 1:
        print("\nNenhum indicador municipal calculado.")
        return

    resultado.to_parquet(OUT_PATH)
    print(f"\n  [h3_municipal] {len(resultado)} hexágonos, "
          f"{len(resultado.columns)-1} coluna(s) → {OUT_PATH.name}")


if __name__ == "__main__":
    main()
    print("\nConcluído.")
