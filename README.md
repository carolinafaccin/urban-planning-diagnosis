# Diagnóstico Territorial Urbanístico

Produto geoespacial de **diagnóstico territorial urbanístico** — mapas
temáticos e análises descritivas que identificam onde intervenções de
adaptação climática têm maior impacto potencial num território.

O produto é replicável: os scripts são genéricos e servem a qualquer
cidade, bairro ou loteamento — só o `config.py` do projeto muda. O projeto
de exemplo configurado no repositório é **Campinas/SP**.

---

## Estrutura

```text
diagnosticos-urbanisticos/
├── config/
│   ├── config.example.json     # template — copiar para config.local.json
│   └── config.local.json       # seus caminhos locais (fora do git)
│
├── scripts/                    # genéricos — servem a qualquer cidade
│   ├── pipeline/               # 01_… a 11_…  (constroem o GeoPackage)
│   ├── gee/                    # fallback LST/NDVI + catálogo nacional res10
│   └── report/                 # gerador do relatório estático (jinja2)
│
├── projetos/
│   └── campinas/
│       ├── config.py           # ← ÚNICO arquivo a editar por projeto
│       └── ref/                # contexto específico do projeto (FORA do git)
│
└── requirements.txt
```

O repositório guarda **só código**. Todos os dados e o contexto específico
de cada projeto (pasta `ref/`) ficam **fora do git** — ver abaixo.

---

## Configuração inicial

```bash
cp config/config.example.json config/config.local.json
# edite config.local.json com seus caminhos:
#   data_dir  → onde ficam os outputs de cada projeto
#   raw_dir   → seu catálogo geral de dados brutos
```

Ambiente Python:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## `raw_dir` vs `data_dir` — a distinção mais importante

| Aspecto | `raw_dir` | `data_dir` |
| --- | --- | --- |
| **O que é** | Catálogo geral de dados brutos do computador | Outputs de cada projeto |
| **Organizado por** | Fonte (`osm/`, `ibge/`, `gee/`, `mapbiomas/`...) | Projeto (`<cidade>/<projeto>/`) |
| **Documentado em** | `README.md` na raiz + um `README.md` por fonte | — (é output, não catálogo) |
| **Escopo** | Compartilhado entre todos os projetos e repositórios | Namespaced por projeto |
| **Scripts...** | **leem** daqui quando o dado já existe no catálogo | **escrevem** aqui (GeoPackage, rasters, geojsons locais) |

`raw_dir` existe independente deste repositório e é compartilhado com
outros projetos — tem seu próprio `README.md` explicando a convenção de
pastas (`t0/`, `t1/`, `t2/`, `t3/` para estágios de processamento), e cada
fonte tem seu README. **Os scripts nunca criam uma pasta nomeada com o
projeto dentro de `raw_dir`** — se precisam cachear algo bruto (ex.:
respostas de API), usam a subpasta que a própria fonte já convenciona
(ex.: `osm/overpass_cache/`).

Antes de escrever um script que baixa ou processa um dado novo, cheque se
ele já existe em `raw_dir`: `gee/` já tem LST e NDVI pré-computados por
célula H3 (por UF) e `ibge/censo/` já tem os agregados do Censo 2022
por setor censitário, por exemplo.

No `config.py` isso vira `RAW_CATALOG` (raiz de leitura) e `DATA_DIR`
(raiz de escrita do projeto, `data_dir/<cidade>/<projeto>/`).

---

## Rodando

Sempre a partir da pasta do projeto — o `cd` é obrigatório, não cosmético
(o `config.py` é importado do diretório de trabalho):

```bash
cd projetos/campinas
python ../../scripts/pipeline/01_download_osm.py
```

## Replicando para uma nova cidade/bairro

```bash
cp -r projetos/campinas projetos/<nova_cidade>
# edite o config.py: PROJECT_NAME, MUNICIPIO, UF, IBGE_COD_MUN, BBOX, ANCORA_*
# (não copie a pasta ref/ — ela é específica do projeto de origem)

cd projetos/<nova_cidade>
python ../../scripts/pipeline/01_download_osm.py
```

Nenhum script precisa ser editado — nenhum nome de lugar, coordenada ou
CRS está hard-coded neles.

---

## Scripts

O pipeline é organizado em torno de uma **malha H3 res10**: os scripts 01–04
trazem os dados por fonte, o 05 monta a malha e recebe o Censo por
**interpolação dasimétrica** (peso = domicílios do CNEFE), os 06–08 anexam
indicadores de raster/pontos por hexágono, e o 10/11 consolidam e pontuam.

| Script (`scripts/pipeline/`) | O que faz | Saída |
| --- | --- | --- |
| `01_download_osm.py` | Viário, ciclovias, parques, pontos de ônibus (OSM) | `osm.gpkg` |
| `02_download_ibge.py` | Setores + Censo 2022 (arborização, iluminação, calçada, renda) | `ibge.gpkg` |
| `03_overture_edificacoes.py` | Edificações do Overture por bbox, filtradas por confiança | `edificacoes.gpkg` |
| `04_cnefe.py` | Varre o CNEFE da UF → recorte + uso do solo + domicílios por hexágono | 3 parquets |
| `05_h3_dasimetrico.py` | Malha H3 res10 + interpolação dasimétrica do Censo + uso do solo | `h3.gpkg::h3_base` |
| `06_mapbiomas.py` | Cobertura do solo (Coleção 10) por hexágono | `h3_mapbiomas.parquet` |
| `07_cool_cities.py` | LST, vegetação, risco de calor, UTCI e cenários (Cool Cities Lab) | `h3_cool_cities.parquet` |
| `08_queimadas.py` | Focos de calor (INPE) por hexágono | `h3_queimadas.parquet` |
| `09_dados_locais.py` | Ingere geojsons à mão + fornecidos pela prefeitura | `locais.gpkg` |
| `10_build_geopackage.py` | Consolida hexágonos + vetores no `.gpkg` final, grava `_metadados` | `{PROJECT_NAME}.gpkg` |
| `11_analises.py` | Score de prioridade, cobertura de ônibus, raio de caminhabilidade | `h3_sintese`, ... |

**`scripts/gee/`** — fallback de LST/NDVI para cidades sem Cool Cities Lab, e
base do catálogo nacional res10: `gee_centroides_res10.py` (gera o CSV de
centróides) → `gee_lst_ndvi_res10.js` (roda no GEE) → `gee_ingest_res10.py`
(traz o resultado como `h3_gee.parquet`).

**`scripts/report/`** — gera um relatório estático (HTML + imagens) a partir do
GeoPackage final, para visualização rápida dos mapas. Saída no `data_dir`
(fora do git), deploy-agnóstico.

CRS de saída padrão: `EPSG:31983` (SIRGAS 2000 / UTM 23S) — parâmetro do
`config.py`.

---

## Contexto específico de cada projeto

O contexto, o escopo e quaisquer documentos de referência de um projeto ficam
em `projetos/<cidade>/ref/`, **fora do git** (não versionado). Cada projeto
mantém ali o que for específico dele; o repositório em si guarda só a
ferramenta genérica.
