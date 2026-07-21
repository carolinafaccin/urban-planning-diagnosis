// ============================================================================
// gee_chuva_extrema_res10.js — intensidade de chuva extrema (curta duração)
// por hexágono H3 res10 (GPM IMERG)
// ----------------------------------------------------------------------------
// Produto NOVO (não existe no catálogo res9 — lá só há seca/SPI, que é o
// oposto: déficit de chuva de longo prazo). Complementa
// gee_inundacao_hand_jrc_res10.js: aquele é risco FLUVIAL (rio transborda,
// função de topografia); este é risco de ALAGAMENTO PLUVIAL URBANO (chuva
// forte e pontual sobre drenagem insuficiente) — ângulo de infraestrutura
// urbana, não de curso d'água. Os dois são indicadores DIFERENTES, não
// substitutos um do outro.
//
// Método: percentil alto (P99, configurável) da taxa de precipitação
//   meia-horária (mm/h) ao longo do período inteiro — proxy de intensidade
//   de chuva extrema, sem precisar agregar por dia manualmente (evita um
//   loop server-side de milhares de dias, que seria pesado demais para
//   rodar em 27 UFs). Não é "chuva acumulada num evento", é "quão intensa
//   fica a chuva nos poucos piores instantes do período" — proxy relativo
//   entre hexágonos, não uma curva IDF (intensidade-duração-frequência).
//   RESOLUÇÃO NATIVA do IMERG é ~10km — assim como a LST noturna (MODIS),
//   isso é sinal de CONTEXTO regional (não varia hexágono a hexágono dentro
//   do mesmo pixel de 10km); útil para comparar áreas do projeto entre si
//   só se elas caírem em pixels IMERG diferentes.
//
// Como usar: mesmo fluxo dos demais gee_*_res10.js.
// ============================================================================

// --- 1. CONFIGURAÇÃO ---
var GEE_PROJECT = 'famous-sandbox-487316-c9';

var PERIODO_INI = '2015-01-01';
var PERIODO_FIM = '2025-01-01';
var PERCENTIL_EXTREMO = 99;

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

// --- 2. Chuva extrema (percentil alto da taxa meia-horária, GPM IMERG) ---
var imerg = ee.ImageCollection('NASA/GPM_L3/IMERG_V07')
  .filterDate(PERIODO_INI, PERIODO_FIM)
  .select('precipitationCal'); // mm/h

var chuva_extrema = imerg.reduce(ee.Reducer.percentile([PERCENTIL_EXTREMO]))
  .rename('gee_chuva_extrema_p' + PERCENTIL_EXTREMO + '_mm_h');

// --- 3. AMOSTRAGEM POR UF ---
ufs.forEach(function (uf) {
  if (!ASSET_POR_UF[uf]) {
    print('[aviso] UF ' + uf + ' sem asset em ASSET_POR_UF — pulando.');
    return;
  }
  var buffered = ee.FeatureCollection(ASSET_POR_UF[uf])
    .map(function (f) { return f.buffer(H3_RES10_CIRCUMRADIUS_M); });

  var amostra = chuva_extrema.reduceRegions({
    collection: buffered,
    reducer: ee.Reducer.mean(),
    scale: 10000,
    tileScale: 16
  });

  Export.table.toDrive({
    collection: amostra,
    description: 'gee_br_h3_res10_chuva_extrema_uf_' + uf,
    folder: 'gee_br_h3_res10_chuva_extrema',
    fileFormat: 'CSV',
    selectors: ['h3_id', 'cd_setor', 'cd_uf', 'qtd_dom', 'gee_chuva_extrema_p' + PERCENTIL_EXTREMO + '_mm_h']
  });
});

print('Tarefas enviadas: P' + PERCENTIL_EXTREMO + ' da taxa de chuva (mm/h, proxy de chuva extrema) por hexágono H3 res10.');
