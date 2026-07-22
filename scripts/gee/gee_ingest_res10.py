"""
gee_ingest_res10.py
-------------------
O que faz   : Lê os CSVs exportados por gee_lst_ndvi_res10.js e já organizados
              em raw_dir/gee/br_h3_res10/lst_ndvi/ (um ou mais arquivos por
              UF — mais de um quando a UF precisou de lotes, ver CHUNK_SIZE
              nos scripts gee_*_res10.js) e consolida em h3_gee.parquet,
              chaveado por h3_id — o enriquecimento que o
              10_build_geopackage.py junta à malha e que o 11_analises.py usa
              como FALLBACK de LST/NDVI quando não há Cool Cities.
Saída       : {DATA_DIR}/processed/h3_gee.parquet (h3_id → gee_lst, gee_ndvi_pct)
Entrada     : {RAW_CATALOG}/gee/br_h3_res10/lst_ndvi/gee_br_h3_res10_lst_ndvi_uf_*.csv
              (default) — passe outra pasta como argumento se quiser
              consolidar de outro lugar.

Múltiplos lotes por UF: o glob casa qualquer arquivo que comece com
gee_br_h3_res10_lst_ndvi_uf_, então tanto _uf_43.csv (UF sem lote) quanto
_uf_43_lote0.csv/_uf_43_lote1.csv (UF que precisou de lotes) entram — o
drop_duplicates(h3_id) já garante que cada hexágono aparece uma vez só no
resultado final, não precisa tratar lotes como caso especial.

Como rodar  : cd projetos/campinas
              python ../../scripts/gee/gee_ingest_res10.py
              (ou passe uma pasta: ... gee_ingest_res10.py <outra_pasta>)
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path.cwd()))
from config import PROCESSED_DIR, RAW_CATALOG  # noqa: E402

DEFAULT_CSV_DIR = RAW_CATALOG / "gee" / "br_h3_res10" / "lst_ndvi"
OUT_PATH = PROCESSED_DIR / "h3_gee.parquet"
COLS = ["h3_id", "gee_lst", "gee_ndvi_pct"]


def main(csv_dir):
    csv_dir = Path(csv_dir)
    arquivos = sorted(csv_dir.glob("gee_br_h3_res10_lst_ndvi_uf_*.csv"))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum CSV 'gee_br_h3_res10_lst_ndvi_uf_*.csv' em {csv_dir}. "
            f"Rode os exports do GEE (gee_lst_ndvi_res10.js) e organize em raw_dir."
        )
    df = pd.concat((pd.read_csv(a) for a in arquivos), ignore_index=True)
    faltando = [c for c in COLS if c not in df.columns]
    if faltando:
        raise ValueError(f"Colunas ausentes nos CSVs do GEE: {faltando}")

    n_arquivos = len(arquivos)
    df = df[COLS].dropna(subset=["h3_id"]).drop_duplicates("h3_id")
    df.to_parquet(OUT_PATH)
    print(f"  [h3_gee] {len(df)} hexágonos ({n_arquivos} arquivo(s)) → {OUT_PATH.name}")


if __name__ == "__main__":
    pasta = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_CSV_DIR)
    main(pasta)
    print("\nConcluído.")
