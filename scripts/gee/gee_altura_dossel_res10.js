// ============================================================================
// gee_altura_dossel_res10.js — altura média de dossel arbóreo por hexágono
// H3 res10 (ETH Global Canopy Height)
// ----------------------------------------------------------------------------
// Produto NOVO (não existe no catálogo res9). NDVI (gee_lst_ndvi_res10.js)
// não distingue grama/gramado de árvore — os dois dão NDVI alto. Só a
// árvore com dossel alto dá SOMBRA de verdade (reduz LST na rua). Este
// produto refina 'deficit_verde'/'deficit_arb' (INDICADORES em
// 14_analises.py) separando arborização real de área verde genérica —
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

// Contagem real de células por UF (gee_centroides_res10_nacional.py, rodado
// em 2026-07-22) — usada em vez de `.size().getInfo()` dentro do loop, que é
// uma chamada SÍNCRONA: pra UFs grandes (MG tem 4,68M células) ela pode
// travar a aba inteira do Code Editor esperando o servidor responder.
var TOTAL_POR_UF = {
  11: 683529, 12: 302841, 13: 590800, 14: 162974, 15: 1873669, 16: 83097,
  17: 617855, 21: 1204427, 22: 980833, 23: 1267994, 24: 396795, 25: 702590,
  26: 1236109, 27: 378441, 28: 290192, 29: 3405997, 31: 4685163, 32: 684201,
  33: 652393, 35: 2541644, 41: 2022412, 42: 1418865, 43: 2557240, 50: 611583,
  51: 1079155, 52: 1449490, 53: 101682
};

// --- 2. Altura de dossel ---
var altura = ee.Image('users/nlang/ETH_GlobalCanopyHeight_2020_10m_v1').rename('gee_altura_dossel_m');
var cobertura_arvore = altura.gte(ALTURA_MIN_ARVORE_M).rename('gee_frac_dossel_alto');

var indicadores = altura.addBands(cobertura_arvore);

// --- 3. AMOSTRAGEM POR UF (em lotes, ver CHUNK_SIZE acima) ---
// UFs com mais de ~1,5M de células estouram "Computed value is too large" no
// reduceRegions num único lote (MG, SP, PA, BA, PR, RS observados na prática)
// — por isso todo UF é processado em lotes de CHUNK_SIZE via toList(count,
// offset), não só os grandes.
// 700000 gerava "Computed value is too large" na conta antiga; numa conta
// com cota de memória menor (ex.: ee2-linafaccin), 700000 já deu "out of
// memory" (Error code: 8). Reduzido pra dar mais folga por lote — se ainda
// estourar, diminua mais.
var CHUNK_SIZE = 150000;

ufs.forEach(function (uf) {
  if (!ASSET_POR_UF[uf]) {
    print('[aviso] UF ' + uf + ' sem asset em ASSET_POR_UF — pulando.');
    return;
  }
  var pts = ee.FeatureCollection(ASSET_POR_UF[uf]);
  var total = TOTAL_POR_UF[uf];
  var nLotes = Math.max(1, Math.ceil(total / CHUNK_SIZE));

  for (var i = 0; i < nLotes; i++) {
    var lote = ee.FeatureCollection(pts.toList(CHUNK_SIZE, i * CHUNK_SIZE));
    var buffered = lote.map(function (f) { return f.buffer(H3_RES10_CIRCUMRADIUS_M); });

    // altura: média (m); frac_dossel_alto: fração da área do buffer acima do limiar (0-1)
    var amostra = indicadores.reduceRegions({
      collection: buffered,
      reducer: ee.Reducer.mean(),
      scale: 10,
      tileScale: 16
    });

    Export.table.toDrive({
      collection: amostra,
      description: 'gee_br_h3_res10_altura_dossel_uf_' + uf + '_lote' + i,
      folder: 'gee_br_h3_res10_altura_dossel',
      fileFormat: 'CSV',
      selectors: ['h3_id', 'cd_setor', 'cd_uf', 'qtd_dom', 'gee_altura_dossel_m', 'gee_frac_dossel_alto']
    });
  }
});

print('Tarefas enviadas: altura média de dossel (m) e fração com dossel alto por hexágono H3 res10.');
