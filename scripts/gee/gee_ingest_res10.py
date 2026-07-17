"""
gee_ingest_res10.py
-------------------
O que faz   : Lê os CSVs exportados pelo gee_lst_ndvi_res10.js (um por UF, no
              Drive) e consolida em h3_gee.parquet, chaveado por h3_id — o
              enriquecimento que o 10_build_geopackage.py junta à malha e que o
              11_analises.py usa como FALLBACK de LST/NDVI quando não há Cool
              Cities.
Saída       : {DATA_DIR}/processed/h3_gee.parquet (h3_id → gee_lst, gee_ndvi_pct)
Entrada     : os CSVs baixados do Drive (pasta GEE_lst_ndvi_res10), apontada
              por GEE_CSV_DIR abaixo — ajuste para onde você baixou.

Como rodar  : cd projetos/campinas
              python ../../scripts/gee/gee_ingest_res10.py <pasta_com_os_csvs>
              (ou ajuste GEE_CSV_DIR no código)
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path.cwd()))
from config import PROCESSED_DIR  # noqa: E402

OUT_PATH = PROCESSED_DIR / "h3_gee.parquet"
COLS = ["h3_id", "gee_lst", "gee_ndvi_pct"]


def main(csv_dir):
    csv_dir = Path(csv_dir)
    arquivos = sorted(csv_dir.glob("gee_lst_ndvi_res10_uf_*.csv"))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum CSV 'gee_lst_ndvi_res10_uf_*.csv' em {csv_dir}. "
            f"Baixe os exports do GEE (Drive/GEE_lst_ndvi_res10) e aponte a pasta."
        )
    df = pd.concat((pd.read_csv(a) for a in arquivos), ignore_index=True)
    faltando = [c for c in COLS if c not in df.columns]
    if faltando:
        raise ValueError(f"Colunas ausentes nos CSVs do GEE: {faltando}")

    df = df[COLS].dropna(subset=["h3_id"]).drop_duplicates("h3_id")
    df.to_parquet(OUT_PATH)
    print(f"  [h3_gee] {len(df)} hexágonos ({len(arquivos)} UF) → {OUT_PATH.name}")


if __name__ == "__main__":
    pasta = sys.argv[1] if len(sys.argv) > 1 else str(PROCESSED_DIR)
    main(pasta)
    print("\nConcluído.")
