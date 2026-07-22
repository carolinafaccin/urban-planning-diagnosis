"""
gee_centroides_res10_nacional.py
---------------------------------
O que faz   : Gera o CSV de centróides dos hexágonos H3 res10 do BRASIL
              INTEIRO, para subir como asset no GEE e alimentar os scripts
              gee_*_res10.js quando a intenção é construir o catálogo
              nacional (raw_dir/gee/br_h3_res10/), em vez de só a malha do
              projeto (para isso, use gee_centroides_res10.py).
Saída       : {RAW_CATALOG}/gee/br_h3_res10/_assets/br_h3_res10_centroides_por_uf/
              br_h3_res10_centroides_uf_<NN>.csv (um por UF, 27 arquivos) —
              "_assets" porque isso não é produto final do catálogo, é
              insumo pra subir como asset no GEE (mesma lógica de
              raw_dir/gee/br_h3_res9/ manter os CSVs de referência à parte
              das pastas de produto).
              colunas: h3_id, cd_setor, cd_mun, cd_uf, qtd_dom, lat, lon
Entrada     : {RAW_CATALOG}/h3/br_h3_res9.parquet (grade nacional res9,
              ~2,6 milhões de células — ver raw_dir/h3/README.md).

Método e limitação conhecida
-----------------------------
Não existe (ainda) um join CNEFE→res10 nacional — refazer isso na resolução
fina para o Brasil inteiro é um job à parte (nos moldes de 04_cnefe.py),
fora do escopo deste script. Em vez disso, cada célula res9 é subdividida
nas suas 7 células-filhas res10 (`h3.cell_to_children`), e cada filha HERDA
os metadados da célula-mãe (cd_setor, cd_mun, cd_uf, qtd_dom) — ou seja,
`qtd_dom` aqui é uma aproximação grosseira (o valor do res9 repetido 7x, não
dividido), suficiente para os scripts gee_*_res10.js (que só usam essas
colunas como metadado de acompanhamento, não para ponderar a amostragem).
Não usar esse `qtd_dom` para nada que exija precisão populacional real.

Escala real (rodado em 2026-07-22): ~28,9 M pontos no Brasil inteiro — mais
que a estimativa ingênua de 7×2,6M (~18M), porque a subdivisão em filhas não
é uniforme. UFs grandes (MG ~4,7M, BA ~3,4M, SP ~2,5M, RS ~2,6M, PR ~2,0M,
PA ~1,9M) de fato estouram "Computed value is too large" no reduceRegions
dos scripts gee_*_res10.js quando processadas num lote só — por isso esses
scripts processam cada UF em lotes de CHUNK_SIZE (ver `AMOSTRAGEM POR UF`
em cada um), não é mais preciso testar 1 UF manualmente antes de rodar as 27.

Como rodar  : cd projetos/campinas   (qualquer projeto serve, só usa
              RAW_CATALOG, que é comum a todos)
              python ../../scripts/gee/gee_centroides_res10_nacional.py
"""

import sys
from pathlib import Path

import h3
import pandas as pd

sys.path.insert(0, str(Path.cwd()))
from config import RAW_CATALOG  # noqa: E402

BR_H3_RES9_PATH = RAW_CATALOG / "h3" / "br_h3_res9.parquet"
OUT_DIR = RAW_CATALOG / "gee" / "br_h3_res10" / "_assets" / "br_h3_res10_centroides_por_uf"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    res9 = pd.read_parquet(
        BR_H3_RES9_PATH,
        columns=["h3_id", "cd_setor", "cd_mun", "cd_uf", "qtd_dom"],
    )

    for cd_uf, grupo in res9.groupby("cd_uf"):
        linhas = []
        for row in grupo.itertuples(index=False):
            filhas = h3.cell_to_children(row.h3_id, 10)
            for filha in filhas:
                lat, lon = h3.cell_to_latlng(filha)
                linhas.append(
                    (filha, row.cd_setor, row.cd_mun, row.cd_uf, row.qtd_dom, lat, lon)
                )

        df_uf = pd.DataFrame(
            linhas, columns=["h3_id", "cd_setor", "cd_mun", "cd_uf", "qtd_dom", "lat", "lon"]
        )
        out_path = OUT_DIR / f"br_h3_res10_centroides_uf_{int(cd_uf):02d}.csv"
        df_uf.to_csv(out_path, index=False)
        print(f"  [uf {int(cd_uf):02d}] {len(df_uf)} células res10 → {out_path.name}")

    print(
        "\nSuba cada CSV como asset separado no GEE (Assets → New → CSV, com "
        "lat/lon) — um FeatureCollection por UF é mais tratável que um único "
        "asset nacional gigante. Preencha ASSET_POR_UF em cada script "
        "gee_*_res10.js com o caminho de cada asset."
    )


if __name__ == "__main__":
    main()
    print("\nConcluído.")
