"""
queimadas.py
---------------
O que faz   : Conta focos de calor/queimadas (INPE) por hexágono da malha H3,
              somando todos os anos disponíveis. Gera o mapa de focos e um
              indicador possível para o score de prioridade.
Saída       : {DATA_DIR}/processed/h3_queimadas.parquet (h3_id → n_focos, ...)
Fonte       : raw_dir/inpe/queimadas/<ano>.csv (um CSV por ano, 2014–2025,
              com latitude/longitude e risco_fogo)
Requer      : h3_dasimetrico.py já rodado (geometria/ids de h3_base).

Nota de expectativa
-------------------
Numa área urbana pequena os focos tendem a ser pouquíssimos ou zero (queimada
é fenômeno mais rural/periférico) — o mapa pode sair quase vazio. É incluído
mesmo assim: barato de rodar, e útil em diagnósticos de territórios com borda
rural. Hexágonos sem foco recebem n_focos = 0.

Para adaptar: nada específico. Usa o BBOX do config.py para recortar os focos.

Como rodar  : cd projetos/campinas
              python ../../scripts/pipeline/queimadas.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import h3
import pandas as pd

# Preenchidos por main(cfg) — usados como globais por carregar_focos_bbox(),
# chamada de dentro de main.
BBOX = None
QUEIMADAS_DIR = None


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


def main(cfg):
    global BBOX, QUEIMADAS_DIR

    BBOX = cfg.BBOX
    QUEIMADAS_DIR = cfg.RAW_CATALOG / "inpe" / "queimadas"
    h3_gpkg_path = cfg.DATA_DIR / "h3.gpkg"
    out_path = cfg.PROCESSED_DIR / "h3_queimadas.parquet"

    hex_gdf = gpd.read_file(h3_gpkg_path, layer="h3_base")[["h3_id"]]

    print("Lendo focos de queimada (INPE)...")
    focos = carregar_focos_bbox()
    print(f"{len(focos)} focos no bbox (todos os anos).")

    if len(focos):
        focos["h3_id"] = [
            h3.latlng_to_cell(lat, lon, cfg.H3_RESOLUCAO)
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
    resultado.to_parquet(out_path)

    print(f"\n  [h3_queimadas] {len(resultado)} hexágonos "
          f"({int((resultado['n_focos'] > 0).sum())} com ao menos 1 foco) → {out_path.name}")

    print("\nConcluído.")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from _projeto import carregar_config
    main(carregar_config())
