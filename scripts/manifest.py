"""
manifest.py
-----------
Ordem canônica de execução do pipeline (scripts/pipeline/, mais os passos de
site/deploy do dashboard/). A ordem é a POSIÇÃO na lista PASSOS, não o nome
do arquivo — os arquivos não têm mais prefixo numérico (ver CLAUDE.md,
"reorganização sem números no nome do arquivo"). O nome do módulo (`modulo`)
é só o stem do arquivo (sem `.py`), lido via importlib pelo run.py.

Cada passo é um dict com:
- modulo    : stem do arquivo (sem .py), usado como identificador nos
              argumentos --from/--only/--skip.
- caminho   : opcional. Caminho do arquivo relativo à raiz do repo, para
              passos que não moram em scripts/pipeline/ (ex.: dashboard/).
              Quando ausente, o run.py assume scripts/pipeline/<modulo>.py.
- opcional  : True marca passos que dependem de um dado/config manual e que
              o pipeline pula com segurança quando ele não existe
              (sinalizado pelo próprio script com uma linha "SKIP: ..."; ver
              run.py).
- kwargs    : opcional. Argumentos extras passados para main(cfg, **kwargs)
              deste passo (ver deploy: skip_data=True porque o passo
              build_web_assets, logo antes no manifesto, já gerou os dados).

Como cada `opcional` foi decidido (ver cabeçalho "Requer" de cada script):
- dados_municipais e indicadores_municipais: tolerantes a CAMADAS_MUNICIPAIS
  vazio no config.py — cidade sem portal municipal cadastrado faz esses dois
  não gravarem nada e o resto seguir igual.
- dados_locais: tolerante a LOCAL_DATA_DIR/SOLICITADOS_DATA_DIR vazios —
  depende de geojson/analise_area.md preenchidos à mão pela equipe.
- Os demais são obrigatórios: mesmo os que avisam e pulam sub-etapas
  internamente quando falta uma fonte específica (app_corregos sem
  hidrografia, build_geopackage com enriquecimento ausente) esperam rodar
  com sucesso no fluxo padrão — não são opt-in por config.
- build_web_assets: obrigatório (gera o site a partir do GeoPackage final).
- deploy: obrigatório no manifesto padrão, mas facilmente pulável com
  `--skip deploy` (ex.: iterando localmente sem publicar a cada rodada) —
  não criamos uma flag dedicada tipo --skip-deploy porque o mecanismo
  genérico --skip já resolve isso.
"""

PASSOS = [
    dict(modulo="download_osm", opcional=False),
    dict(modulo="download_ibge", opcional=False),
    dict(modulo="overture_edificacoes", opcional=False),
    dict(modulo="dados_municipais", opcional=True),   # pula se CAMADAS_MUNICIPAIS vazio
    dict(modulo="app_corregos", opcional=False),
    dict(modulo="cnefe", opcional=False),
    dict(modulo="h3_dasimetrico", opcional=False),
    dict(modulo="mapbiomas", opcional=False),
    dict(modulo="indicadores_municipais", opcional=True),  # pula se CAMADAS_MUNICIPAIS vazio
    dict(modulo="cool_cities", opcional=False),
    dict(modulo="queimadas", opcional=False),
    dict(modulo="dados_locais", opcional=True),  # depende de geojson/analise_area.md manual
    dict(modulo="build_geopackage", opcional=False),
    dict(modulo="analises", opcional=False),
    dict(modulo="build_web_assets", caminho="dashboard/data_prep/build_web_assets.py", opcional=False),
    dict(modulo="deploy", caminho="dashboard/deploy.py", opcional=False,
         kwargs=dict(skip_data=True)),
]
