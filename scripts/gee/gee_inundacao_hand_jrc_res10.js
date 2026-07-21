// ============================================================================
// gee_inundacao_hand_jrc_res10.js — suscetibilidade a inundação fluvial por
// hexágono H3 res10 (HAND + JRC Global Surface Water)
// ----------------------------------------------------------------------------
// Espelha suscetibilidade-inundacoes-hand-jrc-v2/ do catálogo nacional res9
// (raw_dir/gee/h3_res9/), em res10. Ângulo de risco HÍDRICO/FLUVIAL — para
// alagamento pluvial urbano (chuva forte + drenagem), ver
// gee_chuva_extrema_res10.js (produto diferente e complementar).
//
// Método (score 0–1, MAIOR = mais suscetível):
//   HAND (Height Above Nearest Drainage, MERIT Hydro) — quanto mais baixo em
//     relação à drenagem mais próxima, maior o risco. Normalizado como
//     1 - min(HAND, HAND_MAX) / HAND_MAX (satura em HAND_MAX metros).
//   JRC Global Surface Water, banda 'occurrence' — % do tempo (1984–2021)
//     em que o pixel esteve coberto por água (0–100), normalizado /100.
//   flood_score = média simples dos dois componentes normalizados.
// ATENÇÃO: essa fórmula é uma composição razoável, não uma réplica
//   garantida do método exato usado no res9 (o README do catálogo não
//   documenta a fórmula, só o schema de saída). Ajuste HAND_MAX_M e o peso
//   entre os dois componentes se quiser recalibrar.
//
// Como usar: mesmo fluxo dos demais gee_*_res10.js.
// ============================================================================

// --- 1. CONFIGURAÇÃO ---
var GEE_PROJECT = 'famous-sandbox-487316-c9';

var HAND_MAX_M = 15; // acima disso, risco fluvial considerado ~nulo

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

// --- 2. HAND + JRC ---
var hand = ee.Image('MERIT/Hydro/v1_0_1').select('hnd');
var hand_norm = ee.Image(1).subtract(hand.min(HAND_MAX_M).divide(HAND_MAX_M)).rename('hand_norm');

var jrc_occurrence = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence');
var jrc_norm = jrc_occurrence.unmask(0).divide(100).rename('jrc_norm');

var flood_score = hand_norm.add(jrc_norm).divide(2).rename('flood_score');

// --- 3. AMOSTRAGEM POR UF ---
ufs.forEach(function (uf) {
  if (!ASSET_POR_UF[uf]) {
    print('[aviso] UF ' + uf + ' sem asset em ASSET_POR_UF — pulando.');
    return;
  }
  var buffered = ee.FeatureCollection(ASSET_POR_UF[uf])
    .map(function (f) { return f.buffer(H3_RES10_CIRCUMRADIUS_M); });

  var amostra = flood_score.reduceRegions({
    collection: buffered,
    reducer: ee.Reducer.mean(),
    scale: 30,
    tileScale: 16
  });

  Export.table.toDrive({
    collection: amostra,
    description: 'gee_br_h3_res10_inundacao_hand_jrc_uf_' + uf,
    folder: 'gee_br_h3_res10_inundacao_hand_jrc',
    fileFormat: 'CSV',
    selectors: ['h3_id', 'cd_setor', 'cd_uf', 'qtd_dom', 'flood_score']
  });
});

print('Tarefas enviadas: suscetibilidade a inundação fluvial (HAND+JRC, 0-1) por hexágono H3 res10.');
