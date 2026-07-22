"""
05_app_corregos.py
------------------
O que faz   : Calcula a faixa de Área de Preservação Permanente (APP) ao
              longo de cursos d'água, aplicando a largura mínima do Código
              Florestal sobre a hidrografia disponível — prefere a
              hidrografia municipal (04_dados_municipais.py) e cai para o
              `waterway` do OSM (01_download_osm.py) quando não houver.
Camadas     : app_corregos (polígono, buffer dissolvido)
Saída       : {DATA_DIR}/app_corregos.gpkg
Fonte       : {DATA_DIR}/municipais.gpkg::hidrografia[_lagos] (preferencial)
              ou {DATA_DIR}/osm.gpkg::hidrografia_osm (fallback)
Requer      : 01 (fallback) e/ou 04 (preferencial) já rodados. Nenhum dos
              dois é obrigatório — sem hidrografia disponível, este script
              avisa e não grava nada (mesmo estilo tolerante do 12).

Método e limitação — LER ANTES DE MEXER
----------------------------------------
Código Florestal (Lei 12.651/2012, Art. 4º, inciso I) define a largura
mínima de APP a partir da MARGEM do curso d'água, escalonada pela largura do
rio: 30 m (< 10 m), 50 m (10-50 m), 100 m (50-200 m), 200 m (200-600 m),
500 m (> 600 m). Dados vetoriais de hidrografia normalmente só trazem a
linha d'água (sem largura do canal) — este script assume o caso mais comum
em córregos urbanos (< 10 m de largura) e aplica a largura de
`APP_LARGURA_MIN` (config.py) a partir da LINHA (centerline), não da margem
real. É uma aproximação: subestima levemente a faixa em cursos mais largos.
Ajuste `APP_LARGURA_MIN` se souber a largura real do curso d'água do projeto.

Para adaptar: ajuste `APP_LARGURA_MIN` no config.py (metros). Nenhum nome de
              lugar fica hard-coded aqui — os nomes de camada de hidrografia
              (`hidrografia`, `hidrografia_lagos`, `hidrografia_osm`) são
              convenção do 04/01, não específicos de Campinas.

Como rodar  : cd projetos/campinas
              python ../../scripts/pipeline/05_app_corregos.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio

sys.path.insert(0, str(Path.cwd()))
from config import APP_LARGURA_MIN, CRS_PROJETO, DATA_DIR  # noqa: E402

MUNICIPAIS_GPKG_PATH = DATA_DIR / "municipais.gpkg"
OSM_GPKG_PATH = DATA_DIR / "osm.gpkg"
OUT_PATH = DATA_DIR / "app_corregos.gpkg"

CAMADAS_HIDRO_MUNICIPAL = ["hidrografia", "hidrografia_lagos"]
CAMADA_HIDRO_OSM = "hidrografia_osm"


def _camadas_existentes(gpkg_path, camadas):
    if not gpkg_path.exists():
        return []
    existentes = {nome for nome, _ in pyogrio.list_layers(gpkg_path)}
    return [c for c in camadas if c in existentes]


def carregar_hidrografia():
    presentes = _camadas_existentes(MUNICIPAIS_GPKG_PATH, CAMADAS_HIDRO_MUNICIPAL)
    if presentes:
        print(f"  [fonte] hidrografia municipal: {presentes}")
        partes = [gpd.read_file(MUNICIPAIS_GPKG_PATH, layer=c)[["geometry"]] for c in presentes]
        return gpd.GeoDataFrame(pd.concat(partes, ignore_index=True), crs=partes[0].crs)

    if _camadas_existentes(OSM_GPKG_PATH, [CAMADA_HIDRO_OSM]):
        print(f"  [fonte] fallback: {CAMADA_HIDRO_OSM} (OSM)")
        return gpd.read_file(OSM_GPKG_PATH, layer=CAMADA_HIDRO_OSM)[["geometry"]]

    return None


def main():
    hidro = carregar_hidrografia()
    if hidro is None or hidro.empty:
        print("  [aviso] nenhuma hidrografia municipal nem OSM encontrada — "
              "app_corregos não calculado.")
        return

    hidro = hidro.to_crs(CRS_PROJETO)
    faixa = hidro.buffer(APP_LARGURA_MIN).union_all()
    gdf = gpd.GeoDataFrame({"largura_m": [APP_LARGURA_MIN]}, geometry=[faixa], crs=CRS_PROJETO)
    gdf.to_file(OUT_PATH, layer="app_corregos", driver="GPKG")
    area_ha = gdf.geometry.area.sum() / 1e4
    print(f"  [app_corregos] faixa de {APP_LARGURA_MIN} m, {area_ha:.1f} ha → {OUT_PATH.name}")


if __name__ == "__main__":
    main()
    print("\nConcluído.")
