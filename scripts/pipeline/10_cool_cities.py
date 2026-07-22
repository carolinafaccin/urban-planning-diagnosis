"""
10_cool_cities.py
-----------------
O que faz   : Agrega os rasters do Cool Cities Lab por hexágono da malha
              H3, via estatística zonal (média). Fornece LST, cobertura vegetal
              fina, risco de calor, conforto térmico (UTCI) e o impacto modelado
              das intervenções (arborização e cool roofs) — mapas 3, 4, 5, 6 e
              insumo dos mapas 16/17.
Saída       : {DATA_DIR}/processed/h3_cool_cities.parquet (h3_id → colunas)
Fonte       : raw_dir/wri/cool-cities-lab/BRA-<Cidade>/
                baseline/    — rasters da mancha urbana (cobrem a cidade toda)
                scenarios/   — rasters da "accelerator_area" (≈ área de estudo)
Requer      : 07_h3_dasimetrico.py já rodado (geometria de h3_base).

Cobertura / disponibilidade
---------------------------
O Cool Cities Lab só tem dados para poucas cidades. Este script é o caminho
preferencial quando há dado; quando NÃO há (outra cidade), o fallback é a
extração via GEE (ver gee_lst_res10). Rasters ausentes são apenas avisados e
pulados — o pipeline segue.

Os rasters de cenário cobrem só a accelerator_area (≈ bbox do projeto);
hexágonos fora dela ficam com esses campos nulos (esperado). Os de baseline
cobrem a cidade inteira.

Para adaptar: aponte CCL_DIR para a pasta BRA-<Cidade> correspondente. A lista
              RASTERS (coluna → subpasta + padrão glob) é o único ponto a
              revisar se a nomenclatura do CCL mudar.

Como rodar  : cd projetos/campinas
              python ../../scripts/pipeline/10_cool_cities.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import rasterio
from rasterstats import zonal_stats

sys.path.insert(0, str(Path.cwd()))
from config import DATA_DIR, MUNICIPIO, PROCESSED_DIR, RAW_CATALOG  # noqa: E402

H3_GPKG_PATH = DATA_DIR / "h3.gpkg"
OUT_PATH = PROCESSED_DIR / "h3_cool_cities.parquet"

# Pasta da cidade no catálogo CCL. MUNICIPIO="Campinas" → "BRA-Campinas".
CCL_DIR = RAW_CATALOG / "wri" / "cool-cities-lab" / f"BRA-{MUNICIPIO}"

# coluna de saída → (subpasta relativa ao CCL_DIR, padrão glob do arquivo).
# Seleção curada; há mais rasters na pasta baseline/ se precisar.
RASTERS = {
    # --- baseline (cidade inteira) ---
    "ccl_lst":                ("baseline", "*HighLandSurfaceTemperature__*"),          # °C (mapa 3)
    "ccl_frac_veg":           ("baseline", "*FractionalVegetationPercent__*"),         # % (mapa 6)
    "ccl_tree_canopy":        ("baseline", "*TreeCanopyCoverMaskIndex__*"),            # índice de dossel
    "ccl_albedo":             ("baseline", "*AlbedoCloudMasked__ZonalStats*"),          # % albedo
    "ccl_risco_calor":        ("baseline", "*HeatRiskIndexGeneral*"),                   # risco geral (mapa 5)
    "ccl_risco_calor_arvore": ("baseline", "*HeatRiskIndexTree*"),                      # risco mitigável por árvore
    "ccl_risco_calor_roof":   ("baseline", "*HeatRiskIndexCoolRoof*"),                  # risco mitigável por cool roof
    "ccl_pop":                ("baseline", "*WorldPop__Version*"),                      # densidade pop.
    "ccl_pop_idosos":         ("baseline", "*WorldPop__AgesexClasses_ELDERLY*"),        # idosos
    "ccl_pop_criancas":       ("baseline", "*WorldPop__AgesexClasses_YOUNG_CHILDREN*"), # crianças
    "ccl_oport_arvores":      ("baseline", "*opportunity__trees__all-plantable*"),      # área plantável
    "ccl_oport_cool_roofs":   ("baseline", "*opportunity__cool-roofs__all-roofs*"),     # telhados elegíveis
    # --- cenários (accelerator_area ≈ bbox) ---
    "ccl_utci_base":          ("scenarios/street-trees", "*utci_1500_baseline*"),                       # conforto térmico base (mapa 4)
    "ccl_utci_ganho_arvores": ("scenarios/street-trees", "*utci_1500_street_trees_achievable_vs_baseline*"),  # Δ UTCI por arborização
    "ccl_utci_ganho_roofs":   ("scenarios/cool-roofs",   "*utci_1500_cool_roofs_achievable_vs_baseline*"),    # Δ UTCI por cool roofs
}


def achar(subpasta, padrao):
    matches = sorted((CCL_DIR / subpasta).glob(padrao))
    return matches[0] if matches else None


def main():
    if not CCL_DIR.exists():
        raise FileNotFoundError(
            f"Pasta Cool Cities não encontrada: {CCL_DIR}. Se esta cidade não tem "
            f"dado no CCL, use a extração via GEE (fallback) em vez deste script."
        )

    hex_gdf = gpd.read_file(H3_GPKG_PATH, layer="h3_base")[["h3_id", "geometry"]]
    resultado = pd.DataFrame({"h3_id": hex_gdf["h3_id"]})

    for coluna, (subpasta, padrao) in RASTERS.items():
        tif = achar(subpasta, padrao)
        if tif is None:
            print(f"  [pulado] {coluna}: nenhum raster casa '{padrao}' em {subpasta}/")
            continue
        with rasterio.open(tif) as src:
            hexr = hex_gdf.to_crs(src.crs)
            nodata = src.nodata
        stats = zonal_stats(hexr, str(tif), stats=["mean"], nodata=nodata)
        resultado[coluna] = [s["mean"] for s in stats]
        n_ok = resultado[coluna].notna().sum()
        print(f"  [{coluna}] {n_ok}/{len(hex_gdf)} hexágonos com valor  ({tif.name[:60]}...)")

    resultado.to_parquet(OUT_PATH)
    print(f"\n  [h3_cool_cities] {len(resultado)} hexágonos, "
          f"{len(resultado.columns)-1} colunas → {OUT_PATH.name}")


if __name__ == "__main__":
    main()
    print("\nConcluído.")
