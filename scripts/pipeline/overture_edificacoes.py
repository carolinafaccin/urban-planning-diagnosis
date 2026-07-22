"""
overture_edificacoes.py
--------------------------
O que faz   : Baixa as edificações do Overture Maps para o bbox e filtra por
              confiança de detecção. Substitui o OSM para footprints — em
              bairros pouco mapeados o OSM pode ter pouquíssimas edificações
              (num piloto testado, ~120 contra ~7 mil no Overture).
Camadas     : edificacoes (em {DATA_DIR}/edificacoes.gpkg), reprojetada p/ CRS.
Fonte       : Overture Maps (tema buildings), via pacote `overturemaps`. O
              Overture já funde e deduplica OpenStreetMap + Google/Microsoft
              Open Buildings; a confiança de detecção vem das fontes de ML.
Requer      : internet (lê os parquets públicos do Overture no S3).

Filtro de confiança
-------------------
`confidence` não é coluna direta — vem por fonte, dentro de `sources`. A regra:
  - edificações com fonte OpenStreetMap são mantidas sempre (mapeamento humano);
  - as demais (ML) são mantidas se a confiança máxima ≥ OVERTURE_CONF_MIN.
Ajuste OVERTURE_CONF_MIN no config.py.

Cache
-----
O download bruto (lento) é cacheado em processed/overture_raw_<hash do bbox>.parquet
— o nome inclui um hash do BBOX para que uma mudança de bbox (comum ao ajustar
a área de estudo) nunca sirva silenciosamente o cache de outra área; cada bbox
tem seu próprio arquivo. Reexecuções com o mesmo bbox filtram do cache sem
rebaixar. Apague o(s) arquivo(s) para forçar novo download.

A fração construída por hexágono (pct_construido, p/ o score) é calculada no
build_geopackage.py, que tem a malha H3 — este script só entrega a camada.

Para adaptar: nada específico. Usa BBOX e OVERTURE_CONF_MIN do config.py.

Como rodar  : cd projetos/campinas
              python ../../scripts/pipeline/overture_edificacoes.py
"""

import hashlib
import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

# Preenchidos por main(cfg) — usados como globais por baixar_bruto(), que é
# chamada de dentro de main.
BBOX = None
RAW_CACHE = None


def baixar_bruto():
    """Baixa buildings do Overture no bbox (ou lê o cache)."""
    if RAW_CACHE.exists():
        print(f"Usando cache: {RAW_CACHE.name}")
        return gpd.read_parquet(RAW_CACHE)
    from overturemaps import core

    print("Baixando edificações do Overture (pode levar alguns minutos)...")
    bb = (BBOX["west"], BBOX["south"], BBOX["east"], BBOX["north"])
    gdf = core.geodataframe("building", bbox=bb)
    gdf.to_parquet(RAW_CACHE)
    print(f"  {len(gdf)} edificações baixadas e cacheadas em {RAW_CACHE.name}")
    return gdf


def confianca_e_osm(sources):
    """De uma lista de fontes Overture, extrai (confiança máx de ML, tem OSM?)."""
    conf, tem_osm = None, False
    for s in sources or []:
        ds = (s.get("dataset") or "").lower()
        if "openstreetmap" in ds or ds == "osm":
            tem_osm = True
        c = s.get("confidence")
        if c is not None:
            conf = c if conf is None else max(conf, c)
    return conf, tem_osm


def main(cfg):
    global BBOX, RAW_CACHE

    BBOX = cfg.BBOX
    edif_gpkg_path = cfg.DATA_DIR / "edificacoes.gpkg"

    # Hash curto do bbox no nome do cache — muda automaticamente se a área de
    # estudo mudar, para nunca servir silenciosamente o cache de outro bbox.
    bbox_hash = hashlib.sha1(json.dumps(BBOX, sort_keys=True).encode()).hexdigest()[:8]
    RAW_CACHE = cfg.PROCESSED_DIR / f"overture_raw_{bbox_hash}.parquet"

    gdf = baixar_bruto()

    info = gdf["sources"].apply(confianca_e_osm)
    gdf["confianca"] = [c for c, _ in info]
    tem_osm = pd.Series([o for _, o in info], index=gdf.index)

    manter = tem_osm | (gdf["confianca"].fillna(0) >= cfg.OVERTURE_CONF_MIN)
    filtrado = gdf[manter].copy()

    print(f"\nEdificações: {len(gdf)} baixadas → {len(filtrado)} mantidas "
          f"({int(tem_osm.sum())} via OSM, "
          f"{int((~tem_osm & manter).sum())} de ML com confiança ≥ {cfg.OVERTURE_CONF_MIN}).")

    # GeoPackage não aceita colunas de listas/dicts (names, sources...) —
    # mantém só o essencial e reprojeta.
    manter_cols = ["id", "confianca", "height", "num_floors", "class", "subtype", "geometry"]
    filtrado = filtrado[[c for c in manter_cols if c in filtrado.columns]]
    # O Overture entrega em WGS84, mas o CRS pode não vir preenchido no gdf.
    if filtrado.crs is None:
        filtrado = filtrado.set_crs(cfg.CRS_WGS84)
    filtrado = filtrado.to_crs(cfg.CRS_PROJETO)
    filtrado["area_m2"] = filtrado.geometry.area

    filtrado.to_file(edif_gpkg_path, layer="edificacoes", driver="GPKG")
    print(f"  [edificacoes] {len(filtrado)} feições → {edif_gpkg_path} "
          f"(área construída total: {filtrado['area_m2'].sum():,.0f} m²)")

    print("\nConcluído.")


if __name__ == "__main__":
    sys.path.insert(0, str(Path.cwd()))
    import config
    main(config)
