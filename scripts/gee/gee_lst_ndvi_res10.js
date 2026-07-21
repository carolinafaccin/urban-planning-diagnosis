// ============================================================================
// gee_lst_ndvi_res10.js — LST e NDVI médios por hexágono H3 res10
// ----------------------------------------------------------------------------
// Fallback do 07_cool_cities.py para cidades sem Cool Cities Lab, e base do
// catálogo nacional (raw_dir/gee/h3_res10/). Adaptado do e4 do
// climate-injustice-index (que fez o Brasil em res9).
//
// Método: o asset de centróides (um ponto por hexágono) é bufferizado pelo
//   circunraio do H3 res10 (~76 m) para aproximar a área do hexágono, e
//   reduceRegions(mean) amostra LST (Landsat) e NDVI dentro de cada buffer.
//   Exporta um CSV por UF.
//
// DIFERENÇA vs. res9: no res9 o circunraio é 174 m; no res10 é ~76 m. Só isso
//   muda no buffer — o resto do fluxo é o mesmo.
//
// Piloto (só o projeto) vs. catálogo nacional (Brasil inteiro)
// --------------------------------------------------------------
// - Piloto: rode gee_centroides_res10.py (malha só do projeto), suba UM
//   asset, e aponte ASSET_POR_UF['<sua_uf>'] pra ele.
// - Nacional: rode gee_centroides_res10_nacional.py (gera 1 CSV por UF em
//   raw_dir/gee/h3_res10/centroides/), suba CADA CSV como um asset separado
//   (mais tratável que um único asset gigante) e preencha ASSET_POR_UF
//   abaixo com o caminho de cada um. TESTE 1 UF PRIMEIRO — res10 nacional
//   tem ~7x mais células que res9 (~18M no Brasil); reduceRegions pode
//   estourar timeout/memória em estados grandes antes de rodar as 27 de
//   uma vez overnight.
//
// Como usar:
//   1. Gere os centróides (ver acima) e suba os CSVs como assets no GEE.
//   2. Preencha ASSET_POR_UF abaixo com o caminho de cada asset.
//   3. Ajuste PERIODO conforme o config.py do projeto (LST_PERIODO).
//   4. Rode no Code Editor e confirme as tarefas de Export (uma por UF).
//   5. Baixe os CSVs e rode gee_ingest_res10.py para gerar h3_gee.parquet.
// ============================================================================

// --- 1. CONFIGURAÇÃO ---
// Projeto GEE onde os assets de centróides (gee_centroides_res10_nacional.py)
// foram subidos — nome do asset segue br_h3_res10_centroides_uf_<NN>.
var GEE_PROJECT = 'famous-sandbox-487316-c9';

var PERIODO_INI = '2020-01-01';   // = LST_PERIODO[0] no config.py
var PERIODO_FIM = '2025-01-01';   // = LST_PERIODO[1] no config.py

// Circunraio do hexágono H3 res10 (centro → vértice), em metros.
var H3_RES10_CIRCUMRADIUS_M = 76;

// UFs a exportar (para o piloto, deixe só a do projeto; para o Brasil, todas).
var ufs = [
  11, 12, 13, 14, 15, 16, 17, // Norte: RO, AC, AM, RR, PA, AP, TO
  21, 22, 23, 24, 25, 26, 27, 28, 29, // Nordeste: MA, PI, CE, RN, PB, PE, AL, SE, BA
  31, 32, 33, 35, // Sudeste: MG, ES, RJ, SP
  41, 42, 43, // Sul: PR, SC, RS
  50, 51, 52, 53 // Centro-Oeste: MS, MT, GO, DF
];

// Mapa uf → asset de centróides res10 dessa UF (um FeatureCollection cada).
var ASSET_POR_UF = {};
ufs.forEach(function (uf) {
  ASSET_POR_UF[uf] = 'projects/' + GEE_PROJECT + '/assets/br_h3_res10_centroides_uf_' + uf;
});

// --- 2. LST (Landsat 8/9, banda térmica) e NDVI ---
function maskL89(image) {
  var qa = image.select('QA_PIXEL');
  return qa.bitwiseAnd(1 << 3).eq(0).and(qa.bitwiseAnd(1 << 4).eq(0));
}

function toLST(image) {  // ST_B10 → °C
  return image.select('ST_B10').updateMask(maskL89(image))
    .multiply(0.00341802).add(149.0).subtract(273.15)
    .rename('LST').copyProperties(image, ['system:time_start']);
}

function toNDVI(image) {  // (NIR - RED) / (NIR + RED), Landsat SR
  var sr = image.updateMask(maskL89(image))
    .select(['SR_B5', 'SR_B4']).multiply(0.0000275).add(-0.2);
  return sr.normalizedDifference(['SR_B5', 'SR_B4'])
    .rename('NDVI').copyProperties(image, ['system:time_start']);
}

var l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2').filterDate(PERIODO_INI, PERIODO_FIM);
var l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2').filterDate(PERIODO_INI, PERIODO_FIM);
var col = l8.merge(l9);

var lst_medio  = col.map(toLST).mean().rename('gee_lst');
var ndvi_medio = col.map(toNDVI).mean().multiply(100).rename('gee_ndvi_pct'); // % p/ casar com frac_veg

var indicadores = lst_medio.addBands(ndvi_medio);

// --- 3. AMOSTRAGEM POR UF ---
ufs.forEach(function (uf) {
  if (!ASSET_POR_UF[uf]) {
    print('[aviso] UF ' + uf + ' sem asset em ASSET_POR_UF — pulando.');
    return;
  }
  var buffered = ee.FeatureCollection(ASSET_POR_UF[uf])
    .map(function (f) { return f.buffer(H3_RES10_CIRCUMRADIUS_M); });

  var amostra = indicadores.reduceRegions({
    collection: buffered,
    reducer: ee.Reducer.mean(),
    scale: 30,
    tileScale: 16
  });

  Export.table.toDrive({
    collection: amostra,
    description: 'gee_br_h3_res10_lst_ndvi_uf_' + uf,
    folder: 'gee_br_h3_res10_lst_ndvi',
    fileFormat: 'CSV',
    selectors: ['h3_id', 'cd_setor', 'cd_uf', 'qtd_dom', 'gee_lst', 'gee_ndvi_pct']
  });
});

print('Tarefas enviadas: LST (°C) e NDVI (%) médios por hexágono H3 res10.');
