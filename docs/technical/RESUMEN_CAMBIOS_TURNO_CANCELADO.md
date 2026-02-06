# Resumen de Cambios: Migración asistencia → turno_cancelado

## ✅ Cambios Completados

### **1. Base de Datos (Supabase)**

Ejecutar script: [`migrate_asistencia_to_turno_cancelado.sql`](file:///home/pablo/gestion-rrhh-centro/admin_tools/migrate_asistencia_to_turno_cancelado.sql)

**Cambios:**
- ✅ Recreada `vista_saldo_horas_live` para usar `estado = 'cumplida'` en lugar de `asistencia = true`
- ✅ Agregada columna `turno_cancelado BOOLEAN DEFAULT FALSE` en tabla `convocatoria`
- ✅ Eliminada columna `asistencia`
- ✅ Vista actualizada para excluir turnos cancelados del cálculo de saldos

---

### **2. Scripts Google Apps Script**

#### **Archivos actualizados:**

1. **`download_data.gs`** ✅
   - Cambio en `downloadConvocatoria()`:
     - Fetch: `'...turno_cancelado'` (antes `'...asistencia'`)
     - Header: `'turno_cancelado'` (antes `'asistencia'`)
     - Mapeado: `c.turno_cancelado ? 'Sí' : 'No'`
     - Formato condicional: **rojo** para turnos cancelados (antes verde para asistencia)

2. **`config.gs`** ✅
   - Agregado a `convocatoria.types`:
     ```javascript
     turno_cancelado: 'bool'  // NUEVO
     ```

3. **`sync_turnos.gs`** ✅ (corregido anteriormente)
   - Nombres de columna: `cant_horas`, `hora_inicio`, `hora_fin`

---

## 📋 Checklist de Despliegue

### **Orden de ejecución:**

- [ ] 1. **Ejecutar SQL** en Supabase:
  ```bash
  # Archivo: admin_tools/migrate_asistencia_to_turno_cancelado.sql
  # Copiar contenido → SQL Editor → Ejecutar todo
  ```

- [ ] 2. **Actualizar scripts GAS**:
  - [ ] `download_data.gs` → copiar versión actualizada
  - [ ] `config.gs` → copiar versión actualizada
  - [ ] `sync_turnos.gs` → copiar versión actualizada (si no lo hiciste aún)

- [ ] 3. **Verificar en Google Sheets**:
  ```
  📥 Descargar Datos → 👥 Convocatoria
  ```
  - Columna debe llamarse `turno_cancelado` (no `asistencia`)
  - Valores: "Sí" o "No"
  - "Sí" debe aparecer con fondo rojo

- [ ] 4. **Verificar cálculo de saldos**:
  ```
  🧮 Cálculos Automáticos → Calcular Saldos Mensuales
  ```
  - Los turnos con `turno_cancelado = Sí` NO deben contar en las horas

---

## 🎯 Comportamiento Esperado

### **Antes (asistencia):**
- Todos los turnos tenían `asistencia = false`
- No se usaba para cálculos (se usaba `estado = 'cumplida'`)
- Color verde confuso (parecía positivo)

### **Ahora (turno_cancelado):**
- Todos comienzan con `turno_cancelado = No`
- Puedes marcar turnos individuales como cancelados
- Los cancelados **NO cuentan** para saldos
- Color rojo visual para cancelados

---

## 📊 Archivos Modificados

| Archivo | Cambios | Estado |
|---------|---------|--------|
| [`migrate_asistencia_to_turno_cancelado.sql`](file:///home/pablo/gestion-rrhh-centro/admin_tools/migrate_asistencia_to_turno_cancelado.sql) | Script completo de migración DB | ✅ Listo |
| [`download_data.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/download_data.gs) | downloadConvocatoria actualizado | ✅ Listo |
| [`config.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/config.gs) | Agregado turno_cancelado type | ✅ Listo |
| [`sync_turnos.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/sync_turnos.gs) | Columnas corregidas | ✅ Listo |

---

## ⚠️ Nota Importante

La vista `vista_saldo_horas_live` ahora excluye automáticamente turnos cancelados. **No necesitas cambiar ningún script Python** - la vista se encarga de todo.
