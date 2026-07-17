# CLAUDE.md

Orientação para trabalhar neste repositório. Leia antes de mexer nos
scripts ou em `config/config.local.json`.

## O que é este repositório

Produto geoespacial de **diagnóstico territorial urbanístico**: mapas
temáticos + análises descritivas que identificam onde intervenções de
adaptação climática têm maior impacto num território. Projeto de exemplo
configurado: Campinas/SP.

O produto é replicável: `scripts/` é genérico e serve a qualquer cidade,
bairro ou loteamento; `projetos/<cidade>/config.py` é o único arquivo que
muda por projeto.

Ver `README.md` para a visão geral e o passo a passo de replicação. O
contexto e o escopo específicos de cada projeto (incluindo `PLANO.md` e a
lista de tarefas) ficam em `projetos/<cidade>/ref/`, **fora do git** — leia
essa pasta ao trabalhar num projeto, mas nada dali entra em commit.

## Regra crítica: `raw_dir` vs `data_dir`

Isso já causou um bug real (uma pasta de projeto foi criada por engano
dentro do `raw_dir` — teve que ser removida manualmente). **Não repita.**

- `raw_dir` (definido em `config/config.local.json`) é o catálogo GERAL de
  dados brutos do usuário, organizado por **fonte** (`osm/`, `ibge/`,
  `gee/`, `mapbiomas/`...), documentado em `<raw_dir>/README.md` e um
  `README.md` por fonte. **Já existe independente deste repo** e é
  compartilhado com outros projetos fora daqui.
  - Scripts **leem** de `raw_dir` quando o dado já existe no catálogo.
  - Scripts **nunca criam uma pasta nova nomeada com o projeto/cidade
    dentro de `raw_dir`**. Se precisam cachear algo bruto (ex.: respostas
    de API), usam a subpasta que a própria fonte já convenciona (ex.:
    `01_download_osm.py` aponta o cache do osmnx para
    `raw_dir/osm/overpass_cache/`, que já existia antes deste repo).
  - Antes de escrever um script que baixa/processa um dado, **cheque se ele
    já existe em `raw_dir`** lendo o README daquela fonte. Ex.:
    `gee/land_surface_temperature/` e `gee/areas_verdes_ndvi/` já têm
    LST/NDVI pré-computados nacionalmente por célula H3 **res9** (por UF);
    `ibge/censo/2022/` já tem os agregados por setor censitário. Extrair/
    filtrar o que existe é preferível a reprocessar do zero — mas confira a
    resolução (ver TODO abaixo).

- `data_dir` (também em `config.local.json`) é onde o projeto grava seus
  **outputs**: GeoPackage final, rasters processados, geojsons desenhados à
  mão, arquivos fornecidos pela prefeitura. Aqui sim é namespaced por
  projeto: `data_dir/<cidade>/<projeto>/`.

No `config.py` isso vira `RAW_CATALOG` (raiz de leitura, sem `mkdir`) e
`DATA_DIR` (raiz de escrita do projeto, com `mkdir`).

## Convenções dos scripts

- `scripts/` é genérico: **nenhum nome de lugar, coordenada ou CRS
  hard-coded**. Tudo vem de `config.py`.
- `projetos/<cidade>/config.py` é o **único arquivo a editar** para rodar em
  um novo projeto.
- Scripts rodam a partir da pasta do projeto (o `config.py` é importado via
  `sys.path.insert(0, str(Path.cwd()))` — por isso o `cd` antes de rodar é
  obrigatório, não cosmético):
  `cd projetos/campinas && python ../../scripts/01_download_osm.py`.
- `REPO_ROOT` no `config.py` é resolvido por busca ascendente (helper
  `_find_repo_root`, procura a pasta que contém `config/config.local.json`)
  — robusto a mudanças de profundidade. Não usar índice fixo de `parents[N]`.
- Nada de dado entra no git — nem de `raw_dir`, nem de `data_dir`, nem na
  pasta do projeto. O repo guarda só código. Ver `.gitignore`
  (`projetos/**/data/`, `**/cache/`, `**/*.gpkg` como rede de segurança).
- CRS de saída padrão: `EPSG:31983` (SIRGAS 2000 / UTM 23S) — parâmetro do
  `config.py`, não fixo no código.
- Cada script tem cabeçalho padrão documentando: o que faz, camadas geradas,
  fonte, saída, como adaptar e como rodar.

## Ambiente Python

`venv/` na raiz do repo (não versionado). Dependências em `requirements.txt`:
osmnx/overpy (OSM), geopandas/shapely/pandas/pyarrow (base), overturemaps/duckdb
(edificações), h3 (malha), rasterio/rasterstats (zonal stats), openpyxl (dicionários).

