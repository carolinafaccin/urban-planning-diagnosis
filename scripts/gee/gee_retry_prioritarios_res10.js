// ============================================================================
// gee_retry_prioritarios_res10.js — reprocessa SÓ as UFs que falharam nos 4
// produtos prioritários (lst_ndvi, inundacao_hand_jrc, crescimento_urbano,
// anomalia_calor), num único script, já com o chunking corrigido.
// ----------------------------------------------------------------------------
// UFs que falharam abaixo foram lidos dos prints que você mandou (Tasks do
// GEE). Se algum UF fora do que aparece nos screenshots também tiver
// falhado (ex.: rolou pra fora da tela), adicione o código na lista
// correspondente antes de rodar — não tem problema incluir um UF que já
// deu certo, o pior caso é reexportar de novo (arquivo extra pra ignorar).
//
// Como usar: cole este script inteiro no Code Editor e rode. Ele gera 4
// blocos de tarefas de export (um por produto), só para os UFs listados em
// cada FAILED_UFS_* abaixo.
// ============================================================================

// --- CONFIGURAÇÃO COMUM ---
var GEE_PROJECT = 'ee2-linafaccin';
var H3_RES10_CIRCUMRADIUS_M = 76;
var CHUNK_SIZE = 700000; // ver nota nos scripts individuais: acima disso, "Computed value is too large"

