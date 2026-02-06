# Guía: Saldos - Gestión de Horas Mensuales

## 🎯 Funcionalidad

El módulo de **Saldos** permite:
1. **Registrar manualmente** horas mensuales por agente
2. **Calcular automáticamente** desde convocatorias cumplidas
3. **Sincronizar** con Supabase para liquidación/RRHH

---

## 📋 Estructura Tabla Saldos

| Campo | Tipo | Descripción | Obligatorio |
|-------|------|-------------|-------------|
| `id_agente` | int | ID del agente (o usar DNI) | ✅ |
| `mes` | int | Mes (1-12) | ✅ |
| `anio` | int | Año (2020-2030) | ✅ |
| `horas_mes` | float | Total horas trabajadas | ❌ (default: 0) |

**Unique Key**: (id_agente, mes, anio) — 1 registro por agente/mes

---

## 🚀 Uso

### Opción 1: Cálculo Automático (Recomendado)

**Menú**: 🧮 Cálculos Automáticos → Calcular Saldos Mensuales

1. Ingresar mes (ej: `1` para enero)
2. Ingresar año (ej: `2026`)
3. El script:
   - Lee todas las convocatorias con `estado='cumplida'`
   - Suma horas de cada turno por agente
   - Escribe directamente a Supabase

**Ejemplo de resultado**:
```
✅ Cálculo completado

Agentes procesados: 15
Total horas: 337.5 hs
Promedio por agente: 22.5 hs
```

---

### Opción 2: Registro Manual

**Menú**: 📥 Descargar Datos → Saldos (para ver existentes)

1. Crear/editar hoja `SALDOS`:

| id_agente | mes | anio | horas_mes | sync_status |
|-----------|-----|------|-----------|-------------|
| 123       | 1   | 2026 | 22.5      |             |
| 456       | 1   | 2026 | 18.0      |             |

2. **Menú**: 📤 Sincronizar a Supabase → Saldos

---

## ✅ Validaciones

| Validación | Mensaje Error |
|------------|---------------|
| ID agente existe | `❌ ID agente no existe` |
| DNI existe | `❌ DNI no encontrado` |
| Mes válido (1-12) | `❌ Mes inválido (1-12)` |
| Año válido | `❌ Año inválido` |
| Duplicado | *Actualiza automáticamente (UPSERT)* |

---

## 🔍 Filtrado con CONFIG

Si configuraste `año_activo = 2026` en CONFIG:
- **Descarga saldos**: Solo trae registros de 2026
- **Cálculo**: Procesa solo convocatorias de ese año

---

## 💡 Casos de Uso

### 1. Liquidación Mensual
```
1. Fin de mes → 🧮 Calcular Saldos Mensuales
2. Descargar: 📥 Saldos
3. Exportar hoja SALDOS a Excel/PDF
4. Enviar a RRHH/Contabilidad
```

### 2. Verificación de Horas
```
1. Agente reclama horas incorrectas
2. Ver su fila en SALDOS
3. Comparar con convocatorias individuales
4. Ajustar manualmente si necesario y re-sincronizar
```

### 3. Reporte Trimestral
```
1. Descargar saldos de enero, febrero, marzo
2. Sumar horas_mes en Excel
3. Análisis de tendencias
```

---

## 📊 Fórmula del Cálculo

```javascript
horas_mes = SUM(
  cant_horas_default de cada turno
  WHERE
    convocatoria.estado = 'cumplida'
    AND fecha_convocatoria BETWEEN inicio_mes AND fin_mes
)
```

**Importante**: Solo cuenta convocatorias con `estado='cumplida'`. Si el agente faltó (estado='con_inasistencia'), no suma horas.

---

## 🛠️ Actualización de Estado de Convocatoria

Para que el cálculo sea preciso, debes actualizar el estado de las convocatorias:

1. Durante el mes: estado = `'vigente'`
2. Después de cada jornada:
   - Asistió → `'cumplida'`
   - Faltó → `'con_inasistencia'`
3. Fin de mes → Ejecutar cálculo de saldos

---

## 📁 Archivos Relacionados

- [`sync_saldos.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/sync_saldos.gs) — Código principal
- [`config_tables.json`](file:///home/pablo/gestion-rrhh-centro/config_tables.json#L121-L144) — Configuración tabla saldos
- [`menu_updates.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/menu_updates.gs) — Menú actualizado
