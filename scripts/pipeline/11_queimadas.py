"""
11_queimadas.py
---------------
O que faz   : Conta focos de calor/queimadas (INPE) por hexágono da malha H3,
              somando todos os anos disponíveis. Gera o mapa de focos e um
              indicador possível para o score de prioridade.
Saída       : {DATA_DIR}/processed/h3_queimadas.parquet (h3_id → n_focos, ...)
Fonte       : raw_dir/inpe/queimadas/<ano>.csv (um CSV por ano, 2014–2025,
              com latitude/longitude e risco_fogo)
Requer      : 07_h3_dasimetrico.py já rodado (geometria/ids de h3_base).

Nota de expectativa
-------------------
Numa área urbana pequena os focos tendem a ser pouquíssimos ou zero (queimada
é fenômeno mais rural/periférico) — o mapa pode sair quase vazio. É incluído
mesmo assim: barato de rodar, e útil em diagnósticos de territórios com borda
rural. Hexágonos sem foco recebem n_focos = 0.

Para adaptar: nada específico. Usa o BBOX do config.py para recortar os focos.

Como rodar  : cd projetos/campinas
              python ../../scripts/pipeline/11_queimadas.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import h3
import pandas as pd

sys.path.insert(0, str(Path.cwd()))
from config import BBOX, DATA_DIR, H3_RESOLUCAO, PROCESSED_DIR, RAW_CATALOG  # noqa: E402

H3_GPKG_PATH = DATA_DIR / "h3.gpkg"
OUT_PATH = PROCESSED_DIR / "h3_queimadas.parquet"
QUEIMADAS_DIR = RAW_CATALOG / "inpe" / "queimadas"


def carregar_focos_bbox():
    """Lê todos os CSVs anuais, mantendo só focos dentro do BBOX."""
    partes = []
    for csv in sorted(QUEIMADAS_DIR.glob("*.csv")):
        df = pd.read_csv(csv, usecols=["latitude", "longitude", "risco_fogo"])
        dentro = df[
            df["latitude"].between(BBOX["south"], BBOX["north"])
            & df["longitude"].between(BBOX["west"], BBOX["east"])
        ]
        if len(dentro):
            partes.append(dentro)
        print(f"  {csv.name}: {len(dentro)} focos no bbox")
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(
        columns=["latitude", "longitude", "risco_fogo"]
    )


def main():
    hex_gdf = gpd.read_file(H3_GPKG_PATH, layer="h3_base")[["h3_id"]]

    print("Lendo focos de queimada (INPE)...")
    focos = carregar_focos_bbox()
    print(f"{len(focos)} focos no bbox (todos os anos).")

    if len(focos):
        focos["h3_id"] = [
            h3.latlng_to_cell(lat, lon, H3_RESOLUCAO)
            for lat, lon in zip(focos["latitude"], focos["longitude"])
        ]
        agg = focos.groupby("h3_id").agg(
            n_focos=("h3_id", "size"),
            risco_fogo_medio=("risco_fogo", "mean"),
        ).reset_index()
    else:
        agg = pd.DataFrame(columns=["h3_id", "n_focos", "risco_fogo_medio"])

    resultado = hex_gdf.merge(agg, on="h3_id", how="left")
    resultado["n_focos"] = resultado["n_focos"].fillna(0).astype(int)
    resultado.to_parquet(OUT_PATH)

    print(f"\n  [h3_queimadas] {len(resultado)} hexágonos "
          f"({int((resultado['n_focos'] > 0).sum())} com ao menos 1 foco) → {OUT_PATH.name}")


if __name__ == "__main__":
    main()
    print("\nConcluído.")
