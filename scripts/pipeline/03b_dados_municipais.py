"""
03b_dados_municipais.py
------------------------
O que faz   : Ingere as camadas do catálogo de dados municipais (prefeitura)
              já baixadas em raw_dir/prefeituras_municipais/<slug>/t0/,
              filtra pela área de estudo (BBOX) e reprojeta para o CRS do
              projeto — uma camada por entrada de CAMADAS_MUNICIPAIS.
Camadas     : uma por chave de CAMADAS_MUNICIPAIS presente no raw_dir e com
              interseção com o BBOX (nome da camada = a chave, não o nome do
              arquivo de origem — abstração que deixa o 10_build_geopackage.py
              e o dashboard referenciarem um nome estável independente da
              fonte municipal real por trás).
Saída       : {DATA_DIR}/municipais.gpkg
              {DATA_DIR}/viario_enriquecido.gpkg (só se 'classificacao_viaria'
              existir — ver nota abaixo)
Fonte       : raw_dir/prefeituras_municipais/<MUNICIPIO_SLUG>/t0/*.shp
              (ver README.md dessa pasta para proveniência de cada camada)
Requer      : 01_download_osm.py já rodado, se 'classificacao_viaria' estiver
              em CAMADAS_MUNICIPAIS (usa {DATA_DIR}/osm.gpkg::viario).

Preferir municipal, fallback nacional/global — 3 categorias (ver CLAUDE.md)
---------------------------------------------------------------------------
1. Sempre global (edificações, viário/topologia, censo): um dado municipal
   equivalente (ex.: classificacao_viaria) NUNCA substitui a camada global —
   só enriquece um atributo dela. Ver `enriquecer_viario()` abaixo: gera
   viario_enriquecido.gpkg (cópia do viário OSM + coluna classificacao_pmc via
   join espacial), sem tocar em osm.gpkg. O 10_build_geopackage.py prefere
   esse arquivo se ele existir, senão usa o viário OSM puro (mesmo mecanismo
   de "primeira fonte existente vence" do 11_analises.py::INDICADORES).
2. Fallback de indicador do score: camadas com `indicador_score` preenchido em
   CAMADAS_MUNICIPAIS não viram indicador aqui — isso é o
   06b_indicadores_municipais.py (precisa da malha H3, que só existe depois
   do 05). Este script só entrega o vetor bruto recortado.
3. Aditivo: a maioria das camadas — só entram no GeoPackage final como
   camada extra, sem nenhuma lógica de fallback.

Tolerante: CAMADAS_MUNICIPAIS vazio (cidade sem portal municipal, ou pasta
ainda não baixada) faz este script não gravar nada e o resto do pipeline
segue igual — dado municipal é sempre opt-in, nunca obrigatório.

Para adaptar: preencha CAMADAS_MUNICIPAIS no config.py do projeto (ver
              exemplo em projetos/campinas/config.py). Nenhum nome de camada
              ou arquivo fica hard-coded aqui.

Como rodar  : cd projetos/campinas
              python ../../scripts/pipeline/03b_dados_municipais.py
"""

import sys
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

sys.path.insert(0, str(Path.cwd()))
from config import (  # noqa: E402
    BBOX,
    CAMADAS_MUNICIPAIS,
    CRS_PROJETO,
    CRS_WGS84,
    DATA_DIR,
    MUNICIPAIS_RAW_DIR,
)

MUNICIPAIS_GPKG_PATH = DATA_DIR / "municipais.gpkg"
OSM_GPKG_PATH = DATA_DIR / "osm.gpkg"
VIARIO_ENRIQUECIDO_PATH = DATA_DIR / "viario_enriquecido.gpkg"

BBOX_WGS84 = box(BBOX["west"], BBOX["south"], BBOX["east"], BBOX["north"])
BBOX_PROJ = gpd.GeoSeries([BBOX_WGS84], crs=CRS_WGS84).to_crs(CRS_PROJETO).iloc[0]