var ASSET_POR_UF = {};
[11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 25, 26, 27, 28, 29,
 31, 32, 33, 35, 41, 42, 43, 50, 51, 52, 53].forEach(function (uf) {
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

// Loop genérico: exporta 1 produto (imagem + seletor de colunas) só para os
// UFs de `ufsFalhos`, em lotes de CHUNK_SIZE.
function exportarProduto(imagem, ufsFalhos, nomeProduto, scale, selectors) {
  ufsFalhos.forEach(function (uf) {
    var pts = ee.FeatureCollection(ASSET_POR_UF[uf]);
    var total = TOTAL_POR_UF[uf];
    var nLotes = Math.max(1, Math.ceil(total / CHUNK_SIZE));

    for (var i = 0; i < nLotes; i++) {
      var lote = ee.FeatureCollection(pts.toList(CHUNK_SIZE, i * CHUNK_SIZE));
      var buffered = lote.map(function (f) { return f.buffer(H3_RES10_CIRCUMRADIUS_M); });

      var amostra = imagem.reduceRegions({
        collection: buffered,
        reducer: ee.Reducer.mean(),
        scale: scale,
        tileScale: 16
      });

      Export.table.toDrive({
        collection: amostra,
        description: 'gee_br_h3_res10_' + nomeProduto + '_uf_' + uf + '_lote' + i,
        folder: 'gee_br_h3_res10_' + nomeProduto,
        fileFormat: 'CSV',
        selectors: selectors
      });
    }
  });
  print('Tarefas enviadas: ' + nomeProduto + ' para UFs ' + ufsFalhos.join(', '));
}

// ============================================================================
// 1. LST + NDVI (gee_lst_ndvi_res10.js) — UFs que falharam
// ============================================================================
var FAILED_UFS_LST_NDVI = [43, 41, 35, 31, 29, 15];

var img_lst_ndvi = (function () {
  var PERIODO_INI = '2020-01-01';
  var PERIODO_FIM = '2025-01-01';

  function maskL89(image) {
    var qa = image.select('QA_PIXEL');
    return qa.bitwiseAnd(1 << 3).eq(0).and(qa.bitwiseAnd(1 << 4).eq(0));
  }
  function toLST(image) {
    return image.select('ST_B10').updateMask(maskL89(image))
      .multiply(0.00341802).add(149.0).subtract(273.15)
      .rename('LST').copyProperties(image, ['system:time_start']);
  }
  function toNDVI(image) {
    var sr = image.updateMask(maskL89(image))
      .select(['SR_B5', 'SR_B4']).multiply(0.0000275).add(-0.2);
    return sr.normalizedDifference(['SR_B5', 'SR_B4'])
      .rename('NDVI').copyProperties(image, ['system:time_start']);
  }

  var l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2').filterDate(PERIODO_INI, PERIODO_FIM);
  var l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2').filterDate(PERIODO_INI, PERIODO_FIM);
  var col = l8.merge(l9);

  var lst_medio = col.map(toLST).mean().rename('gee_lst');
  var ndvi_medio = col.map(toNDVI).mean().multiply(100).rename('gee_ndvi_pct');
  return lst_medio.addBands(ndvi_medio);
})();

exportarProduto(
  img_lst_ndvi, FAILED_UFS_LST_NDVI, 'lst_ndvi', 30,
  ['h3_id', 'cd_setor', 'cd_uf', 'qtd_dom', 'gee_lst', 'gee_ndvi_pct']
);

// ============================================================================
// 2. Suscetibilidade a inundação — HAND + JRC (gee_inundacao_hand_jrc_res10.js)
// ============================================================================
var FAILED_UFS_INUNDACAO = [31, 29];

var img_flood_score = (function () {
  var HAND_MAX_M = 15;
  var hand = ee.Image('MERIT/Hydro/v1_0_1').select('hnd');
  var hand_norm = ee.Image(1).subtract(hand.min(HAND_MAX_M).divide(HAND_MAX_M)).rename('hand_norm');

  var jrc_occurrence = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence');
  var jrc_norm = jrc_occurrence.unmask(0).divide(100).rename('jrc_norm');

  return hand_norm.add(jrc_norm).divide(2).rename('flood_score');
})();

exportarProduto(
  img_flood_score, FAILED_UFS_INUNDACAO, 'inundacao_hand_jrc', 30,
  ['h3_id', 'cd_setor', 'cd_uf', 'qtd_dom', 'flood_score']
);

// ============================================================================
// 3. Crescimento urbano — GHSL 2000→2020 (gee_crescimento_urbano_res10.js)
// ============================================================================
var FAILED_UFS_CRESCIMENTO = [31, 29];

var img_crescimento = (function () {
  var LIMIAR_CONSTRUIDO_FRAC = 0.2;
  var CELULA_M2 = 10000;
  var ghsl = ee.ImageCollection('JRC/GHSL/P2023A/GHS_BUILT_S');

  function fracConstruida(ano) {
    var img = ghsl.filter(ee.Filter.calendarRange(ano, ano, 'year')).first();
    return img.select('built_surface').divide(CELULA_M2).rename('frac_' + ano);
  }

  var frac_2000 = fracConstruida(2000);
  var frac_2020 = fracConstruida(2020);
  var era_nao_construido_2000 = frac_2000.lt(LIMIAR_CONSTRUIDO_FRAC);
  var passou_a_construido_2020 = frac_2020.gte(LIMIAR_CONSTRUIDO_FRAC);
  return era_nao_construido_2000.and(passou_a_construido_2020).rename('gee_crescimento_construido');
})();

exportarProduto(
  img_crescimento, FAILED_UFS_CRESCIMENTO, 'crescimento_urbano', 100,
  ['h3_id', 'cd_setor', 'cd_uf', 'qtd_dom', 'gee_crescimento_construido']
);

// ============================================================================
// 4. Anomalia de calor — histórico vs. recente (gee_anomalia_calor_res10.js)
// ============================================================================
var FAILED_UFS_ANOMALIA = [31, 29];

var img_anomalia_calor = (function () {
  var HIST_INI = '1985-01-01';
  var HIST_FIM = '2015-01-01';
  var RECENTE_INI = '2020-01-01';
  var RECENTE_FIM = '2025-01-01';

  function maskQA(bit3, bit4) {
    return function (image) {
      var qa = image.select('QA_PIXEL');
      return qa.bitwiseAnd(1 << bit3).eq(0).and(qa.bitwiseAnd(1 << bit4).eq(0));
    };
  }
  function toLSTGenerica(banda) {
    return function (image) {
      return image.select(banda).updateMask(maskQA(3, 4)(image))
        .multiply(0.00341802).add(149.0).subtract(273.15)
        .rename('LST').copyProperties(image, ['system:time_start']);
    };
  }

  var l5 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2').filterDate(HIST_INI, HIST_FIM);
  var l7 = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2').filterDate(HIST_INI, HIST_FIM);
  var l8_rec = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2').filterDate(RECENTE_INI, RECENTE_FIM);
  var l9_rec = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2').filterDate(RECENTE_INI, RECENTE_FIM);

  var lst_historico = l5.map(toLSTGenerica('ST_B6')).merge(l7.map(toLSTGenerica('ST_B6'))).mean();
  var lst_recente = l8_rec.map(toLSTGenerica('ST_B10')).merge(l9_rec.map(toLSTGenerica('ST_B10'))).mean();

  return lst_recente.subtract(lst_historico).rename('anomalia_temp');
})();

exportarProduto(
  img_anomalia_calor, FAILED_UFS_ANOMALIA, 'anomalia_calor', 30,
  ['h3_id', 'cd_setor', 'cd_uf', 'qtd_dom', 'anomalia_temp']
);
