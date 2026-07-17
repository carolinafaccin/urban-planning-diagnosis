"""
04_cnefe.py
-----------
O que faz   : Varre o CNEFE 2022 da UF do projeto UMA vez, recorta os
              endereços dos setores da área de estudo e produz os insumos
              derivados do CNEFE:
                (a) recorte do projeto (parquet reutilizável) — para os
                    scripts seguintes não relerem os ~3,6 GB da UF;
                (b) uso do solo por hexágono H3 (contagem de endereços por
                    espécie — método da Ana Maffini);
                (c) domicílios por (hexágono, setor) — peso da interpolação
                    dasimétrica no 05_h3_dasimetrico.py.
Camadas     : — (só tabelas/parquet; a geometria dos hexágonos é montada no 05)
Saídas      : {DATA_DIR}/processed/cnefe_recorte.parquet      (geoparquet, pontos)
              {DATA_DIR}/processed/cnefe_uso_h3.parquet        (h3_id → cat_*)
              {DATA_DIR}/processed/cnefe_dom_h3_setor.parquet  (h3_id, cd_setor → qtd_dom)
Fonte       : raw_dir/ibge/censo/2022/cnefe/por_uf/{cod_uf}_*.csv
              (CSV por UF, sep=';', com latitude/longitude e cod_especie)
Requer      : 02_download_ibge.py já rodado (usa {DATA_DIR}/ibge.gpkg como
              recorte espacial e fonte da chave cd_setor).

DECISÃO DE CHAVE — LER ANTES DE MEXER
-------------------------------------
O `cod_setor` do CNEFE 2022 NÃO casa com o `cd_setor` da malha
br_setores.gpkg: são versões diferentes de codificação (num caso observado o
CNEFE dizia distrito 05 e a malha 30/35, para o mesmo lugar). Um join por código
daria zero match silenciosamente. Por isso a espécie/identidade do setor de
cada ponto vem de um JOIN ESPACIAL (point-in-polygon) com a malha — nunca do
código do CNEFE. Validado: 100% dos pontos do bbox caem dentro de algum setor
da malha; 0% batem por código.

Método (espelha e refina o climate-injustice-index)
---------------------------------------------------
- O peso dasimétrico precisa do total de domicílios do setor INTEIRO, não só
  da parte dentro do bbox de estudo. Por isso a varredura filtra pelos limites
  da UNIÃO dos setores da área (que se estendem além do bbox), e o join
  espacial mantém todo ponto que cai em qualquer um desses setores.
- As contagens de domicílio são chaveadas por (h3_id, cd_setor): um hexágono
  que cruza divisa de setor recebe contribuição de cada setor via os pontos
  que ali estão — mais preciso que atribuir o hexágono inteiro a um só setor
  (o ponto fraco do método res9 em resoluções finas).

Para adaptar: nada específico de Campinas. Usa IBGE_COD_MUN (p/ achar a UF e
              filtrar o município) e H3_RESOLUCAO do config.py.

Como rodar  : cd projetos/campinas
              python ../../scripts/pipeline/04_cnefe.py
              (varredura de UF grande leva alguns minutos; é uma vez só.)
"""

import sys
from pathlib import Path

import geopandas as gpd
import h3
import pandas as pd

sys.path.insert(0, str(Path.cwd()))
from config import (  # noqa: E402
    CRS_PROJETO,
    CRS_WGS84,
    DATA_DIR,
    H3_RESOLUCAO,
    IBGE_COD_MUN,
    PROCESSED_DIR,
    RAW_CATALOG,
)

IBGE_GPKG_PATH = DATA_DIR / "ibge.gpkg"
CNEFE_DIR = RAW_CATALOG / "ibge" / "censo" / "2022" / "cnefe" / "por_uf"

RECORTE_PATH = PROCESSED_DIR / "cnefe_recorte.parquet"
USO_H3_PATH = PROCESSED_DIR / "cnefe_uso_h3.parquet"
DOM_H3_SETOR_PATH = PROCESSED_DIR / "cnefe_dom_h3_setor.parquet"

COD_UF = IBGE_COD_MUN[:2]  # 2 primeiros dígitos do código do município = UF

# Mapeamento COD_ESPECIE → categoria de uso (CNEFE 2022; ver dicionário e o
# repo Codigo-CNEFE-2022 de Ana Luisa Maffini, github.com/anamaffini).
ESPECIE_CAT = {
    "1": "domicilio_particular",
    "2": "domicilio_coletivo",
    "3": "agropecuario",
    "4": "ensino",
    "5": "saude",
    "6": "outras_finalidades",
    "7": "construcao_reforma",
    "8": "religioso",
}
ESPECIE_DOMICILIO = "1"  # domicílio particular — usado como peso dasimétrico

CHUNK = 500_000
CSV_COLS = ["cod_municipio", "cod_setor", "latitude", "longitude", "cod_especie", "dsc_estabelecimento"]


def achar_csv_uf():
    matches = sorted(CNEFE_DIR.glob(f"{COD_UF}_*.csv"))
    if not matches:
        raise FileNotFoundError(
            f"Não achei o CSV do CNEFE da UF {COD_UF} em {CNEFE_DIR} "
            f"(esperado {COD_UF}_<sigla>.csv)."
        )
    return matches[0]


