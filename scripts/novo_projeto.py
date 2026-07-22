"""
novo_projeto.py
---------------
O que faz   : Cria projetos/<slug>/config.py a partir do template em
              projetos/_template/config.py, preenchendo os campos de
              identificação básica (PROJECT_NAME, MUNICIPIO, UF,
              IBGE_COD_MUN, TITULO_PROJETO, PAGES_BRANCH). Não roda nada do
              pipeline — só cria o arquivo de configuração.
Não preenche: BBOX, ANCORA_COORD, CAMADAS_MUNICIPAIS e outros campos
              marcados "# TODO(scaffold)" no template — exigem decisão
              humana (desenhar a área de estudo, escolher a âncora, etc.) e
              não são inventados aqui. Ver o checklist impresso ao final.
Como rodar  : a partir da raiz do repo:
              python scripts/novo_projeto.py <slug> --municipio "Sorocaba" \
                  --uf SP --ibge-cod-mun 3552205 \
                  --titulo "Diagnóstico urbanístico de <bairro>, em Sorocaba"
              <slug> vira o nome da pasta projetos/<slug>/, o PROJECT_NAME
              e o PAGES_BRANCH padrão (derivável, mas edite se quiser um
              subdomínio diferente).
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = REPO_ROOT / "projetos" / "_template" / "config.py"


def slugificar(texto):
    t = texto.strip().lower()
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")
    return t


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", help="nome curto do projeto (ex.: sorocaba_centro) — vira projetos/<slug>/")
    ap.add_argument("--municipio", required=True, help='ex.: "Sorocaba"')
    ap.add_argument("--uf", required=True, help="ex.: SP")
    ap.add_argument("--ibge-cod-mun", required=True, dest="ibge_cod_mun", help="código IBGE de 7 dígitos do município")
    ap.add_argument("--titulo", required=True, help="título de exibição do diagnóstico no site")
    ap.add_argument("--pages-branch", default=None,
                     help="branch do Cloudflare Pages (padrão: o próprio slug)")
    args = ap.parse_args()

    slug = slugificar(args.slug)
    if slug != args.slug:
        print(f"[aviso] slug normalizado para '{slug}'")

    destino_dir = REPO_ROOT / "projetos" / slug
    destino_config = destino_dir / "config.py"
    if destino_config.exists():
        sys.exit(f"erro: {destino_config} já existe — apague ou escolha outro slug.")

    pages_branch = args.pages_branch or slug

    texto = TEMPLATE.read_text(encoding="utf-8")
    substituicoes = {
        "__PROJECT_NAME__": slug,
        "__MUNICIPIO__": args.municipio,
        "__UF__": args.uf,
        "__IBGE_COD_MUN__": args.ibge_cod_mun,
        "__TITULO_PROJETO__": args.titulo,
        "__PAGES_BRANCH__": pages_branch,
    }
    for chave, valor in substituicoes.items():
        texto = texto.replace(chave, valor)
    texto = texto.replace(
        '"""\nconfig.py — TEMPLATE de projeto novo (gerado por scripts/novo_projeto.py)',
        f'"""\nconfig.py — parâmetros do projeto {args.municipio} (gerado por scripts/novo_projeto.py)',
    )

    destino_dir.mkdir(parents=True, exist_ok=False)
    destino_config.write_text(texto, encoding="utf-8")

    print(f"Criado: {destino_config}")
    print(
        "\nPendências antes de rodar o pipeline (procure '# TODO(scaffold)' no arquivo):\n"
        "  - BBOX: desenhe a área de estudo (ex.: geojson.io) e preencha os 4 vértices.\n"
        "  - CRS_PROJETO: confirme a zona UTM/SIRGAS 2000 correta da região.\n"
        "  - ANCORA_COORD / ANCORA_NOME / RAIO_ANCORA: ponto-âncora de caminhabilidade,\n"
        "    se houver um natural (senão deixe fora do BBOX de propósito — o pipeline\n"
        "    avisa e pula essa análise sem travar).\n"
        "  - H3_PESOS: reavalie os pesos padrão para o território.\n"
        "  - CAMADAS_MUNICIPAIS: opcional — só depois de catalogar/baixar o portal da\n"
        "    prefeitura (ver CLAUDE.md, 'Procedimento para catalogar/baixar o portal\n"
        "    de uma NOVA cidade').\n"
        "  - CAMADA_INTERVENCAO: opcional — só se a área de estudo tiver um sub-recorte\n"
        "    de intervenção (ex.: um loteamento) diferente da área de estudo inteira.\n"
        f"\nDepois de preencher: cd projetos/{slug} && python ../../scripts/pipeline/run.py"
    )


if __name__ == "__main__":
    main()
