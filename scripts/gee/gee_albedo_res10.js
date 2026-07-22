// ============================================================================
// gee_albedo_res10.js — albedo médio (potencial de cool roof) por hexágono
// H3 res10
// ----------------------------------------------------------------------------
// Produto NOVO (não existe no catálogo res9 — não é réplica do
// climate-injustice-index). Superfícies de baixo albedo absorvem mais
// radiação solar e contribuem mais para a ilha de calor — hexágonos com
// albedo baixo E alta fração construída (pct_construido, já calculado no
// pipeline via Overture) são candidatos a intervenção de cool roof, mesmo
// fora de cidades com Cool Cities Lab (hoje só o CCL calcula albedo, via
// 10_cool_cities.py — este é o fallback GEE equivalente).
//
// Método: albedo de banda larga por conversão narrowband→broadband (Liang,
//   2001), usando as bandas do Sentinel-2 equivalentes às do Landsat ETM+
//   originais do método (azul/vermelho/NIR/SWIR1/SWIR2 → B2/B4/B8/B11/B12).
//   APROXIMAÇÃO: os coeficientes de Liang foram calibrados para Landsat, não
//   Sentinel-2 — suficiente como proxy relativo (comparar hexágonos entre
//   si), não como medida absoluta de albedo. Composto de mediana de imagens
//   com pouca nuvem no período, para reduzir ruído de nuvem/sombra pontual.
//
// Como usar: mesmo fluxo dos demais gee_*_res10.js.
// ============================================================================

// --- 1. CONFIGURAÇÃO ---
var GEE_PROJECT = 'famous-sandbox-487316-c9';

var PERIODO_INI = '2023-01-01';
var PERIODO_FIM = '2025-01-01';
var NUVEM_MAX_PCT = 20;

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

// --- 2. Albedo (Sentinel-2 SR harmonized) ---
function maskNuvem(image) {
  var scl = image.select('SCL');
  // exclui sombra de nuvem (3), nuvem média/alta prob. (8,9) e cirrus (10)
  var mask = scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10));
  return image.updateMask(mask);
}

function toAlbedo(image) {
  var img = maskNuvem(image).multiply(0.0001); // reflectância 0-1
  var albedo = img.expression(
    '0.356*B2 + 0.130*B4 + 0.373*B8 + 0.085*B11 + 0.072*B12 - 0.0018', {
      B2: img.select('B2'), B4: img.select('B4'), B8: img.select('B8'),
      B11: img.select('B11'), B12: img.select('B12')
    }).rename('gee_albedo');
  return albedo.copyProperties(image, ['system:time_start']);
}

var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterDate(PERIODO_INI, PERIODO_FIM)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', NUVEM_MAX_PCT));

var albedo_medio = s2.map(toAlbedo).median();

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

    var amostra = albedo_medio.reduceRegions({
      collection: buffered,
      reducer: ee.Reducer.mean(),
      scale: 20,
      tileScale: 16
    });

    Export.table.toDrive({
      collection: amostra,
      description: 'gee_br_h3_res10_albedo_uf_' + uf + '_lote' + i,
      folder: 'gee_br_h3_res10_albedo',
      fileFormat: 'CSV',
      selectors: ['h3_id', 'cd_setor', 'cd_uf', 'qtd_dom', 'gee_albedo']
    });
  }
});

print('Tarefas enviadas: albedo médio (0-1, proxy de potencial de cool roof) por hexágono H3 res10.');
