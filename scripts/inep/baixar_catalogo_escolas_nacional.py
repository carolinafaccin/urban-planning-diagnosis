"""
baixar_catalogo_escolas_nacional.py
------------------------------------
O que faz   : Baixa o catálogo de escolas do INEP georreferenciado (Censo
              Escolar), para o BRASIL INTEIRO, via o pacote `geobr`
              (mantido pelo IPEA) — sem precisar raspar a página de
              microdados do INEP nem lidar com o ZIP de matrículas, que não
              traz coordenada (dado de endereço é excluído dos microdados
              por LGPD).
Saída       : {RAW_CATALOG}/inep/catalogo_escolas/<ano>/
              catalogo_escolas_brasil.parquet — um ponto por escola, colunas
              incluem code_school (código INEP, chave pra cruzar com o CSV
              de matrículas do Censo Escolar se um dia for baixado à parte),
              lat_inep/lon_inep (coordenada declarada), lat_geocodebr/
              lon_geocodebr + precisao_geocodebr (fallback geocodificado
              pelo próprio IPEA quando a escola não informou coordenada),
              tp_dependencia, tp_situacao_funcionamento, endereço, etc.
Fonte       : geobr.read_schools() — foi isso que resolveu o problema de
              coordenada: os microdados oficiais do Censo Escolar (ZIP em
              download.inep.gov.br) NÃO têm lat/lon (dado de endereço
              excluído por LGPD); o `geobr` republica um catálogo já
              geolocalizado (coordenada declarada pela escola + fallback
              geocodificado), atualizado por ano do Censo Escolar.
Como adaptar: ANO abaixo escolhe a edição do Censo Escolar (ver anos
              disponíveis com `geobr.list_geobr()`, coluna years_available
              da linha read_schools). Rodar de novo com outro ANO não
              sobrescreve pastas de anos anteriores.
Como rodar  : cd projetos/campinas   (qualquer projeto serve, só usa
              RAW_CATALOG, que é comum a todos)
              python ../../scripts/inep/baixar_catalogo_escolas_nacional.py
"""

import sys
from pathlib import Path

import geobr

sys.path.insert(0, str(Path.cwd()))
from config import RAW_CATALOG  # noqa: E402

ANO = 2025

OUT_DIR = RAW_CATALOG / "inep" / "catalogo_escolas" / str(ANO)
OUT_PATH = OUT_DIR / "catalogo_escolas_brasil.parquet"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Baixando catálogo de escolas do Brasil inteiro (Censo Escolar {ANO}) via geobr...")
    escolas = geobr.read_schools(year=ANO, code_muni="all")
    print(f"  {len(escolas)} escolas baixadas, {len(escolas.columns)} colunas.")

    escolas.to_parquet(OUT_PATH)
    print(f"  Salvo em {OUT_PATH}")


if __name__ == "__main__":
    main()
    print("\nConcluído.")
