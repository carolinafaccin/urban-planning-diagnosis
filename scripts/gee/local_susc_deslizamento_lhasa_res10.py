"""
local_susc_deslizamento_lhasa_res10.py
---------------------------------------
O que faz   : Amostra o raster global de suscetibilidade a deslizamentos
              LHASA (NASA), já baixado localmente, nos centróides H3 res10
              — SEM usar Earth Engine. Ao contrário dos outros produtos
              gee_*_res10.js (que exportam do GEE), o LHASA já existe como
              GeoTIFF estático em raw_dir/nasa/ (baixado direto do portal
              NASA GPM) — processar localmente é mais simples e mais rápido
              que subir como asset e rodar reduceRegions no GEE.
              Espelha suscetibilidade-deslizamentos-lhasa-v1/ do catálogo
              nacional res9 (raw_dir/gee/h3_res9/), em res10.
Fonte       : raw_dir/nasa/global_landslide_susceptibility_map/
              global-landslide-susceptibility-map-2-27-23.tif
              (raster global ~1km, classes 0-5, ver README da pasta).
Entrada     : raw_dir/gee/h3_res10/centroides/br_h3_res10_centroides_uf_*.csv
              (gerado por gee_centroides_res10_nacional.py).
Saída       : raw_dir/gee/h3_res10/suscetibilidade-deslizamentos-lhasa-v1/
              h3_susc_desliz_lhasa_v1_uf_<NN>.csv
              colunas: h3_id, cd_setor, cd_uf, qtd_dom, lhasa_class

Nota sobre resolução: o raster tem ~1km — mais grosso que o hexágono res10
(~76m de circunraio). Por isso amostramos por PONTO (rasterio.sample no
centróide), não por zonal stats num buffer: numa célula de 1km, a média
zonal de um buffer de 76m é essencialmente o mesmo valor do pixel que
contém o ponto. `lhasa_class` é a classe 0-5 direto do raster (ver schema
no README de raw_dir/nasa/), não normalizada — normalizar/decidir threshold
"alto/muito alto" fica para quando isso virar indicador de fato (ver nota
no CLAUDE.md: candidato a nova dimensão do score, não antecipar agora).

Como rodar  : cd projetos/campinas
              python ../../scripts/gee/local_susc_deslizamento_lhasa_res10.py
"""

import sys
from pathlib import Path

import pandas as pd
import rasterio

sys.path.insert(0, str(Path.cwd()))
from config import RAW_CATALOG  # noqa: E402

CENTROIDES_DIR = RAW_CATALOG / "gee" / "h3_res10" / "centroides"
RASTER_PATH = (
    RAW_CATALOG / "nasa" / "global_landslide_susceptibility_map"
    / "global-landslide-susceptibility-map-2-27-23.tif"
)
OUT_DIR = RAW_CATALOG / "gee" / "h3_res10" / "suscetibilidade-deslizamentos-lhasa-v1"


def main():
    if not RASTER_PATH.exists():
        raise FileNotFoundError(
            f"Raster LHASA não encontrado em {RASTER_PATH}. Ver "
            f"raw_dir/nasa/README.md (subpasta global_landslide_susceptibility_map/)."
        )
    arquivos = sorted(CENTROIDES_DIR.glob("br_h3_res10_centroides_uf_*.csv"))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum centróide em {CENTROIDES_DIR}. Rode "
            f"gee_centroides_res10_nacional.py primeiro."
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with rasterio.open(RASTER_PATH) as src:
        nodata = src.nodata
        for csv_path in arquivos:
            df = pd.read_csv(csv_path)
            coords = list(zip(df["lon"], df["lat"]))
            valores = [v[0] for v in src.sample(coords)]
            df["lhasa_class"] = valores
            if nodata is not None:
                df.loc[df["lhasa_class"] == nodata, "lhasa_class"] = pd.NA

            out = df[["h3_id", "cd_setor", "cd_uf", "qtd_dom", "lhasa_class"]]
            out_path = OUT_DIR / csv_path.name.replace(
                "br_h3_res10_centroides", "h3_susc_desliz_lhasa_v1"
            )
            out.to_csv(out_path, index=False)
            n_validos = out["lhasa_class"].notna().sum()
            print(f"  [{out_path.name}] {n_validos}/{len(out)} células com classe válida")

    print(f"\nSaída em {OUT_DIR}")


if __name__ == "__main__":
    main()
    print("\nConcluído.")
