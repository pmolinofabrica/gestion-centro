# 🐛 Corrección de Bugs en Cálculo de Saldos

## Problemas Identificados

### **Bug #1: Nombre de columna incorrecto** ❌
**Línea 241 (anterior):**
```javascript
const turnos = fetchAll('turnos', 'id_turno,cant_horas_default');
```

**Problema:** La columna en Supabase se llama `cant_horas`, no `cant_horas_default`.

**Impacto:** Todas las horas se calculaban como `0` porque la columna no existía.

---

### **Bug #2: Fecha incorrecta para filtrado** ❌
**Líneas 229-236 (anterior):**
```javascript
const convocatorias = fetchAllWithFilters('convocatoria', 
  'id_agente,id_turno,fecha_convocatoria,estado', 
  {
    fecha_convocatoria_gte: fechaInicio,
    fecha_convocatoria_lt: fechaFin,
    estado: 'cumplida'
  }
);
```

**Problema:** `fecha_convocatoria` es la fecha de **registro** de la convocatoria, NO la fecha del turno real.

**Ejemplo del error:**
- Turno del 15 de Enero registrado el 10 de Diciembre → se contaba en Diciembre ❌
- Debería contarse en Enero ✅

**Impacto:** Los saldos se asignaban al mes incorrecto.

---

### **Bug #3: No excluye turnos cancelados** ❌
**Problema:** No se verificaba `turno_cancelado = true`.

**Impacto:** Si un residente fue convocado pero luego se canceló puntualmente, esas horas igual sumaban.

---

## Solución Implementada ✅

### **Nueva Lógica (5 pasos):**

1. **Obtener días del mes** → Filtra `dias` por rango de fechas
2. **Obtener planificación del mes** → Usa `id_dia` para filtrar turnos del mes real
3. **Obtener convocatorias** → Trae TODAS las convocatorias
4. **Filtrar convocatorias válidas:**
   - `id_plani` debe estar en la planificación del mes
   - `estado = 'cumplida'`
   - `turno_cancelado ≠ true`
5. **Acumular horas** → Usa `cant_horas` de la planificación (no de turnos)

### **Código Corregido:**
```javascript
// PASO 1: Días del mes
const diasDelMes = fetchAllWithFilters('dias', 'id_dia,fecha', {
  fecha_gte: fechaInicio,
  fecha_lt: fechaFin
});
const diasIds = new Set(diasDelMes.map(d => d.id_dia));

// PASO 2: Planificación del mes
const planificacion = fetchAll('planificacion', 'id_plani,id_dia,id_turno,cant_horas');
const planiDelMes = planificacion.filter(p => diasIds.has(p.id_dia));

// Mapa id_plani -> horas
const planiHoras = {};
planiDelMes.forEach(p => {
  planiHoras[p.id_plani] = p.cant_horas || 0;
});

// PASO 3: Convocatorias válidas
const convocatorias = fetchAll('convocatoria', 'id_plani,id_agente,estado,turno_cancelado');
const convValidas = convocatorias.filter(c => {
  return planiHoras.hasOwnProperty(c.id_plani) && 
         c.estado === 'cumplida' && 
         c.turno_cancelado !== true;
});

// PASO 4: Acumular
convValidas.forEach(conv => {
  const horas = planiHoras[conv.id_plani] || 0;
  horasPorAgente[conv.id_agente] += horas;
});
```

---

## Verificación

### **Antes de actualizar GAS:**
1. Descarga saldos actuales (si los tienes) para comparar
2. Anota cuántas horas tiene cada residente

### **Después de actualizar:**
1. Copia el nuevo `sync_saldos.gs` a tu proyecto GAS
2. Ejecuta: **🧮 Cálculos Automáticos → Calcular Saldos Mensuales**
3. Ingresa mes y año de prueba (ej: 1, 2025)
4. Verifica que:
   - Las horas sean > 0 (antes eran 0 por Bug #1)
   - Los turnos cancelados NO sumen
   - Los turnos estén en el mes correcto

---

## Archivo Actualizado

[`sync_saldos.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/sync_saldos.gs)
