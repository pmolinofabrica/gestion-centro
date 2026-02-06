# PROJECT_AUDIT.md

## 1. Estructura de Archivos (/frontend)

```text
frontend/
├── app/
│   ├── actions/
│   │   ├── logistica.ts       (Server Action: Módulo C)
│   │   ├── rrhh.ts            (Server Action: Módulo D)
│   │   ├── saldos.ts          (Server Action: Módulo E)
│   │   ├── scheduler.ts       (Server Action: Módulo A)
│   │   └── visitas.ts         (Server Action: Módulo B)
│   ├── logistica/
│   │   └── page.tsx           (Vista: Gemelo Digital)
│   ├── planificacion/
│   │   └── page.tsx           (Vista: Scheduler Matrix)
│   ├── rrhh/
│   │   └── page.tsx           (Vista: Novedades)
│   ├── saldos/
│   │   └── page.tsx           (Vista: Tablero Equidad)
│   ├── visitas/
│   │   └── page.tsx           (Vista: Booking)
│   ├── globals.css
│   └── layout.tsx
├── components/
│   ├── layout/
│   │   └── Sidebar.tsx        (Navegación Principal)
│   ├── logistica/
│   │   ├── DeviceCard.tsx     (Tarjeta de Espacio Físico)
│   │   └── FloorMap.tsx       (Mapa Visual Interactiva)
│   ├── rrhh/
│   │   └── NovedadForm.tsx    (Formulario Inasistencias)
│   ├── saldos/
│   │   ├── AjusteModal.tsx    (Modal Corrección Horas)
│   │   └── SaldosTable.tsx    (Tabla con Semáforo)
│   ├── scheduler/
│   │   └── SchedulerGrid.tsx  (Matriz Drag & Drop)
│   └── visitas/
│       └── BookingForm.tsx    (Formulario de Carga)
├── context/
│   └── YearContext.tsx        (Estado Global Año Fiscal)
├── utils/
│   └── supabase/              (Clientes SSR)
├── next.config.mjs
├── package.json
└── tailwind.config.ts (automático en v4)
```

## 2. Mapa de Integraciones

### Módulo E: Saldos (Equidad)
*   **Vista**: `app/saldos/page.tsx`
*   **Lógica**: `app/actions/saldos.ts`
*   **Tablas Supabase**:
    *   `vista_saldo_horas_live` (Lectura): Obtiene deuda real y meta teórica.
    *   `ajustes_horas` (Escritura): Inserta correcciones manuales.

### Módulo A: Scheduler (Planificación)
*   **Vista**: `app/planificacion/page.tsx`
*   **Lógica**: `app/actions/scheduler.ts`
*   **Tablas Supabase**:
    *   `convocatoria` (Lectura/Escritura): Lee turnos asignados e inserta nuevas asignaciones.
    *   `planificacion` (Lectura): Obtiene cupos y estructura del mes.
    *   `visitas_grupales` (Lectura): **Integración**: Consulta visitas 'confirmadas' para mostrar alertas (Bus 🚌).

### Módulo B: Visitas (Booking)
*   **Vista**: `app/visitas/page.tsx`
*   **Lógica**: `app/actions/visitas.ts`
*   **Tablas Supabase**:
    *   `visitas_grupales` (Escritura/Lectura): Inserta reservas y lee carga del día.
    *   `config_visitas_coeficientes` (Lectura): Obtiene ponderadores (fallback a Mock si falla la conexión).

### Módulo C: Logística (Gemelo Digital)
*   **Vista**: `app/logistica/page.tsx`
*   **Lógica**: `app/actions/logistica.ts`
*   **Tablas Supabase**:
    *   `dispositivos` (Lectura): Obtiene lista de espacios y pisos.
    *   *Nota*: El cálculo de "cobertura actual vs cupo" usa lógica simulada [MOCK] para la Demo al no detectar datos poblados en la tabla `menu`.

### Módulo D: RRHH (Novedades)
*   **Vista**: `app/rrhh/page.tsx`
*   **Lógica**: `app/actions/rrhh.ts`
*   **Tablas Supabase**:
    *   `inasistencias` (Escritura): Inserta Ceros/Tardanzas.

## 3. Estado de Implementación

| Funcionalidad | Estado | Detalles |
| :--- | :--- | :--- |
| **Scheduler -> Database** | **[REAL]** | Lee y escribe directamente en tabla `convocatoria`. |
| **Integración Visitas -> Scheduler** | **[REAL]** | El scheduler consulta `visitas_grupales` real. |
| **Lista Residentes (Deuda)** | **[REAL]** | Ordena usando `vista_saldo_horas_live`. |
| **Configuración Coeficientes** | **[HÍBRIDO]** | Intenta leer DB; usa Fallback hardcodeado si la tabla está vacía. |
| **Salud Dispositivos (Logística)** | **[SIMULADO]** | Lee dispositivos reales, pero simula la ocupación (al azar) para efectos de la Demo. |
| **Validación Tardanza (<15min)** | **[UX ONLY]** | Advertencia visual estática; el backend acepta el input tal cual. |

## 4. Dependencias Críticas
*   **Next.js**: `14.2.35` (Downgrade forzado por compatibilidad Node 18).
*   **React**: `18.3.1`
*   **Supabase**: `@supabase/ssr` + `@supabase/supabase-js`.
*   **UI**: `tailwindcss` v4, `lucide-react`.
