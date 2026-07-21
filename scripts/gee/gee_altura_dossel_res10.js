// ============================================================================
// gee_altura_dossel_res10.js — altura média de dossel arbóreo por hexágono
// H3 res10 (ETH Global Canopy Height)
// ----------------------------------------------------------------------------
// Produto NOVO (não existe no catálogo res9). NDVI (gee_lst_ndvi_res10.js)
// não distingue grama/gramado de árvore — os dois dão NDVI alto. Só a
// árvore com dossel alto dá SOMBRA de verdade (reduz LST na rua). Este
// produto refina 'deficit_verde'/'deficit_arb' (INDICADORES em
// 11_analises.py) separando arborização real de área verde genérica —
// útil quando não há dado municipal de arborização (pct_sem_arb).
//
// Fonte: Lang et al. (2023) — ETH Global Sentinel-2 10m Canopy Height (2020),
//   asset comunitário (não é catálogo oficial do GEE, é upload de terceiro
//   — 'users/nlang/...'). Valor em metros, 0 = sem dossel.
//
// Como usar: mesmo fluxo dos demais gee_*_res10.js.
// ============================================================================

// --- 1. CONFIGURAÇÃO ---
var GEE_PROJECT = 'famous-sandbox-487316-c9';

var ALTURA_MIN_ARVORE_M = 3; // abaixo disso, considera-se "sem dossel arbóreo"

var H3_RES10_CIRCUMRADIUS_M = 76;
var ufs = [
  11, 12, 13, 14, 15, 16, 17,
  21, 22, 23, 24, 25, 26, 27, 28, 29,
  31, 32, 33, 35,
  41, 42, 43,
  50, 51, 52, 53
];

var ASSET_POR_UF = {};
ufs.forEach(function (uf) {
  ASSET_POR_UF[uf] = 'projects/' + GEE_PROJECT + '/assets/br_h3_res10_centroides_uf_' + uf;
});

// --- 2. Altura de dossel ---
var altura = ee.Image('users/nlang/ETH_GlobalCanopyHeight_2020_10m_v1').rename('gee_altura_dossel_m');
var cobertura_arvore = altura.gte(ALTURA_MIN_ARVORE_M).rename('gee_frac_dossel_alto');

var indicadores = altura.addBands(cobertura_arvore);

// --- 3. AMOSTRAGEM POR UF ---
ufs.forEach(function (uf) {
  if (!ASSET_POR_UF[uf]) {
    print('[aviso] UF ' + uf + ' sem asset em ASSET_POR_UF — pulando.');
    return;
  }
  var buffered = ee.FeatureCollection(ASSET_POR_UF[uf])
    .map(function (f) { return f.buffer(H3_RES10_CIRCUMRADIUS_M); });

  // altura: média (m); frac_dossel_alto: fração da área do buffer acima do limiar (0-1)
  var amostra = indicadores.reduceRegions({
    collection: buffered,
    reducer: ee.Reducer.mean(),
    scale: 10,
    tileScale: 16
  });

  Export.table.toDrive({
    collection: amostra,
    description: 'gee_br_h3_res10_altura_dossel_uf_' + uf,
    folder: 'gee_br_h3_res10_altura_dossel',
    fileFormat: 'CSV',
    selectors: ['h3_id', 'cd_setor', 'cd_uf', 'qtd_dom', 'gee_altura_dossel_m', 'gee_frac_dossel_alto']
  });
});

print('Tarefas enviadas: altura média de dossel (m) e fração com dossel alto por hexágono H3 res10.');
