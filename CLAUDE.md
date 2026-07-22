# CLAUDE.md

Orientação para trabalhar neste repositório. Leia antes de mexer nos
scripts ou em `config/config.local.json`.

## O que é este repositório

Produto geoespacial de **diagnóstico territorial urbanístico**: um pipeline
que constrói um GeoPackage por projeto (entregável principal, para uso em
QGIS) — vários mapas temáticos, uma análise descritiva textual da área
analisada e um mapa-síntese final (score de prioridade) que identifica onde
intervenções de adaptação climática têm maior impacto num território.
Complementarmente, um site em `dashboard/` apresenta esse diagnóstico
(bônus para gestores locais e para a equipe). Projeto de exemplo
configurado: Campinas/SP.

O produto é replicável: `scripts/` é genérico e serve a qualquer cidade,
bairro ou loteamento; `projetos/<cidade>/config.py` é o único arquivo que
muda por projeto. O `dashboard/` segue a mesma lógica — o código React é
genérico, só os dados que ele consome (gerados por projeto) mudam.

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

## Convenções de dados municipais (prefeitura)

**Regra de ouro:** preferir dado municipal quando existir e for mais preciso;
fallback para nacional/global quando faltar ou tiver baixa qualidade.
Edificações, viário (topologia) e censo demográfico são **sempre**
nacionais/globais — nunca substituídos por dado municipal, em nenhuma cidade.

### Framework de 3 categorias

Toda camada municipal (desta cidade ou de uma futura) se encaixa numa destas:

1. **Sempre global/nacional** (nunca há substituto): edificações
   (`03_overture_edificacoes.py`), viário/topologia (`01_download_osm.py`),
   censo (`02`/`04`). Um dado municipal equivalente (ex.: classificação
   viária por decreto) só entra como **enriquecimento de atributo** sobre a
   camada global — nunca a substitui — porque a topologia de rede do OSM
   (grafo conectado, nós roteáveis) tem garantias que um shapefile municipal
   de eixos tipicamente não tem. Ver `enriquecer_viario()` em
   `04_dados_municipais.py`: gera `viario_enriquecido.gpkg` (cópia do viário
   OSM + coluna extra via join espacial), sem tocar em `osm.gpkg`.
2. **Preferir municipal, fallback global** — quando os dois alimentam o MESMO
   indicador do score. Usa o mecanismo que já existe em
   `14_analises.py::INDICADORES` (`fontes=[...]`, primeira coluna presente
   vence — o mesmo que já resolve LST do Cool Cities OU do GEE). Não inventar
   um novo mecanismo de fallback por camada; sempre estender essa lista.
3. **Exclusivo municipal, aditivo** (sem equivalente global no pipeline
   hoje): a maioria das camadas de um portal municipal — equipamentos
   públicos, hidrografia, risco/suscetibilidade, unidades de conservação,
   divisões administrativas etc. Entram no GeoPackage final como camada
   extra, sem lógica de fallback. Risco de inundação/movimento de massa é
   candidato natural a virar uma NOVA dimensão do score (`H3_PESOS`) no
   futuro — só depois de rodar com dados reais, não antecipar agora.

### Registro por projeto: `CAMADAS_MUNICIPAIS` (config.py)

Dict vazio por padrão — cidade sem portal municipal utilizável faz o
pipeline seguir idêntico ao comportamento sem dado municipal (opt-in, nunca
obrigatório). Cada entrada: `{"arquivo": stem do shapefile em
raw_dir/prefeituras_municipais/<slug>/t0/, "indicador_score": None ou a
chave de H3_PESOS que essa camada alimenta}`. Ver
`projetos/campinas/config.py` para o exemplo populado (49 camadas).

Scripts que leem esse registro: `04_dados_municipais.py` (ingestão bruta,
recorte por bbox → `municipais.gpkg`) e `09_indicadores_municipais.py`
(zonal stats de % de cobertura por hexágono para as entradas com
`indicador_score` → `h3_municipal.parquet`, consumido pelo `11`).

### Procedimento para catalogar/baixar o portal de uma NOVA cidade

Quando a usuária pedir para investigar o portal de dados geoespaciais de uma
prefeitura (ex.: "faz o mesmo para a prefeitura de X"), repita o processo
usado para Campinas nesta ordem:

1. Ler `projetos/<cidade>/ref/PLANO.md`/`TAREFAS.md` para ver o que já se
   sabe sobre o portal daquele município (se houver).
2. Encontrar o portal de metadados/dados geoespaciais (URL dada pela usuária
   ou pesquisada). Se for uma SPA client-side (Angular/React), WebFetch/curl
   não bastam — usar Playwright para renderizar e extrair a lista completa.
3. Gerar `projetos/<cidade>/ref/catalogo_<orgao>_metadados.md` com
   **checkboxes** (`- [ ] nome — descrição curta`), um item por dataset —
   nunca em tabela. A usuária prefere marcar caixas e aprovar em rodadas, não
   tudo de uma vez.
