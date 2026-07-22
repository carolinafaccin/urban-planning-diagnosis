// ============================================================================
// gee_anomalia_calor_res10.js — anomalia de LST (histórico vs. recente) por
// hexágono H3 res10
// ----------------------------------------------------------------------------
// Complementa gee_lst_ndvi_res10.js (LST médio absoluto) com uma leitura de
// TENDÊNCIA: quanto cada hexágono aqueceu em relação à própria média
// histórica. Espelha anomalia_calor_1985-2025/ do catálogo nacional res9
// (raw_dir/gee/h3_res9/), mas em res10.
//
// Método: média de LST no período HISTÓRICO (Landsat 5+7, 1985–2015) menos
//   média de LST no período RECENTE (Landsat 8+9, PERIODO_INI–PERIODO_FIM);
//   positivo = a célula está mais quente hoje que na média histórica.
//   Landsat 5/7 (Collection 2 L2) usam banda térmica ST_B6; Landsat 8/9
//   usam ST_B10 — mesmo fator de escala (0.00341802, offset 149.0) nas duas.
//
// Como usar: mesmo fluxo do gee_lst_ndvi_res10.js — preencha ASSET_POR_UF,
//   rode, baixe os CSVs (pasta GEE_anomalia_calor_res10) e rode
//   gee_ingest_res10.py apontando pra cá (ou um ingest equivalente).
// ============================================================================

// --- 1. CONFIGURAÇÃO ---
var GEE_PROJECT = 'famous-sandbox-487316-c9';

var HIST_INI = '1985-01-01';
var HIST_FIM = '2015-01-01';
var RECENTE_INI = '2020-01-01';  // = LST_PERIODO[0] no config.py
var RECENTE_FIM = '2025-01-01';  // = LST_PERIODO[1] no config.py

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

// --- 2. LST por geração de satélite (mesmo fator de escala em todas) ---
function maskQA(bit3, bit4) {
  return function (image) {
    var qa = image.select('QA_PIXEL');
    return qa.bitwiseAnd(1 << bit3).eq(0).and(qa.bitwiseAnd(1 << bit4).eq(0));
  };
}

function toLST(banda) {
  return function (image) {
    return image.select(banda).updateMask(maskQA(3, 4)(image))
      .multiply(0.00341802).add(149.0).subtract(273.15)
      .rename('LST').copyProperties(image, ['system:time_start']);
  };
}

var l5 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2').filterDate(HIST_INI, HIST_FIM);
var l7 = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2').filterDate(HIST_INI, HIST_FIM);
var l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2').filterDate(RECENTE_INI, RECENTE_FIM);
var l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2').filterDate(RECENTE_INI, RECENTE_FIM);

var lst_historico = l5.map(toLST('ST_B6')).merge(l7.map(toLST('ST_B6'))).mean();
var lst_recente   = l8.map(toLST('ST_B10')).merge(l9.map(toLST('ST_B10'))).mean();

var anomalia = lst_recente.subtract(lst_historico).rename('anomalia_temp');

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

    var amostra = anomalia.reduceRegions({
      collection: buffered,
      reducer: ee.Reducer.mean(),
      scale: 30,
      tileScale: 16
    });

    Export.table.toDrive({
      collection: amostra,
      description: 'gee_br_h3_res10_anomalia_calor_uf_' + uf + '_lote' + i,
      folder: 'gee_br_h3_res10_anomalia_calor',
      fileFormat: 'CSV',
      selectors: ['h3_id', 'cd_setor', 'cd_uf', 'qtd_dom', 'anomalia_temp']
    });
  }
});

print('Tarefas enviadas: anomalia de LST (°C, recente - histórico) por hexágono H3 res10.');
