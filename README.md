# Diagnóstico Territorial Urbanístico

Produto geoespacial de **diagnóstico territorial urbanístico**: um pipeline
que constrói um GeoPackage por projeto (o entregável principal, para uso em
QGIS), gerando vários mapas temáticos, uma análise descritiva textual da
área analisada e um mapa-síntese final (um score de prioridade que
identifica onde intervenções de adaptação climática têm maior impacto
potencial). Complementarmente, um site (`dashboard/`) apresenta esse
diagnóstico — bônus para gestores locais e para a equipe, além de servir de
prática de visualização de dados.

O produto é replicável: os scripts são genéricos e servem a qualquer
cidade, bairro ou loteamento — só o `config.py` do projeto muda. O projeto
de exemplo configurado no repositório é **Campinas/SP**.

---

## Estrutura

```text
urban-planning-diagnosis/
├── config/
│   ├── config.example.json     # template — copiar para config.local.json
│   └── config.local.json       # seus caminhos locais (fora do git)
│
├── scripts/                    # genéricos — servem a qualquer cidade
│   ├── run.py                    # orquestrador (roda o pipeline inteiro)
│   ├── manifest.py                # ordem canônica de execução
│   ├── novo_projeto.py            # scaffold de projetos/<slug>/config.py
│   ├── _projeto.py                 # resolução de config.py (cwd/--projeto/env var)
│   ├── pipeline/                  # scripts do pipeline (constroem o GeoPackage)
│   └── gee/                       # fallback LST/NDVI + catálogo nacional res10
│
├── dashboard/                  # site React (Vite+TS+Tailwind) — diagnóstico
│   ├── data_prep/                # Python: GeoPackage → report.json + PNGs
│   ├── src/                      # componentes do site
│   ├── public/data/               # gerado por data_prep (fora do git)
│   └── deploy.py                  # build + publica no Cloudflare Pages
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
(o `config.py` é importado do diretório de trabalho). O orquestrador
(`scripts/run.py`) roda o pipeline inteiro, na ordem definida em
`scripts/manifest.py`, terminando no site publicado:

```bash
cd projetos/campinas
python ../../scripts/run.py                          # pipeline inteiro + site + deploy
python ../../scripts/run.py --from h3_dasimetrico     # a partir de um passo
python ../../scripts/run.py --only analises           # só um passo
python ../../scripts/run.py --skip deploy             # pula um passo (ex.: iterando sem publicar)
```

Cada script também roda isolado, sem o orquestrador (útil iterando em um
passo específico):

```bash
cd projetos/campinas
python ../../scripts/pipeline/download_osm.py
```

Passos que dependem de dado/config manual (ex.: `dados_municipais`,
`indicadores_municipais`, `dados_locais`) imprimem uma linha `SKIP: ...` e
seguem sem travar quando o dado não existe — o resumo final do `run.py`
lista o que foi pulado e por quê.

**Rodando sem `cd`, a partir da raiz do repo** (ver `scripts/_projeto.py`):
qualquer script individual ou o `run.py` aceitam `--projeto <slug>` (quando
o script expõe o flag, caso de `run.py`/`deploy.py`/`build_web_assets.py`)
ou a variável de ambiente `DIAGNOSTICO_PROJETO`:

```bash
python scripts/run.py --projeto campinas
DIAGNOSTICO_PROJETO=campinas python scripts/pipeline/download_osm.py
```

## Replicando para uma nova cidade/bairro

```bash
python scripts/novo_projeto.py <slug> --municipio "Sorocaba" --uf SP \
    --ibge-cod-mun 3552205 --titulo "Diagnóstico urbanístico de <bairro>, em Sorocaba"
```

Gera `projetos/<slug>/config.py` a partir do template
(`projetos/_template/config.py`) com a identificação básica preenchida. O
comando imprime um checklist do que ainda exige decisão humana antes de
rodar (BBOX, CRS_PROJETO, H3_PESOS, CAMADAS_MUNICIPAIS, CAMADA_INTERVENCAO —
todos marcados `# TODO(scaffold)` no arquivo gerado).

```bash
cd projetos/<slug>
python ../../scripts/run.py
```

Nenhum script precisa ser editado — nenhum nome de lugar, coordenada ou
CRS está hard-coded neles.

---

## Scripts

O pipeline é organizado em torno de uma **malha H3 res10**: os primeiros
scripts trazem os dados por fonte (`dados_municipais`/`app_corregos` são
opcionais), `cnefe`/`h3_dasimetrico` montam a malha e recebem o Censo por
**interpolação dasimétrica** (peso = domicílios do CNEFE), os scripts
seguintes anexam indicadores de raster/pontos por hexágono
(`indicadores_municipais` opcional), e `build_geopackage`/`analises`
consolidam e pontuam. A ordem canônica de execução vive em
`scripts/manifest.py`, não no nome dos arquivos — ver
`scripts/run.py`.

