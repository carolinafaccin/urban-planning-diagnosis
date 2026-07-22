// ============================================================================
// gee_crescimento_urbano_res10.js — crescimento da mancha construída
// (2000→2020) por hexágono H3 res10 (GHSL)
// ----------------------------------------------------------------------------
// Produto NOVO (não existe no catálogo res9). Todos os outros indicadores do
// score (14_analises.py) olham o estado PRESENTE do território. Este é o
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

    // média de um booleano = fração da área do buffer que urbanizou 2000->2020
    var amostra = crescimento.reduceRegions({
      collection: buffered,
      reducer: ee.Reducer.mean(),
      scale: 100,
      tileScale: 16
    });

    Export.table.toDrive({
      collection: amostra,
      description: 'gee_br_h3_res10_crescimento_urbano_uf_' + uf + '_lote' + i,
      folder: 'gee_br_h3_res10_crescimento_urbano',
      fileFormat: 'CSV',
      selectors: ['h3_id', 'cd_setor', 'cd_uf', 'qtd_dom', 'gee_crescimento_construido']
    });
  }
});

print('Tarefas enviadas: fração de urbanização recente 2000->2020 (0-1) por hexágono H3 res10.');
