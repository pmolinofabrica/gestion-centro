/**
 * DIAGNÓSTICO DE CONECTIVIDAD SUPABASE
 * Ejecuta esta función manualmente para ver qué responde exactamente Supabase
 */
function testConnectionDiagnostics() {
  const ui = SpreadsheetApp.getUi();
  const config = getSupabaseConfig_(); // Usa la función existente en db_helpers.gs
  
  if (!config.url || !config.key) {
    ui.alert('❌ Error: Configuración de URL/KEY vacía o no encontrada.');
    return;
  }

  // Debug URL
  Logger.log('URL Base: ' + config.url);

  // 1. Prueba Ping (Opcional, a la raíz)
  // 2. Prueba Tabla Calendario (1 fila)
  const urlCal = config.url + '/rest/v1/calendario_dispositivos?select=count&limit=1';
  
  const options = {
    method: 'GET',
    headers: {
      'apikey': config.key,
      'Authorization': 'Bearer ' + config.key
    },
    muteHttpExceptions: true
  };
  
  try {
    const response = UrlFetchApp.fetch(urlCal, options);
    const code = response.getResponseCode();
    const body = response.getContentText();
    
    Logger.log('Status: ' + code);
    Logger.log('Body: ' + body);
    
    let msg = `Status Code: ${code}\n`;
    
    if (code === 200) {
      msg += `✅ Conexión OK. Respuesta recibida.\nDatos: ${body.substring(0, 200)}...`;
    } else if (code === 401) {
      msg += `❌ 401 Unauthorized: Tu API KEY es inválida o expiró.`;
    } else if (code === 403) {
      msg += `🚫 403 Forbidden: Permisos insuficientes (RLS bloqueando o falta GRANT).`;
    } else if (code === 404) {
      msg += `❓ 404 Not Found: La tabla no existe o la URL está mal escrita.`;
    } else {
      msg += `⚠️ Error desconocido: ${body}`;
    }
    
    ui.alert('Diagnóstico Conectividad', msg, ui.ButtonSet.OK);
    
  } catch (e) {
    ui.alert('❌ Error de Red', e.message, ui.ButtonSet.OK);
  }
}
