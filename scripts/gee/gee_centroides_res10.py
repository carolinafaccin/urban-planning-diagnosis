"""
gee_centroides_res10.py
-----------------------
O que faz   : Gera o CSV de centróides dos hexágonos H3 res10 da área de
              estudo, para subir como asset no Google Earth Engine e amostrar
              LST/NDVI (fallback quando não há Cool Cities, e base do catálogo
              nacional). Espelha o fluxo do climate-injustice-index (que fez
              isso em res9 para o Brasil inteiro).
Saída       : {DATA_DIR}/processed/centroides_h3_res10.csv
              colunas: h3_id, cd_setor, cd_uf, qtd_dom, lat, lon
Requer      : 05_h3_dasimetrico.py já rodado (usa h3_base + os domicílios).

Sobre o asset / escala
----------------------
Para a área do piloto são ~300 pontos — pequeno. O CSV existe para (a)
padronizar com o fluxo nacional e (b) alimentar o script GEE
(gee_lst_ndvi_res10.js), que faz reduceRegions sobre um buffer no centróide
(~76 m = circunraio do H3 res10) e exporta por UF.

Para o CATÁLOGO NACIONAL: rode a mesma lógica sobre a malha nacional de
setores (ver rebuild_h3_base do climate-injustice-index) em vez de h3_base.
Aqui geramos só a área do projeto; a versão nacional é um job separado, seu.

Cada hexágono recebe um cd_setor representativo (o de maior nº de domicílios),
só para carregar metadado — a análise não depende dessa atribuição única.

Como rodar  : cd projetos/campinas
              python ../../scripts/gee/gee_centroides_res10.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import h3
import pandas as pd

sys.path.insert(0, str(Path.cwd()))
from config import DATA_DIR, IBGE_COD_MUN, PROCESSED_DIR  # noqa: E402

H3_GPKG_PATH = DATA_DIR / "h3.gpkg"
DOM_H3_SETOR_PATH = PROCESSED_DIR / "cnefe_dom_h3_setor.parquet"
OUT_CSV = PROCESSED_DIR / "centroides_h3_res10.csv"

COD_UF = int(IBGE_COD_MUN[:2])


def main():
    hexg = gpd.read_file(H3_GPKG_PATH, layer="h3_base")[["h3_id", "qtd_dom"]]

    # cd_setor representativo = o de maior nº de domicílios no hexágono
    dom = pd.read_parquet(DOM_H3_SETOR_PATH)
    setor_rep = (
        dom.sort_values("qtd_dom", ascending=False)
        .drop_duplicates("h3_id")[["h3_id", "cd_setor"]]
    )
    df = hexg.merge(setor_rep, on="h3_id", how="left")

    # centróide (lat, lon) de cada célula
    latlon = [h3.cell_to_latlng(h) for h in df["h3_id"]]
    df["lat"] = [p[0] for p in latlon]
    df["lon"] = [p[1] for p in latlon]
    df["cd_uf"] = COD_UF

    df = df[["h3_id", "cd_setor", "cd_uf", "qtd_dom", "lat", "lon"]]
    df.to_csv(OUT_CSV, index=False)
    print(f"  [centroides] {len(df)} hexágonos → {OUT_CSV}")
    print("\nSuba este CSV como asset no GEE (Assets → New → CSV, com lat/lon) e "
          "aponte o gee_lst_ndvi_res10.js para ele.")


if __name__ == "__main__":
    main()
    print("\nConcluído.")
