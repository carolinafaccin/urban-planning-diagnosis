// ============================================================================
// gee_crescimento_urbano_res10.js — crescimento da mancha construída
// (2000→2020) por hexágono H3 res10 (GHSL)
// ----------------------------------------------------------------------------
// Produto NOVO (não existe no catálogo res9). Todos os outros indicadores do
// score (11_analises.py) olham o estado PRESENTE do território. Este é o
// único de caráter PROATIVO/PREVENTIVO: aponta hexágonos que urbanizaram
// recentemente e provavelmente ainda não tiveram tempo de consolidar
// infraestrutura verde/drenagem — candidatos a intervenção ANTES que o
// problema apareça, não depois.
//
// Método: GHS-BUILT-S (superfície construída, m² por célula de 100m) nas
//   épocas 2000 e 2020. gee_crescimento_construido = fração da célula que
//   ERA não-construída em 2000 e passou a ser construída em 2020 (0-1,
//   maior = urbanização mais recente/mais rápida no hexágono).
//
// Como usar: mesmo fluxo dos demais gee_*_res10.js.
// ============================================================================

// --- 1. CONFIGURAÇÃO ---
var GEE_PROJECT = 'famous-sandbox-487316-c9';

var LIMIAR_CONSTRUIDO_FRAC = 0.2; // fração da célula 100m considerada "construída"

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

// --- 2. GHSL built-up surface, 2000 vs 2020 ---
var ghsl = ee.ImageCollection('JRC/GHSL/P2023A/GHS_BUILT_S');
// célula nativa de 100m = 10.000 m²; built_surface em m² -> fração construída
var CELULA_M2 = 10000;

function fracConstruida(ano) {
  var img = ghsl.filter(ee.Filter.calendarRange(ano, ano, 'year')).first();
  return img.select('built_surface').divide(CELULA_M2).rename('frac_' + ano);
}

var frac_2000 = fracConstruida(2000);
var frac_2020 = fracConstruida(2020);

var era_nao_construido_2000 = frac_2000.lt(LIMIAR_CONSTRUIDO_FRAC);
var passou_a_construido_2020 = frac_2020.gte(LIMIAR_CONSTRUIDO_FRAC);
var crescimento = era_nao_construido_2000.and(passou_a_construido_2020)
  .rename('gee_crescimento_construido');

// --- 3. AMOSTRAGEM POR UF ---
ufs.forEach(function (uf) {
  if (!ASSET_POR_UF[uf]) {
    print('[aviso] UF ' + uf + ' sem asset em ASSET_POR_UF — pulando.');
    return;
  }
  var buffered = ee.FeatureCollection(ASSET_POR_UF[uf])
    .map(function (f) { return f.buffer(H3_RES10_CIRCUMRADIUS_M); });

  // média de um booleano = fração da área do buffer que urbanizou 2000->2020
  var amostra = crescimento.reduceRegions({
    collection: buffered,
    reducer: ee.Reducer.mean(),
    scale: 100,
    tileScale: 16
  });

  Export.table.toDrive({
    collection: amostra,
    description: 'gee_br_h3_res10_crescimento_urbano_uf_' + uf,
    folder: 'gee_br_h3_res10_crescimento_urbano',
    fileFormat: 'CSV',
    selectors: ['h3_id', 'cd_setor', 'cd_uf', 'qtd_dom', 'gee_crescimento_construido']
  });
});

print('Tarefas enviadas: fração de urbanização recente 2000->2020 (0-1) por hexágono H3 res10.');