```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Pegadinhas já descobertas (osmnx / overpy)

- **osmnx 2.x** mudou a assinatura de `graph_from_bbox` e
  `features_from_bbox`: agora é um único parâmetro `bbox` no formato
  `(left, bottom, right, top)` = `(west, south, east, north)` — não mais
  `north, south, east, west` separados. Confirmado via `inspect.signature`
  na v2.1.0; não confie em exemplos antigos.
- **Overpass API rejeita requisições sem User-Agent** (HTTP 406). `overpy`
  usa `urllib` puro e não expõe headers na API pública — a correção é
  registrar um opener global via `urllib.request.install_opener()` antes de
  qualquer chamada (ver início de `01_download_osm.py`).
- **osmnx grava cache HTTP em `./cache/` por padrão**, relativo à pasta onde
  o script roda — polui o repo se não for redirecionado via
  `ox.settings.cache_folder` (ver regra `raw_dir` acima: aponta para
  `raw_dir/osm/overpass_cache/`, não para uma pasta nova).
- `features_from_bbox` levanta `osmnx._errors.InsufficientResponseError`
  quando a consulta não retorna nada (ex.: sem ciclovias na área) — tratar
  em vez de deixar quebrar.
- GeoPackage não aceita colunas de listas/dicts (comuns em tags do OSM) —
  converter para string antes de gravar (ver `salvar_camada`).

## Pegadinhas do pipeline H3 / CNEFE / dasimétrica

- **CNEFE × malha: os códigos de setor NÃO batem.** O `cod_setor` do CNEFE
  2022 é de outra versão que o `cd_setor` da malha `br_setores.gpkg` (num caso
  observado, distrito 05 no CNEFE vs 30/35 na malha, para o mesmo lugar). Join
  por código dá zero match silencioso. Sempre atribua setor por **join
  espacial** (point-in-polygon), nunca por código. Ver cabeçalho do `04_cnefe.py`.
- **Interpolação dasimétrica: intensiva ≠ extensiva.** A fórmula do
  climate-injustice-index (`Valor × domicílios/total_setor`) é para *contagens*
  (extensivas). Renda e percentuais são *médias/taxas* (intensivas) e precisam
  de **média ponderada por domicílios dentro do hexágono**. Trocar uma pela
  outra subestima o valor silenciosamente (renda saiu ~536 em vez de ~2.290 na
  1ª versão). Ver cabeçalho do `05_h3_dasimetrico.py`.
- **A malha de setores tem 1,4 GB.** Filtrar por bbox usa o índice espacial
  (~10s); filtrar por atributo (`where=`) varre a tabela inteira (minutos no
  Drive). Ver `02_download_ibge.py`.
- **CNEFE por UF tem ~3,6 GB.** O `04` varre uma vez e salva um recorte do
  projeto (`processed/cnefe_recorte.parquet`) — os demais scripts leem o
  recorte, não a UF.
- **`renda_responsavel.csv` tem célula com lixo** (vírgula solta) que faz o
  pandas devolver a coluna como texto; converter a vírgula decimal à mão (ver `02`).
- Rasters do **Cool Cities** cobrem só a mancha urbana (baseline) e a
  `accelerator_area` ≈ bbox (cenários) — hexágonos de borda ficam nulos nesses
  campos; o score do `11` renormaliza os pesos sobre o que existe.

## Estado atual

- **Pipeline completo (01–11 + gee_*) escrito e rodando** no projeto de exemplo.
  Malha H3 res10 (293 hexágonos) com Censo dasimétrico, uso do solo (CNEFE),
  edificações (Overture), cobertura (MapBiomas col.10), calor/vegetação/UTCI
  (Cool Cities), queimadas (INPE) e score de prioridade. GeoPackage final em
  `<data_dir>/<cidade>/<projeto>/<projeto>.gpkg`, camada `h3_sintese`.
- **GEE fora do caminho crítico quando há Cool Cities** (que cobre LST/vegetação/
  risco/UTCI). Continua como **fallback** para cidades sem Cool Cities e como
  base do catálogo nacional res10 — scripts `gee_*` prontos; a extração nacional
  é um job à parte.
- **Pendências específicas do projeto** (geojsons à mão, dados da prefeitura,
  coordenada da âncora — `ANCORA_COORD` cai fora do bbox, marcado `TODO`, só o
  `11` usa) ficam na lista de tarefas em `projetos/<cidade>/ref/` (fora do git).
- Educação: o `04` já extrai ensino/saúde do CNEFE geocodificados — pode
  dispensar uma fonte INEP separada.
  