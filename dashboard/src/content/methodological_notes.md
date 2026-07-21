## Como o score de prioridade é calculado

O **score de prioridade** de cada hexágono (malha H3) é uma média ponderada de
indicadores normalizados, calculada pelo script `11_analises.py`:

- **Temperatura de superfície** (LST)
- **Déficit de cobertura vegetal** (inverso da fração de vegetação)
- **Impermeabilização** (% do hexágono ocupado por edificações)
- **Vulnerabilidade social** (renda média, normalizada)
- **Déficit de arborização** (% de domicílios em face sem arborização)

Os pesos de cada indicador são configuráveis por projeto (não são fixos entre
cidades diferentes).

### Normalização e classificação

Cada indicador é normalizado por **min-max dentro da própria área analisada**
(o menor valor observado vira 0, o maior vira 1). Hexágonos sem algum
indicador (por exemplo, sem domicílios, como um córrego ou área verde) têm os
pesos dos indicadores ausentes redistribuídos automaticamente entre os
indicadores presentes — o score não é penalizado nem vira nulo por causa de
dados ausentes.

O score final é classificado em 4 faixas fixas — **baixa, média, alta, muito
alta** — usando os mesmos cortes absolutos (0,25 / 0,50 / 0,75) em qualquer
projeto, o que torna a classificação comparável entre diferentes execuções da
mesma área ao longo do tempo.

### Limitação importante

Como a normalização é **local à área analisada**, o score bruto — e portanto
a distribuição em faixas — **não é diretamente comparável entre projetos
diferentes** (bairros, municípios) sem recalibração. Um hexágono "muito alta
prioridade" em um projeto pequeno reflete o que é mais crítico *dentro
daquele recorte*, não necessariamente um valor absoluto comparável a outro
território.
