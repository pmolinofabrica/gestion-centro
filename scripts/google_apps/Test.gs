/**
 * TEST UTILS - Diagnóstico de conexión
 */

/**
 * Test completo de acceso a Supabase con diagnóstico detallado
 */
function testSupabaseAccess() {
  Logger.log('=== INICIANDO TEST DE ACCESO ===');
  
  const config = getSupabaseConfig_();
  const ui = SpreadsheetApp.getUi();
  
  // 1. Verificar credenciales
  if (!config.url || !config.key) {
    const msg = '❌ CREDENCIALES FALTANTES\n\nURL: ' + (config.url ? 'OK' : 'FALTA') + '\nKEY: ' + (config.key ? 'OK' : 'FALTA');
    Logger.log(msg);
    ui.alert(msg);
    return;
  }
  
  Logger.log('✅ Credenciales configuradas');
  Logger.log('URL: ' + config.url);
  
  // 2. Test de conexión básica a 'dias' (tabla pequeña)
  Logger.log('\n--- TEST 1: Tabla dias ---');
  try {
    const diasData = fetchAll('dias', 'id_dia,fecha');
    Logger.log('✅ Días: ' + diasData.length + ' registros');
  } catch (e) {
    Logger.log('❌ Error en dias: ' + e.message);
    ui.alert('❌ Error al leer tabla dias:\n' + e.message);
    return;
  }
  
  // 3. Test de conexión a 'planificacion'
  Logger.log('\n--- TEST 2: Tabla planificacion ---');
  try {
    const planiData = fetchAll('planificacion', 'id_plani,id_dia,id_turno');
    Logger.log('✅ Planificación: ' + planiData.length + ' registros');
    
    if (planiData.length === 0) {
      const msg = '⚠️ TABLA VACÍA\n\nLa tabla planificacion existe pero está vacía.\n\nVerifica:\n1. Grants en Supabase\n2. RLS (Row Level Security)\n3. Que realmente haya datos cargados';
      Logger.log(msg);
      ui.alert(msg);
    } else {
      // Mostrar muestra
      Logger.log('Primer registro: ' + JSON.stringify(planiData[0]));
      ui.alert('✅ CONEXIÓN OK\n\nPlanificación: ' + planiData.length + ' registros encontrados');
    }
  } catch (e) {
    const msg = '❌ ERROR AL LEER PLANIFICACION\n\n' + e.message + '\n\nPosibles causas:\n1. RLS activo sin política para service_role\n2. Grant faltante\n3. Tabla no existe';
    Logger.log(msg);
    Logger.log('Stack: ' + e.stack);
    ui.alert(msg);
    return;
  }
  
  // 4. Test de permisos de escritura
  Logger.log('\n--- TEST 3: Permisos ---');
  Logger.log('Service key length: ' + config.key.length);
  Logger.log('✅ Test completado. Revisa Logs para detalles.');
}

/**
 * Test rápido de conteo
 */
function testPlanificacionCount() {
  const config = getSupabaseConfig_();
  const url = config.url + '/rest/v1/planificacion?select=count';
  
  const options = {
    method: 'GET',
    headers: buildHeaders_(config.key),
    muteHttpExceptions: true
  };
  
  const response = UrlFetchApp.fetch(url, options);
  const code = response.getResponseCode();
  const body = response.getContentText();
  
  Logger.log('Status: ' + code);
  Logger.log('Body: ' + body);
  Logger.log('Headers: ' + JSON.stringify(response.getHeaders()));
  
  SpreadsheetApp.getUi().alert('Status: ' + code + '\n\nBody: ' + body);
}
