"""
12_dados_locais.py
------------------
O que faz   : Ingere os dados georreferenciados à mão (LOCAL_DATA_DIR) e os
              fornecidos pela prefeitura (SOLICITADOS_DATA_DIR) — uma camada
              por arquivo — reprojetando para o CRS do projeto.
Camadas     : uma por geojson/shape/gpkg encontrado nas duas pastas.
Saída       : {DATA_DIR}/locais.gpkg
Fonte       : {DATA_DIR}/raw/local/*  e  {DATA_DIR}/raw/solicitados/*

Estes arquivos são preenchidos pela equipe. O script é tolerante: se as
pastas estiverem vazias, apenas avisa e não grava nada — o resto do pipeline
segue e o 13_build_geopackage.py inclui o que existir.

Para adaptar: nada. Lê tudo que houver nas duas pastas do config.py.

Como rodar  : cd projetos/campinas
              python ../../scripts/pipeline/12_dados_locais.py
"""

import sys
from pathlib import Path

import geopandas as gpd

sys.path.insert(0, str(Path.cwd()))
from config import (  # noqa: E402
    CRS_PROJETO,
    DATA_DIR,
    LOCAL_DATA_DIR,
    SOLICITADOS_DATA_DIR,
)

LOCAIS_GPKG_PATH = DATA_DIR / "locais.gpkg"
EXTENSOES = {".geojson", ".json", ".gpkg", ".shp", ".kml"}


def coletar(pasta):
    if not pasta.exists():
        return []
    return sorted(p for p in pasta.iterdir() if p.suffix.lower() in EXTENSOES)


def main():
    arquivos = coletar(LOCAL_DATA_DIR) + coletar(SOLICITADOS_DATA_DIR)
    if not arquivos:
        print("Nenhum arquivo local/solicitado encontrado ainda."
              f"\n  {LOCAL_DATA_DIR}\n  {SOLICITADOS_DATA_DIR}")
        return

    n = 0
    for arq in arquivos:
        nome = arq.stem
        try:
            gdf = gpd.read_file(arq)
        except Exception as e:  # noqa: BLE001 — arquivo malformado não deve derrubar o resto
            print(f"  [pulado] {arq.name}: {e}")
            continue
        if gdf.empty:
            print(f"  [vazio]  {arq.name}")
            continue
        gdf = gdf.to_crs(CRS_PROJETO)
        gdf.to_file(LOCAIS_GPKG_PATH, layer=nome, driver="GPKG")
        print(f"  [{nome}] {len(gdf)} feições → {LOCAIS_GPKG_PATH.name}")
        n += 1

    print(f"\n{n} camada(s) locais ingeridas.")


if __name__ == "__main__":
    main()
    print("\nConcluído.")