| Script (`scripts/pipeline/`) | O que faz | Saída |
| --- | --- | --- |
| `download_osm.py` | Viário, ciclovias, parques, pontos de ônibus (OSM) | `osm.gpkg` |
| `download_ibge.py` | Setores + Censo 2022 (arborização, iluminação, calçada, renda) + país/UF/município para o mapa de localização (sem recorte de bbox) | `ibge.gpkg`, `localizacao.gpkg` |
| `overture_edificacoes.py` | Edificações do Overture por bbox, filtradas por confiança | `edificacoes.gpkg` |
| `dados_municipais.py` | Ingere o catálogo de dados municipais (prefeitura), opt-in | `municipais.gpkg` |
| `app_corregos.py` | APP de córregos (Código Florestal) a partir da hidrografia | `app_corregos.gpkg` |
| `cnefe.py` | Varre o CNEFE da UF → recorte + uso do solo + domicílios por hexágono | 3 parquets |
| `h3_dasimetrico.py` | Malha H3 res10 + interpolação dasimétrica do Censo + uso do solo | `h3.gpkg::h3_base` |
| `mapbiomas.py` | Cobertura do solo (Coleção 10) por hexágono | `h3_mapbiomas.parquet` |
| `indicadores_municipais.py` | % de cobertura por hexágono das camadas municipais que alimentam o score | `h3_municipal.parquet` |
| `cool_cities.py` | LST, vegetação, risco de calor, UTCI e cenários (Cool Cities Lab) | `h3_cool_cities.parquet` |
| `queimadas.py` | Focos de calor (INPE) por hexágono | `h3_queimadas.parquet` |
| `dados_locais.py` | Ingere geojsons à mão + fornecidos pela prefeitura | `locais.gpkg` |
| `build_geopackage.py` | Consolida hexágonos + vetores no `.gpkg` final, grava `_metadados` | `{PROJECT_NAME}.gpkg` |
| `analises.py` | Score de prioridade, cobertura de ônibus | `h3_sintese`, ... |

**`scripts/gee/`** — fallback de LST/NDVI para cidades sem Cool Cities Lab, e
base do catálogo nacional res10: `gee_centroides_res10.py` (gera o CSV de
centróides) → `gee_lst_ndvi_res10.js` (roda no GEE) → `gee_ingest_res10.py`
(traz o resultado como `h3_gee.parquet`).

CRS de saída padrão: `EPSG:31983` (SIRGAS 2000 / UTM 23S) — parâmetro do
`config.py`.

---

## Site (`dashboard/`)

Site React (Vite + TypeScript + Tailwind) que apresenta o diagnóstico:
estatísticas, mapa-síntese (score de prioridade), os demais mapas temáticos,
a análise descritiva da área e as notas metodológicas. Mesmo "modo de
execução" adotado no projeto irmão `climate-injustice-index` — um único
jeito de trabalhar entre os dois repositórios.

```bash
# 1. Gerar os dados do site (a partir da pasta do projeto)
cd projetos/campinas
python ../../dashboard/data_prep/build_web_assets.py

# 2. Front-end
cd ../../dashboard
npm install
npm run dev              # http://localhost:5173
```

`dashboard/public/data/` (report.json + PNGs) é gerado pelo passo 1 e é
**gitignored** — regenerável, não sincroniza pelo GitHub. O que é
compartilhado entre máquinas (Mac/Windows) é o GeoPackage de origem, que já
fica no `data_dir` do Google Drive.

A análise descritiva da área (texto específico do projeto, não genérico) vem
de `{LOCAL_DATA_DIR}/analise_area.md` — mesmo lugar de outros inputs manuais
do projeto. Leitura tolerante: se não existir, a seção simplesmente não
aparece no site.

### Design system

Os componentes visuais (`Button`, `Card`, `KpiCard`...) vêm do
`@wri-brasil/design-system` (repositório próprio, privado, instalado via
`github:carolinafaccin/wri-brasil-design-system` no `package.json`). Ver
`dashboard/.npmrc` e a seção de pegadinhas no `CLAUDE.md` — dependências git
exigem configuração extra em npm 12+.

### Deploy

```bash
cd projetos/campinas
python ../../dashboard/deploy.py
```

Builda o site e publica no Cloudflare Pages, no branch do projeto atual (um
único Pages project guarda-chuva, um branch por projeto/bbox — vira
`<PAGES_BRANCH>.<PAGES_PROJECT>.pages.dev`, valores em `config.py`). O
acesso é restrito por Cloudflare Access (allowlist de e-mails), configurado
uma vez no painel Zero Trust.

---

## Contexto específico de cada projeto

O contexto, o escopo e quaisquer documentos de referência de um projeto ficam
em `projetos/<cidade>/ref/`, **fora do git** (não versionado). Cada projeto
mantém ali o que for específico dele; o repositório em si guarda só a
ferramenta genérica.
