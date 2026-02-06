# Workflow: Cambio de Turno entre Residentes

## Estrategia: Cancel + New con Link (Option A - DAMA Compliant)

### Principios
1. **Inmutabilidad**: El registro original no se modifica (excepto estado).
2. **Trazabilidad**: El nuevo turno referencia al original vía `id_convocatoria_origen`.
3. **Auditoría**: `motivo_cambio` documenta la razón.

---

## Proceso

### Paso 1: Recepción de Solicitud
- Residente A solicita cambio con Residente B.
- Datos requeridos: Día, Tipo de Turno, DNI/Nombre de ambos.

### Paso 2: Validación
- Verificar que ambos residentes tienen turnos asignados en los días indicados.
- Confirmar que el intercambio es simétrico (A toma turno de B, B toma turno de A).

### Paso 3: Registro en Sistema

#### Para cada turno afectado:

**A) Cancelar Turno Original**
```sql
UPDATE convocatoria 
SET 
    turno_cancelado = TRUE,
    estado = 'cancelada',
    motivo_cambio = 'Cambio con [Nombre Otro Residente] - [Fecha Nuevo Turno]',
    fecha_modificacion = NOW(),
    usuario_modificacion = 'admin'
WHERE id_convocatoria = [ID_TURNO_ORIGINAL];
```

**B) Crear Nuevo Turno**
```sql
INSERT INTO convocatoria (
    id_plani, id_agente, id_turno, fecha_convocatoria, 
    estado, id_convocatoria_origen, motivo_cambio
) VALUES (
    [ID_PLANI_NUEVO],
    [ID_AGENTE],
    [ID_TURNO_NUEVO],
    [FECHA_NUEVA],
    'vigente',
    [ID_TURNO_ORIGINAL],  -- Link al turno cancelado
    'Cambio desde [Fecha Original] con [Nombre Otro Residente]'
);
```

### Paso 4: Confirmación
- Notificar a ambos residentes.
- Verificar en Dashboard que los saldos se calculan correctamente.

---

## Diagrama de Relación

```
┌─────────────────────────┐
│  CONVOCATORIA ORIGINAL  │
│  id_convocatoria: 100   │
│  estado: 'cancelada'    │
│  turno_cancelado: TRUE  │
└───────────┬─────────────┘
            │
            │ id_convocatoria_origen
            ▼
┌─────────────────────────┐
│   CONVOCATORIA NUEVA    │
│  id_convocatoria: 150   │
│  estado: 'vigente'      │
│  id_convocatoria_origen:│
│         100             │
└─────────────────────────┘
```

---

## Casos de Uso Comunes

| Caso | Acción |
|------|--------|
| Cambio de día capacitación | Cancel turno día X, crear turno día Y |
| Cambio mañana/tarde mismo día | Cancel turno mañana, crear turno tarde |
| Intercambio fin de semana | Cancel ambos turnos, crear 2 nuevos cruzados |
| Cambio sin contraparte (excepcional) | Edición directa vía Sync Convocatoria |

---

## Vista de Auditoría (SQL)

Ver `vista_cambios_turno` en `dama_implementation_v1.sql`.
