"""
dados_locais.py
------------------
O que faz   : Ingere os dados georreferenciados à mão (LOCAL_DATA_DIR) e os
              fornecidos pela prefeitura (SOLICITADOS_DATA_DIR) — uma camada
              por arquivo — reprojetando para o CRS do projeto.
Camadas     : uma por geojson/shape/gpkg encontrado nas duas pastas.
Saída       : {DATA_DIR}/locais.gpkg
Fonte       : {DATA_DIR}/raw/local/*  e  {DATA_DIR}/raw/solicitados/*

Estes arquivos são preenchidos pela equipe. O script é tolerante: se as
pastas estiverem vazias, apenas avisa e não grava nada — o resto do pipeline
segue e o build_geopackage.py inclui o que existir.

Para adaptar: nada. Lê tudo que houver nas duas pastas do config.py.

Como rodar  : cd projetos/campinas
              python ../../scripts/pipeline/dados_locais.py
"""

import sys
from pathlib import Path

import geopandas as gpd

EXTENSOES = {".geojson", ".json", ".gpkg", ".shp", ".kml"}


def coletar(pasta):
    if not pasta.exists():
        return []
    return sorted(p for p in pasta.iterdir() if p.suffix.lower() in EXTENSOES)


def main(cfg):
    locais_gpkg_path = cfg.DATA_DIR / "locais.gpkg"

    arquivos = coletar(cfg.LOCAL_DATA_DIR) + coletar(cfg.SOLICITADOS_DATA_DIR)
    if not arquivos:
        print("SKIP: nenhum arquivo local/solicitado encontrado ainda."
              f"\n  {cfg.LOCAL_DATA_DIR}\n  {cfg.SOLICITADOS_DATA_DIR}")
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
        gdf = gdf.to_crs(cfg.CRS_PROJETO)
        gdf.to_file(locais_gpkg_path, layer=nome, driver="GPKG")
        print(f"  [{nome}] {len(gdf)} feições → {locais_gpkg_path.name}")
        n += 1

    print(f"\n{n} camada(s) locais ingeridas.")

    print("\nConcluído.")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from _projeto import carregar_config
    main(carregar_config())