def limites_setores():
    """Bounds (WGS84) da união dos setores da área — captura o setor inteiro,
    inclusive as partes que passam do bbox de estudo."""
    setores = gpd.read_file(IBGE_GPKG_PATH, layer="setores_censitarios")
    oeste, sul, leste, norte = setores.to_crs(CRS_WGS84).total_bounds
    return setores, (oeste, sul, leste, norte)


def varrer_cnefe(csv_path, bounds):
    """Lê o CSV da UF em chunks, mantendo só o município do projeto dentro dos
    limites dos setores. Retorna DataFrame com lat/lon/espécie/estab/cod_setor."""
    oeste, sul, leste, norte = bounds
    partes, lidas = [], 0
    print(f"Varrendo {csv_path.name} (chunks de {CHUNK:,})...")
    for ch in pd.read_csv(csv_path, sep=";", usecols=CSV_COLS, dtype=str, chunksize=CHUNK):
        lidas += len(ch)
        c = ch[ch["cod_municipio"] == IBGE_COD_MUN]
        if c.empty:
            continue
        lat = pd.to_numeric(c["latitude"], errors="coerce")
        lon = pd.to_numeric(c["longitude"], errors="coerce")
        dentro = c[lat.between(sul, norte) & lon.between(oeste, leste)]
        if len(dentro):
            partes.append(dentro)
        print(f"  {lidas:,} linhas lidas — {sum(map(len, partes)):,} candidatos no município/bounds", end="\r")
    print()
    if not partes:
        raise RuntimeError("Nenhum endereço do CNEFE caiu no município/bounds — confira IBGE_COD_MUN e BBOX.")
    df = pd.concat(partes, ignore_index=True)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    return df.dropna(subset=["latitude", "longitude"])


def atribuir_setor(df, setores):
    """Join espacial ponto→setor: cada ponto herda o cd_setor DA MALHA
    (nunca o cod_setor do CNEFE). Descarta pontos fora dos setores da área."""
    pts = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df["longitude"], df["latitude"]), crs=CRS_WGS84
    ).to_crs(CRS_PROJETO)
    setores = setores[["cd_setor", "geometry"]].to_crs(CRS_PROJETO)
    joined = gpd.sjoin(pts, setores, how="inner", predicate="within").drop(columns="index_right")
    return joined


def main():
    print(f"CNEFE — município {IBGE_COD_MUN} (UF {COD_UF}), H3 res {H3_RESOLUCAO}\n")
    setores, bounds = limites_setores()
    print(f"{len(setores)} setores na área; bounds WGS84 (O,S,L,N) = "
          f"({bounds[0]:.4f}, {bounds[1]:.4f}, {bounds[2]:.4f}, {bounds[3]:.4f})\n")

    df = varrer_cnefe(achar_csv_uf(), bounds)
    print(f"{len(df):,} endereços do município dentro dos bounds.")

    gdf = atribuir_setor(df, setores)
    print(f"{len(gdf):,} endereços caíram dentro dos setores da área (join espacial).")

    # h3 res10 a partir das coordenadas WGS84 originais
    gdf["h3_id"] = [
        h3.latlng_to_cell(lat, lon, H3_RESOLUCAO)
        for lat, lon in zip(gdf["latitude"], gdf["longitude"])
    ]

    # (a) recorte reutilizável
    cols_recorte = ["cd_setor", "cod_especie", "dsc_estabelecimento", "h3_id", "geometry"]
    gdf[cols_recorte].to_parquet(RECORTE_PATH)
    print(f"\n  [recorte] {len(gdf):,} pontos → {RECORTE_PATH.name}")

    # (b) uso do solo por hexágono: one-hot de cod_especie → soma por h3
    cat = gdf["cod_especie"].map(ESPECIE_CAT).fillna("nao_classificado")
    onehot = pd.get_dummies(cat, prefix="cat").astype("int64")
    onehot["h3_id"] = gdf["h3_id"].values
    uso = onehot.groupby("h3_id").sum()
    uso["total_enderecos"] = uso.sum(axis=1)
    uso.reset_index().to_parquet(USO_H3_PATH)
    print(f"  [uso_h3]  {len(uso):,} hexágonos com endereços → {USO_H3_PATH.name}")

    # (c) domicílios particulares por (hexágono, setor) — peso dasimétrico
    dom = gdf[gdf["cod_especie"] == ESPECIE_DOMICILIO]
    dom_agg = (
        dom.groupby(["h3_id", "cd_setor"]).size().reset_index(name="qtd_dom")
    )
    dom_agg.to_parquet(DOM_H3_SETOR_PATH)
    print(f"  [dom_h3]  {len(dom_agg):,} pares (h3,setor); "
          f"{dom_agg['qtd_dom'].sum():,} domicílios → {DOM_H3_SETOR_PATH.name}")

    # Resumo de uso do solo na área
    resumo = uso.drop(columns="total_enderecos").sum().sort_values(ascending=False)
    print("\nEndereços por categoria de uso (CNEFE) na área:")
    for k, v in resumo.items():
        if v:
            print(f"  {k:28} {int(v):>7,}")


if __name__ == "__main__":
    main()
    print("\nConcluído.")
