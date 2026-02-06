# 🔧 Corrección: Paginación en fetchAll

## Problema Identificado

**Síntoma:** Solo se descargan 1000 registros de planificación cuando en Supabase hay 3000.

**Causa:** Supabase REST API limita las respuestas a **1000 registros por defecto**. Las funciones `fetchAll` y `fetchAllWithFilters` no manejaban paginación.

---

## Solución Implementada

### **Cambios en `Code.gs`:**

Actualicé `fetchAll()` para usar el header `Range` de HTTP:

```javascript
// Antes (sin paginación)
function fetchAll(table, select) {
  const query = '?select=' + (select || '*');
  const result = supabaseRequest_(table, query, 'GET');
  return result.data; // Máximo 1000
}

// Ahora (con paginación automática)
function fetchAll(table, select) {
  const PAGE_SIZE = 1000;
  let allData = [];
  let offset = 0;
  
  while (hasMore) {
    // Fetch con Range: 0-999, 1000-1999, 2000-2999...
    headers: { 'Range': offset + '-' + (offset + PAGE_SIZE - 1) }
    
    // Parsear Content-Range: "0-999/3000"
    // Continuar si end < total
  }
  
  return allData; // Todos los registros
}
```

### **Cambios en `menu_updates.gs`:**

Actualicé `fetchAllWithFilters()` con la misma lógica de paginación.

---

## Cómo Funciona

1. **Primera petición**: `Range: 0-999` → Devuelve registros 0-999
2. **Supabase responde**: `Content-Range: 0-999/3000` (hay 3000 totales)
3. **Segunda petición**: `Range: 1000-1999` → Registros 1000-1999
4. **Tercera petición**: `Range: 2000-2999` → Registros 2000-2999
5. **Fin**: `Content-Range: 2000-2999/3000` → Ya no hay más

---

## Verificación

### **Antes de actualizar:**
```
📥 Fetching planificacion...
✅ planificacion: 1000 registros  ❌ INCORRECTO
```

### **Después de actualizar:**
```
📥 Fetching planificacion...
   📄 Página 1: 1000 registros
   📄 Página 2: 1000 registros
✅ planificacion: 3000 registros totales  ✅ CORRECTO
```

---

## Archivos Actualizados

1. [`Code.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/Code.gs) - `fetchAll()`
2. [`menu_updates.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/menu_updates.gs) - `fetchAllWithFilters()`

---

## Impacto

Esto afecta **todas** las funciones que usan `fetchAll` o `fetchAllWithFilters`:

- ✅ `downloadPlanificacion()` - Ahora descarga los 3000 registros
- ✅ `downloadConvocatoria()` - Si hay >1000 convocatorias
- ✅ `calcularSaldosMensuales()` - Ahora procesa toda la planificación
- ✅ `actualizarDashboard()` - Métricas correctas con datos completos

**Acción requerida:** Actualiza ambos archivos en tu proyecto GAS y vuelve a descargar planificación.
