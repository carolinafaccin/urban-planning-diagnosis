// ============================================================================
// gee_lst_noturna_res10.js — LST diurna e NOTURNA (MODIS) por hexágono H3 res10
// ----------------------------------------------------------------------------
// Produto NOVO (não existe no catálogo res9). O gee_lst_ndvi_res10.js (Landsat)
// só captura a passagem diurna (~10h local) — a ilha de calor NOTURNA (a
// cidade não esfria à noite) é o que mais associa a estresse térmico e
// mortalidade por calor em pessoas, e o Landsat diurno não enxerga isso.
// MODIS tem passagem diurna E noturna prontas no mesmo produto.
//
// Método: MOD11A2 (composto de 8 dias, 1km) — bandas LST_Day_1km e
//   LST_Night_1km, fator de escala 0.02 K, convertido para °C. Resolução
//   nativa (1km) é mais grossa que Landsat (30m) — dentro do buffer de
//   ~76m do hexágono res10 a amostra é essencialmente o pixel de 1km que
//   contém o hexágono (não uma média fina); ainda assim, útil como sinal
//   relativo entre hexágonos próximos do mesmo pixel MODIS carrega a mesma
//   leitura — é mais um dado de CONTEXTO regional (dia vs. noite) do que uma
//   variação fina intra-bairro. Ver `gee_lst_ndvi_res10` para a leitura diurna
//   fina que já existe.
//
// Como usar: mesmo fluxo dos demais gee_*_res10.js.
// ============================================================================

// --- 1. CONFIGURAÇÃO ---
var GEE_PROJECT = 'famous-sandbox-487316-c9';

var PERIODO_INI = '2020-01-01';  // = LST_PERIODO[0] no config.py
var PERIODO_FIM = '2025-01-01';  // = LST_PERIODO[1] no config.py

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

// --- 2. LST dia/noite (MODIS MOD11A2) ---
function toKelvinCelsius(banda, novoNome) {
  return function (image) {
    return image.select(banda).multiply(0.02).subtract(273.15)
      .rename(novoNome).copyProperties(image, ['system:time_start']);
  };
}

var mod11 = ee.ImageCollection('MODIS/061/MOD11A2').filterDate(PERIODO_INI, PERIODO_FIM);

var lst_dia   = mod11.map(toKelvinCelsius('LST_Day_1km', 'gee_lst_dia')).mean();
var lst_noite = mod11.map(toKelvinCelsius('LST_Night_1km', 'gee_lst_noite')).mean();

var indicadores = lst_dia.addBands(lst_noite);
var indicadores_ampl = indicadores.addBands(
  lst_dia.subtract(lst_noite).rename('gee_amplitude_termica')
);

// --- 3. AMOSTRAGEM POR UF ---
ufs.forEach(function (uf) {
  if (!ASSET_POR_UF[uf]) {
    print('[aviso] UF ' + uf + ' sem asset em ASSET_POR_UF — pulando.');
    return;
  }
  var buffered = ee.FeatureCollection(ASSET_POR_UF[uf])
    .map(function (f) { return f.buffer(H3_RES10_CIRCUMRADIUS_M); });

  var amostra = indicadores_ampl.reduceRegions({
    collection: buffered,
    reducer: ee.Reducer.mean(),
    scale: 1000,
    tileScale: 16
  });

  Export.table.toDrive({
    collection: amostra,
    description: 'gee_br_h3_res10_lst_noturna_uf_' + uf,
    folder: 'gee_br_h3_res10_lst_noturna',
    fileFormat: 'CSV',
    selectors: ['h3_id', 'cd_setor', 'cd_uf', 'qtd_dom', 'gee_lst_dia', 'gee_lst_noite', 'gee_amplitude_termica']
  });
});

print('Tarefas enviadas: LST dia/noite (°C, MODIS) e amplitude térmica por hexágono H3 res10.');
