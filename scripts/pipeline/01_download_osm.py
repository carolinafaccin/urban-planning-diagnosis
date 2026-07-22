"""
01_download_osm.py
-------------------
O que faz   : Baixa dados do OpenStreetMap para a área definida no config.py.
Camadas     : viario, edificacoes_osm, pontos_onibus, ciclovia, parques_osm,
              hidrografia_osm
Fonte       : OpenStreetMap via osmnx (viário, edificações, ciclovias,
              parques, hidrografia) e overpy (pontos de ônibus, via consulta
              Overpass QL direta — cobre tanto highway=bus_stop quanto
              public_transport=platform).

`hidrografia_osm` é o fallback nacional/global de hidrografia — usado pelo
05_app_corregos.py só quando não há hidrografia municipal (04). Sempre
baixada aqui (barata), mesmo que acabe não sendo usada.
Saída       : {DATA_DIR}/osm.gpkg — uma camada por feature, já reprojetada
              para CRS_PROJETO.
Para adaptar: ajuste BBOX e MUNICIPIO no config.py. Verifique a cobertura
              do OSM para o novo território em openstreetmap.org antes de
              rodar (bairros muito recentes podem ter poucos dados
              mapeados).

Como rodar  : a partir da pasta do projeto (onde está o config.py):
              cd projetos/campinas
              python ../../scripts/pipeline/01_download_osm.py
"""

import sys
import urllib.request
from pathlib import Path

import geopandas as gpd
import overpy
import osmnx as ox
from osmnx._errors import InsufficientResponseError
from shapely.geometry import Point

sys.path.insert(0, str(Path.cwd()))
from config import BBOX, CRS_PROJETO, CRS_WGS84, DATA_DIR, RAW_CATALOG  # noqa: E402

OSM_GPKG_PATH = DATA_DIR / "osm.gpkg"

# Por padrão o osmnx grava cache de respostas HTTP em ./cache/, relativo à
# pasta de onde o script é rodado — o que poluiria o repositório do projeto.
# Redireciona para a pasta que o próprio catálogo osm/ já usa para isso
# (raw_dir/osm/overpass_cache/), compartilhada entre todos os projetos —
# nunca uma pasta nova por projeto dentro do raw_dir.
ox.settings.cache_folder = str(RAW_CATALOG / "osm" / "overpass_cache")

# A API do Overpass rejeita (HTTP 406) requisições sem um User-Agent
# identificável; overpy usa urllib puro e não expõe um jeito direto de
# configurar headers, então registramos um opener global com User-Agent.
_opener = urllib.request.build_opener()
_opener.addheaders = [("User-Agent", "diagnostico-urbanistico/1.0")]
urllib.request.install_opener(_opener)

# bbox no formato exigido pelo osmnx 2.x: (left, bottom, right, top)
# ou seja (west, south, east, north)
OSMNX_BBOX = (BBOX["west"], BBOX["south"], BBOX["east"], BBOX["north"])


def salvar_camada(gdf, nome):
    """Reprojeta para CRS_PROJETO e grava/atualiza a camada no GeoPackage."""
    if gdf is None or gdf.empty:
        print(f"  [{nome}] nenhum dado retornado — camada não gravada.")
        return
    gdf = gdf.set_crs(CRS_WGS84, allow_override=True) if gdf.crs is None else gdf
    gdf = gdf.to_crs(CRS_PROJETO)
    # GeoPackage não aceita colunas de listas/dicts (comuns em tags do OSM)
    for col in gdf.columns:
        if col != "geometry" and gdf[col].apply(lambda v: isinstance(v, (list, dict))).any():
            gdf[col] = gdf[col].astype(str)
    gdf.to_file(OSM_GPKG_PATH, layer=nome, driver="GPKG")
    print(f"  [{nome}] {len(gdf)} feições salvas em {OSM_GPKG_PATH} (camada '{nome}')")


def baixar_viario():
    print("Baixando viário (rede completa)...")
    grafo = ox.graph_from_bbox(OSMNX_BBOX, network_type="all")
    _, edges = ox.graph_to_gdfs(grafo, nodes=True, edges=True)
    salvar_camada(edges.reset_index(), "viario")


def baixar_edificacoes():
    print("Baixando edificações...")
    try:
        gdf = ox.features_from_bbox(OSMNX_BBOX, tags={"building": True})
    except InsufficientResponseError:
        gdf = None
    salvar_camada(gdf, "edificacoes_osm")


def baixar_ciclovias():
    print("Baixando ciclovias...")
    try:
        gdf = ox.features_from_bbox(
            OSMNX_BBOX, tags={"highway": "cycleway", "cycleway": True}
        )
    except InsufficientResponseError:
        gdf = None
    salvar_camada(gdf, "ciclovia")


def baixar_parques():
    print("Baixando parques e áreas verdes...")
    try:
        gdf = ox.features_from_bbox(
            OSMNX_BBOX, tags={"leisure": "park", "landuse": "recreation_ground"}
        )
    except InsufficientResponseError:
        gdf = None
    salvar_camada(gdf, "parques_osm")


def baixar_hidrografia():
    print("Baixando hidrografia (rios, córregos)...")
    try:
        gdf = ox.features_from_bbox(
            OSMNX_BBOX, tags={"waterway": ["river", "stream", "canal", "drain", "ditch"]}
        )
    except InsufficientResponseError:
        gdf = None
    salvar_camada(gdf, "hidrografia_osm")


def baixar_pontos_onibus():
    """Usa overpy (Overpass QL direto) para pegar highway=bus_stop e
    public_transport=platform numa única consulta."""
    print("Baixando pontos de ônibus (overpy)...")
    api = overpy.Overpass(max_retry_count=3, retry_timeout=10)
    s, w, n, e = BBOX["south"], BBOX["west"], BBOX["north"], BBOX["east"]
    query = f"""
        [out:json][timeout:60];
        (
          node["highway"="bus_stop"]({s},{w},{n},{e});
          node["public_transport"="platform"]({s},{w},{n},{e});
        );
        out body;
    """
    resultado = api.query(query)

    if not resultado.nodes:
        print("  [pontos_onibus] nenhum dado retornado — camada não gravada.")
        return

    registros = [
        {**no.tags, "osm_id": no.id, "geometry": Point(float(no.lon), float(no.lat))}
        for no in resultado.nodes
    ]
    gdf = gpd.GeoDataFrame(registros, geometry="geometry", crs=CRS_WGS84)
    salvar_camada(gdf, "pontos_onibus")


if __name__ == "__main__":
    print(f"Área de estudo (WGS84): {BBOX}")
    print(f"Destino: {OSM_GPKG_PATH}\n")

    baixar_viario()
    baixar_edificacoes()
    baixar_ciclovias()
    baixar_parques()
    baixar_hidrografia()
    baixar_pontos_onibus()

    print("\nConcluído.")
