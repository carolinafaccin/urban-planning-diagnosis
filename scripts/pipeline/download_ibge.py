"""
download_ibge.py
-------------------
O que faz   : Monta a camada de setores censitários da área de estudo, com
              os indicadores do Censo 2022 usados nos mapas 7, 8, 9 e 15 e
              no score de prioridade do analises.py. Também monta as
              camadas de CONTEXTO para o mapa de localização (país > UF >
              município), a partir da malha municipal do IBGE.
Camadas     : setores_censitarios (ibge.gpkg)
              pais, uf, municipios_uf (localizacao.gpkg)
Fonte       : Catálogo raw_dir/ibge/ (nada é baixado — os dados já estão no
              catálogo geral):
              - censo/2022/setores_censitarios/br_setores.gpkg (malha, EPSG:5880)
              - censo/2022/entorno_domicilios/agregados_por_setor/entorno_domicilios.csv
              - censo/2022/agregados_por_setores/t1/renda_responsavel.csv
              - malha_municipal/2024/{pais,uf,municipios}.gpkg (EPSG:5880)
Saída       : {DATA_DIR}/ibge.gpkg (setores_censitarios) e
              {DATA_DIR}/localizacao.gpkg (pais, uf, municipios_uf),
              reprojetados para CRS_PROJETO.
Para adaptar: ajuste BBOX e IBGE_COD_MUN no config.py. Nada aqui é
              específico de Campinas — a malha e os CSVs são nacionais.

Nota sobre `localizacao.gpkg`: DIFERENTE de todo o resto do pipeline, essas
3 camadas NÃO são recortadas pelo BBOX do projeto — são pro mapa de
localização multi-escala (Brasil > UF > município, ver mapa 1 do
diagnóstico), então precisam ficar na escala nacional/estadual inteira, com
o município do projeto identificável por atributo (`cd_mun`/`cd_uf`) para
estilizar em destaque no QGIS, não recortado.

Notas sobre os dados
--------------------
- A malha nacional tem 1,4 GB e ~473 mil setores. O filtro por BBOX usa o
  índice espacial do GeoPackage (~10s); um filtro por atributo (`where=`)
  força varredura da tabela inteira e leva vários minutos, sobretudo com o
  catálogo no Google Drive. Não troque um pelo outro.
- O bloco "entorno dos domicílios" do Censo só foi aplicado em uma parte
  dos setores (~341 mil de ~473 mil). Setores fora da amostra ficam com os
  indicadores de entorno nulos — é esperado, não é erro. O script reporta
  quantos ficaram sem dado.
- Os percentuais de entorno são sobre DOMICÍLIOS (variáveis V050xx). Existe
  no catálogo uma série paralela por MORADORES (V052xx, em
  percentuais_por_setor_gpkg/) — não misturar as duas.
- `renda_media_norm` é a renda média invertida e normalizada [0,1] DENTRO da
  área de estudo (maior = mais vulnerável), como o analises.py espera.
  Por ser relativa ao recorte, não é comparável entre projetos.

Como rodar  : a partir da pasta do projeto (onde está o config.py):
              cd projetos/campinas
              python ../../scripts/pipeline/download_ibge.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

# Preenchidos por main(cfg) — usados como globais pelas funções auxiliares
# abaixo (carregar_malha, gerar_localizacao), chamadas de dentro de main.
BBOX = CRS_PROJETO = CRS_WGS84 = IBGE_COD_MUN = MUNICIPIO = None
IBGE_GPKG_PATH = LOCALIZACAO_GPKG_PATH = None
MALHA_PATH = ENTORNO_PATH = RENDA_PATH = None
MALHA_MUNICIPAL_DIR = COD_UF = None

# Variáveis do bloco "entorno dos domicílios" (contagem de domicílios).
# Ver _dicionario_entorno_domicilios.xlsx no catálogo.
ENTORNO_VARS = {
    "v05000": "domicilios_entorno",   # total de domicílios pesquisados no entorno
    "v05007": "dom_sem_pavimento",    # via pavimentada - NÃO
    "v05013": "dom_sem_ilum",         # iluminação pública - NÃO
    "v05022": "dom_sem_calcada",      # calçada - NÃO
    "v05030": "dom_sem_arb",          # arborização - SEM ÁRVORES
}

# Variáveis de renda do responsável. Ver _dicionario_de_dados_renda_responsavel.xlsx
RENDA_VARS = {
    "v06001": "responsaveis",         # pessoas responsáveis
    "v06002": "moradores",            # moradores
    "v06004": "renda_media",          # rendimento nominal médio mensal do responsável (R$)
}

# Percentuais derivados: nome final -> numerador
PERCENTUAIS = {
    "pct_sem_arb": "dom_sem_arb",
    "pct_sem_ilum": "dom_sem_ilum",
    "pct_sem_calcada": "dom_sem_calcada",
    "pct_sem_pavimento": "dom_sem_pavimento",
}


def carregar_malha():
    """Lê os setores que intersectam o BBOX, via índice espacial da malha."""
    print(f"Lendo malha de setores (filtro espacial pelo BBOX)...\n  {MALHA_PATH}")
    caixa = gpd.GeoSeries(
        [box(BBOX["west"], BBOX["south"], BBOX["east"], BBOX["north"])], crs=CRS_WGS84
    )
    gdf = gpd.read_file(MALHA_PATH, bbox=caixa)
    print(f"  {len(gdf)} setores intersectam a área de estudo.")

    fora = gdf.loc[gdf["cd_mun"] != IBGE_COD_MUN, "nm_mun"].unique()
    if len(fora):
        print(
            f"  AVISO: o BBOX alcança outro(s) município(s) além de {MUNICIPIO}: "
            f"{', '.join(map(str, fora))}. Os setores foram mantidos — se não for "
            f"intencional, ajuste o BBOX no config.py."
        )
    return gdf


def carregar_tabela(caminho, variaveis, **kwargs):
    """Lê um CSV do catálogo trazendo só as colunas de interesse, já renomeadas.

    Lê tudo como texto e converte à mão porque `decimal=","` não é confiável
    aqui: renda_responsavel.csv usa vírgula decimal mas tem células com lixo
    (uma vírgula solta em v06004). Basta uma para o pandas desistir da coluna
    inteira e devolvê-la como texto — e aí um to_numeric direto zeraria todos
    os valores válidos, silenciosamente.
    """
    colunas = ["cd_setor", *variaveis]
    df = pd.read_csv(caminho, usecols=colunas, dtype=str, **kwargs)
    for col in variaveis:
        df[col] = pd.to_numeric(df[col].str.replace(",", ".", regex=False), errors="coerce")
    return df.rename(columns=variaveis)


def normalizar_invertido(serie):
    """Min-max invertido para [0, 1]: o menor valor vira 1 (mais vulnerável)."""
    minimo, maximo = serie.min(), serie.max()
    if pd.isna(minimo) or maximo == minimo:
        return pd.Series(0.0, index=serie.index)
    return (maximo - serie) / (maximo - minimo)


def gerar_localizacao():
    """Camadas de contexto (país/UF/município) pro mapa de localização — sem
    recorte por BBOX, ao contrário do resto do pipeline (ver nota no
    cabeçalho do arquivo)."""
    print("Lendo malha municipal do IBGE (país/UF/municípios)...")

    pais = gpd.read_file(MALHA_MUNICIPAL_DIR / "pais.gpkg", layer="temp_pais")
    uf = gpd.read_file(MALHA_MUNICIPAL_DIR / "uf.gpkg", layer="temp_uf")
    municipios = gpd.read_file(MALHA_MUNICIPAL_DIR / "municipios.gpkg", layer="temp_municipios")
    municipios_uf = municipios[municipios["cd_uf"] == COD_UF]

    pais = pais.to_crs(CRS_PROJETO)
    uf = uf.to_crs(CRS_PROJETO)
    municipios_uf = municipios_uf.to_crs(CRS_PROJETO)

    # Simplificação: a malha do IBGE vem com detalhe de costa/fronteira muito
    # mais fino do que um mapa de localização (escala país/UF) precisa — sem
    # isso, essas 3 camadas sozinhas somam ~42 MB de geometria e estouram o
    # limite de 25 MiB por arquivo do Cloudflare Pages (usado pelo
    # dashboard/deploy.py pra servir o .gpkg pra download). Tolerância em
    # metros (CRS_PROJETO já é métrico) — 200 m é imperceptível numa vista de
    # país/estado e reduz pra ~2 MB no total.
    SIMPLIFY_TOLERANCE_M = 200
    pais["geometry"] = pais.geometry.simplify(SIMPLIFY_TOLERANCE_M, preserve_topology=True)
    uf["geometry"] = uf.geometry.simplify(SIMPLIFY_TOLERANCE_M, preserve_topology=True)
    municipios_uf["geometry"] = municipios_uf.geometry.simplify(
        SIMPLIFY_TOLERANCE_M, preserve_topology=True
    )

    pais.to_file(LOCALIZACAO_GPKG_PATH, layer="pais", driver="GPKG")
    uf.to_file(LOCALIZACAO_GPKG_PATH, layer="uf", driver="GPKG")
    municipios_uf.to_file(LOCALIZACAO_GPKG_PATH, layer="municipios_uf", driver="GPKG")

    print(
        f"  [localizacao] pais (1), uf (27), municipios_uf ({len(municipios_uf)} da UF "
        f"{COD_UF}) → {LOCALIZACAO_GPKG_PATH.name}. Destaque o município do projeto "
        f"no QGIS filtrando cd_mun == '{IBGE_COD_MUN}' em municipios_uf, e a UF "
        f"filtrando cd_uf == '{COD_UF}' em uf."
    )


def main(cfg):
    global BBOX, CRS_PROJETO, CRS_WGS84, IBGE_COD_MUN, MUNICIPIO
    global IBGE_GPKG_PATH, LOCALIZACAO_GPKG_PATH
    global MALHA_PATH, ENTORNO_PATH, RENDA_PATH
    global MALHA_MUNICIPAL_DIR, COD_UF

    BBOX = cfg.BBOX
    CRS_PROJETO = cfg.CRS_PROJETO
    CRS_WGS84 = cfg.CRS_WGS84
    IBGE_COD_MUN = cfg.IBGE_COD_MUN
    MUNICIPIO = cfg.MUNICIPIO

    IBGE_GPKG_PATH = cfg.DATA_DIR / "ibge.gpkg"
    LOCALIZACAO_GPKG_PATH = cfg.DATA_DIR / "localizacao.gpkg"

    censo_dir = cfg.RAW_CATALOG / "ibge" / "censo" / "2022"
    MALHA_PATH = censo_dir / "setores_censitarios" / "br_setores.gpkg"
    ENTORNO_PATH = censo_dir / "entorno_domicilios" / "agregados_por_setor" / "entorno_domicilios.csv"
    RENDA_PATH = censo_dir / "agregados_por_setores" / "t1" / "renda_responsavel.csv"

    MALHA_MUNICIPAL_DIR = cfg.RAW_CATALOG / "ibge" / "malha_municipal" / "2024"
    COD_UF = IBGE_COD_MUN[:2]

    print(f"Área de estudo (WGS84): {BBOX}")
    print(f"Destino: {IBGE_GPKG_PATH}\n")

    setores = carregar_malha()

    print("Lendo entorno dos domicílios (Censo 2022)...")
    entorno = carregar_tabela(ENTORNO_PATH, ENTORNO_VARS, sep=";")

    print("Lendo renda do responsável (Censo 2022)...")
    renda = carregar_tabela(RENDA_PATH, RENDA_VARS, sep=",")

    setores = setores.merge(entorno, on="cd_setor", how="left")
    setores = setores.merge(renda, on="cd_setor", how="left")

    # Percentuais de entorno. O denominador é o total de domicílios
    # pesquisados no entorno — nulo/zero nos setores fora da amostra.
    total = setores["domicilios_entorno"].replace(0, pd.NA)
    for destino, origem in PERCENTUAIS.items():
        setores[destino] = setores[origem] / total * 100

    # Renda invertida e normalizada — o que o analises.py usa como vuln_social
    setores["renda_media_norm"] = normalizar_invertido(setores["renda_media"])

    sem_entorno = int(setores["domicilios_entorno"].isna().sum())
    if sem_entorno:
        print(
            f"  {sem_entorno} de {len(setores)} setores estão fora da amostra de "
            f"entorno do Censo — indicadores de entorno ficaram nulos (esperado)."
        )
    sem_renda = int(setores["renda_media"].isna().sum())
    if sem_renda:
        print(f"  {sem_renda} de {len(setores)} setores sem dado de renda.")

    setores = setores.to_crs(CRS_PROJETO)
    setores.to_file(IBGE_GPKG_PATH, layer="setores_censitarios", driver="GPKG")
    print(
        f"\n  [setores_censitarios] {len(setores)} feições salvas em "
        f"{IBGE_GPKG_PATH} (camada 'setores_censitarios')"
    )

    resumo = setores[["pct_sem_arb", "pct_sem_ilum", "renda_media"]].describe()
    print("\nResumo dos indicadores na área de estudo:")
    print(resumo.round(1).to_string())

    gerar_localizacao()

    print("\nConcluído.")


if __name__ == "__main__":
    sys.path.insert(0, str(Path.cwd()))
    import config
    main(config)
