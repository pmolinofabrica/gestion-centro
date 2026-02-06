# Guía: Dashboard Operativo

## 🎯 Objetivo
Visualizar el estado de la cobertura de turnos y el desempeño del personal sin necesidad de consultas complejas. Todo ocurre en la hoja **DASHBOARD**.

## 📊 Métricas Incluidas

### KPIs Principales (Tarjetas Superiores)
- **CUBRIMIENTO**: % de turnos cubiertos sobre lo planificado.
  - 🟢 > 95% (Ideal)
  - 🔴 < 95% (Atención)
- **VACANTES**: Cantidad absoluta de puestos sin cubrir.
- **TURNOS TOTALES**: Demanda total planificada.
- **HORAS PLANIF**: Carga horaria total del mes.

### Detalle Diario (Tabla Central)
Muestra calendario día a día con semáforo:
- 🟢 **OK**: 100% cubierto
- 🟡 **PARCIAL**: 80-99% cubierto
- 🔴 **CRÍTICO**: < 80% cubierto (texto rojo)

### Top Agentes
Ranking de los 5 agentes con más turnos asignados en el mes.

---

## 🚀 Cómo Usar

1. **Configurar Año**:
   - Menú `🔌 Supabase` → `⚙️ Configuración` → `Configurar Filtros`
   - Asegúrate de que `año_activo` sea correcto (ej: 2026).

2. **Generar Reporte**:
   - Menú `📊 Actualizar Dashboard`.
   - Ingresa el **Mes** (1-12).

3. **Esperar**:
   - El script descargará datos de Planificación y Convocatoria.
   - Calculará métricas en memoria (puede tardar 5-10 seg).
   - Pintará la hoja `DASHBOARD`.

---

## ⚠️ Solución de Problemas

**"El Dashboard está vacío o en ceros"**
- Verifica que hayas sincronizado datos en `PLANIFICACION` y `CONVOCATORIA` para ese mes.
- Revisa el `año_activo` en la hoja `CONFIG`.

**"Error: Mes inválido"**
- Debes ingresar un número del 1 al 12.

**"No coinciden los números con la hoja Convocatoria"**
- El Dashboard solo cuenta convocatorias con estado `vigente` o `cumplida`.
- Las `cancelada` o `con_inasistencia` no suman a la cobertura.

---

## 📁 Archivos Relacionados
- [`dashboard.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/dashboard.gs) — Lógica de cálculo y renderizado.
- [`menu_updates.gs`](file:///home/pablo/gestion-rrhh-centro/admin_tools/gas_scripts/menu_updates.gs) — Ítem de menú.