def _sanitizar(gdf):
    """GeoPackage não aceita colunas de listas/dicts — converte para string.
    'FID' é nome reservado do driver GPKG (case-insensitive) — alguns
    shapefiles municipais trazem essa coluna já pronta, o que quebra a
    escrita; renomeia para não colidir."""
    for col in gdf.columns:
        if col != "geometry" and gdf[col].apply(lambda v: isinstance(v, (list, dict))).any():
            gdf[col] = gdf[col].astype(str)
    if "FID" in gdf.columns:
        gdf = gdf.rename(columns={"FID": "FID_ORIGINAL"})
    return gdf


def ler_recorte(arquivo):
    """Lê o shapefile do raw_dir municipal, reprojeta e filtra por interseção
    com o BBOX (filtro espacial, não corte de geometria — mantém a feição
    inteira se ela tocar a área de estudo)."""
    caminho = MUNICIPAIS_RAW_DIR / f"{arquivo}.shp"
    if not caminho.exists():
        print(f"  [pulado] {arquivo}: não encontrado em {MUNICIPAIS_RAW_DIR}")
        return None
    gdf = gpd.read_file(caminho)
    if gdf.crs is None:
        gdf = gdf.set_crs(CRS_PROJETO, allow_override=True)
    else:
        gdf = gdf.to_crs(CRS_PROJETO)
    gdf = gdf[gdf.intersects(BBOX_PROJ)]
    if gdf.empty:
        print(f"  [vazio]  {arquivo}: nenhuma feição intersecta o BBOX")
        return None
    return _sanitizar(gdf)


def enriquecer_viario(camada_classificacao):
    """Categoria 1: nunca substitui a topologia OSM, só anexa um atributo.
    Join espacial (mais próximo) da classificação viária municipal sobre as
    arestas do viário OSM, gravado num .gpkg separado — osm.gpkg não é
    tocado."""
    if not OSM_GPKG_PATH.exists():
        print("  [aviso] sem osm.gpkg — não é possível enriquecer o viário "
              "(rode o 01_download_osm.py antes).")
        return
    viario = gpd.read_file(OSM_GPKG_PATH, layer="viario").to_crs(CRS_PROJETO)
    cols_pmc = [c for c in camada_classificacao.columns if c != "geometry"]
    join = gpd.sjoin_nearest(
        viario, camada_classificacao[cols_pmc + ["geometry"]],
        how="left", max_distance=30, distance_col="dist_classificacao_pmc",
    ).drop(columns="index_right", errors="ignore")
    # sjoin_nearest pode duplicar arestas quando há empate de distância —
    # mantém a primeira ocorrência por aresta.
    join = join[~join.index.duplicated(keep="first")]
    rename = {c: f"pmc_{c.lower()}" for c in cols_pmc}
    join = join.rename(columns=rename)
    join.to_file(VIARIO_ENRIQUECIDO_PATH, layer="viario", driver="GPKG")
    n_ok = join["dist_classificacao_pmc"].notna().sum()
    print(f"  [viario_enriquecido] {n_ok}/{len(join)} arestas com classificação "
          f"municipal (raio 30 m) → {VIARIO_ENRIQUECIDO_PATH.name}")


def main():
    if not CAMADAS_MUNICIPAIS:
        print("CAMADAS_MUNICIPAIS vazio no config.py — nenhum dado municipal "
              "configurado para este projeto. Nada a fazer.")
        return

    if not MUNICIPAIS_RAW_DIR.exists():
        print(f"[aviso] pasta de dados municipais não encontrada: "
              f"{MUNICIPAIS_RAW_DIR}\nNada será gravado.")
        return

    n = 0
    classificacao_gdf = None
    for nome, cfg in CAMADAS_MUNICIPAIS.items():
        gdf = ler_recorte(cfg["arquivo"])
        if gdf is None:
            continue
        gdf.to_file(MUNICIPAIS_GPKG_PATH, layer=nome, driver="GPKG")
        print(f"  [{nome}] {len(gdf)} feições → {MUNICIPAIS_GPKG_PATH.name}")
        n += 1
        if nome == "classificacao_viaria":
            classificacao_gdf = gdf

    print(f"\n{n} camada(s) municipais ingeridas.")

    if classificacao_gdf is not None:
        enriquecer_viario(classificacao_gdf)


if __name__ == "__main__":
    main()
    print("\nConcluído.")