4. Aguardar a usuária marcar os itens; ela pode fazer isso em mais de uma
   rodada — ao reabrir o arquivo, comparar com o que já foi baixado antes
   para achar só os itens novos.
5. Baixar só os itens marcados, validando cada um (geopandas: contagem de
   feições, tipo de geometria, CRS) antes de gravar. Desconfiar de conteúdo
   suspeito (schema/contagem idêntica a outro dataset já baixado — aconteceu
   com `classificacao_viaria` vs `lotes_SIM` em Campinas, bug do lado do
   servidor) e testar de novo antes de aceitar.
6. Gravar em `raw_dir/prefeituras_municipais/<slug_cidade>/t0/`, documentar
   em `README.md` (proveniência, datasets sem link de download, falhas de
   servidor conhecidas) e marcar o status (`✅ baixado`/`❌ falhou`/
   `⚠️ sem link`) de volta no arquivo de catálogo com checkboxes.
7. Popular `CAMADAS_MUNICIPAIS` no `config.py` daquela cidade, classificando
   cada camada baixada nas 3 categorias acima.

O mecanismo de raspagem em si (scripts Playwright ad hoc) é ferramenta
pontual da cidade — cada prefeitura tem um portal diferente (SPA, GeoServer/
WFS, ArcGIS REST, ou nenhum portal) — e **não entra em `scripts/`**. O
pipeline genérico só começa a existir a partir do shapefile já pousado em
`t0/`.

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

## Convenções do `dashboard/` (site)

- Mesma lógica do `scripts/`: o código React (`dashboard/src/`) é genérico;
  o que muda por projeto são os dados que ele consome, nunca o código.
- `dashboard/data_prep/build_web_assets.py` lê o GeoPackage do projeto e
  escreve `report.json` + PNGs em `REPORT_DIR` (config.py), depois
  sincroniza (com limpeza prévia) para `dashboard/public/data/` — que é
  **gitignored**, regenerado localmente em cada máquina (mesma regra de
  "nada de dado entra no git" do resto do repo).
- A análise descritiva da área (texto específico do projeto, diferente da
  descrição genérica de cada indicador) vem de
  `{LOCAL_DATA_DIR}/analise_area.md` — mesmo lugar de outros inputs manuais
  do projeto (ver `12_dados_locais.py`). Leitura tolerante: se não existir,
  a seção não aparece.
- `dashboard/deploy.py` builda (`npm run build`) e publica no Cloudflare
  Pages, lendo `PAGES_PROJECT`/`PAGES_BRANCH` do `config.py` do projeto —
  mesmo padrão de "config.py é a fonte única" dos outros scripts, só que
  reimplementado em Python puro chamando `npm`/`wrangler` via subprocess.
- Componentes visuais vêm do `@wri-brasil/design-system` (repositório
  próprio, privado). O `RampLegend` do pacote é hardcoded para a rampa de 5
  classes do índice nacional (`iicRamp`) — não serve para a classificação de
  `prioridade` daqui (4 classes, outras cores). A legenda do mapa-síntese é
  construída à mão em `SinteseSection.tsx`, com os valores espelhados de
  `MAPAS["prioridade"]` em `build_web_assets.py` (sem sincronização
  automática entre os dois — mudar um exige mudar o outro à mão).
- **Identidade visual alinhada com o `climate-injustice-index`** (mesmo
  produto WRI Brasil, "olhar" parecido): `TopBar`/`Footer` com o logo em
  `public/wri-brasil-logo(-k).png` + `favicon.ico` (copiados do repo-irmão,
  não redesenhados), botão "Salvar como PDF" (`window.print()` + CSS de
  impressão), e markdown (`AnaliseArea`/`MethodologyNotes`) estilizado com a
  classe `.prose-notes` (tokens da marca em `index.css`) em vez do plugin
  `@tailwindcss/typography` — mesma escolha do repo-irmão, que usa a mesma
  técnica. Diferente do repo-irmão: sem mapas interativos (decisão já
  registrada acima) e roteamento reduzido ao mínimo (ver abaixo) — site de um
  projeto só, não um explorador multi-município.
- **Rodapé fixo** (`Footer.tsx`, `fixed inset-x-0 bottom-0`) — sempre visível
  na tela, com o link para as notas metodológicas. O conteúdo principal
  reserva espaço (`FOOTER_SPACER` em `App.tsx`) para não ficar escondido
  atrás dele; ambos escondidos na impressão (`print:hidden`/`print:static`).
- **Roteamento por hash** (`router.ts`, `useRoute()`): só 2 telas —
  diagnóstico (`#/`) e notas metodológicas (`#/notas`, página dedicada, não
  mais uma seção na rolagem). Mesmo padrão (`hashchange`) do
  `climate-injustice-index/dashboard/src/router.ts`, sem lib de rotas — não
  adicionar `react-router` aqui, o app não precisa disso.
- `ImageZoom.tsx`: miniatura clicável → modal com a imagem ampliada e um
  link de download do PNG original. Usado em `MapCard.tsx` e
  `SinteseSection.tsx`.
- `DownloadData.tsx`: expõe o GeoPackage final para download direto pelo
  site. `build_web_assets.py` copia o `.gpkg` (não move) para dentro de
  `REPORT_DIR`/`public/data/` e grava `gpkg_arquivo`/`gpkg_tamanho_mb` no
  `report.json` — o entregável principal continua sendo o `.gpkg` do
  `DATA_DIR`; o site só espelha uma cópia para quem só tem o link do site.
- Tokens de cor do Tailwind (`tailwind.config.js`) são importados direto de
  `@wri-brasil/design-system` (`colors`), não redigitados — evita a
  divergência silenciosa que existe no dashboard do `climate-injustice-index`
  (mesmos valores copiados à mão em 3 lugares diferentes).

## Ambiente Python

`venv/` na raiz do repo (não versionado). Dependências em `requirements.txt`:
osmnx/overpy (OSM), geopandas/shapely/pandas/pyarrow (base), overturemaps/duckdb
(edificações), h3 (malha), rasterio/rasterstats (zonal stats), openpyxl (dicionários),
matplotlib/mapclassify (mapas PNG do `dashboard/data_prep/`).

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
  espacial** (point-in-polygon), nunca por código. Ver cabeçalho do `06_cnefe.py`.
- **Interpolação dasimétrica: intensiva ≠ extensiva.** A fórmula do
  climate-injustice-index (`Valor × domicílios/total_setor`) é para *contagens*
  (extensivas). Renda e percentuais são *médias/taxas* (intensivas) e precisam
  de **média ponderada por domicílios dentro do hexágono**. Trocar uma pela
  outra subestima o valor silenciosamente (renda saiu ~536 em vez de ~2.290 na
  1ª versão). Ver cabeçalho do `07_h3_dasimetrico.py`.
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

## Pegadinhas do `dashboard/` (npm / design system)

- **npm 12+ desabilita dependências git por padrão** (`allow-git = "none"` é
  o default de fábrica — hardening contra supply-chain attacks, não é algo
  configurado por alguém). Isso quebra a instalação documentada do
  `@wri-brasil/design-system` (`github:carolinafaccin/wri-brasil-design-system`
  no `package.json`) com `EALLOWGIT: Fetching packages of type "git" have
  been disabled`. Corrigido escopando a liberação só a este projeto via
  `dashboard/.npmrc` (`allow-git=root`) — não mexer na config global do npm.
  Provavelmente afeta qualquer máquina com npm recente (inclusive Windows).
- O `prepare` do design system (`npm run build`, que gera o `dist/` que a
  gente importa) roda mesmo com o aviso `npm warn install-scripts ...
  blocked` — esse aviso é sobre outros scripts (postinstall do `esbuild`,
  `fsevents`), não sobre o `prepare` de dependências git. Confirmar que
  `node_modules/@wri-brasil/design-system/dist/` existe e tem conteúdo real
  (não vazio) após `npm install`, se desconfiar.
- `github:owner/repo` sem `#commit-ish` trava no commit do momento do
  `npm install` (fica congelado no `package-lock.json`) — atualizações do
  design system não chegam sozinhas em builds futuros. Rodar
  `npm update @wri-brasil/design-system` de propósito quando quiser a
  versão mais nova.

## Estado atual

- **Pipeline completo (01–14 + gee_*) escrito e rodando** no projeto de exemplo.
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
  `11` usa — tratado com segurança: `raio_ancora()` pula a camada quando a
  âncora está fora do bbox, e essa camada não aparece no site) ficam na lista
  de tarefas em `projetos/<cidade>/ref/` (fora do git).
- Educação: o `04` já extrai ensino/saúde do CNEFE geocodificados — pode
  dispensar uma fonte INEP separada.
- **Dados municipais (prefeitura) integrados** via `04_dados_municipais.py` e
  `09_indicadores_municipais.py`, com fallback para nacional/global
  (framework de 3 categorias acima). Campinas tem 49 camadas catalogadas em
  `CAMADAS_MUNICIPAIS` (raw_dir/prefeituras_municipais/campinas/). Ainda não
  rodado ponta a ponta contra o GeoPackage de produção — próximo passo antes
  de reexportar o `.gpkg`/dashboard oficial.
- **Site migrado de `scripts/report/` (Jinja2/matplotlib, aposentado) para
  `dashboard/`** (React/Vite/TS/Tailwind, mesmo padrão do
  `climate-injustice-index`). Publicado em
  `https://bassoli.diagnostico-urbanistico.pages.dev` (Cloudflare Pages +
  Access). Mapas continuam estáticos (PNG via matplotlib) — decisão
  deliberada, não interatividade por enquanto (293 hexágonos, área pequena).
  Falta preencher `analise_area.md` (análise descritiva da área) por projeto
  — a seção correspondente do site fica oculta até lá.
  