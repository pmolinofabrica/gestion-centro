# Fase 2: El Cerebro - Motor de Asignación (Python)

Esta fase documenta la lógica algorítmica del motor de asignación `motor_asignacion_apertura5.py`, el corazón de la distribución justa de residentes en dispositivos de mediación cultural.

## 1. El Algoritmo de Asignación (3 Fases)

El motor funciona como un optimizador greedy que opera en tres fases secuenciales por cada día del mes:

### Fase 1: Cupo Mínimo
Asigna residentes a todos los dispositivos abiertos hasta llegar al cupo mínimo de cada uno. Prioriza usando el Score.

### Fase 2: Cupo Máximo
Con los residentes sobrantes, rellena dispositivos hasta su cupo máximo (ej: TARIMA DE PINTURA admite hasta 2).

### Fase 3: Emergencia (Overbooking)
Si aún quedan residentes sin asignar, los fuerza en dispositivos ya llenos con una penalización extra de `-200 × ocupación_actual`.

Los residentes que ni siquiera en emergencia pueden ser ubicados (sin capacitación en ningún dispositivo abierto) se registran con dispositivo `-1` ("SIN CAPACITACIÓN").

## 2. Fórmula de Scoring (Exacta)

```
Score = 1000
      - (repeticiones_en_este_dispositivo × 400)
      - (total_días_trabajados_en_el_mes × 100)
```

| Penalización | Valor | Efecto |
|---|---|---|
| **Repetición de Dispositivo** | `-400` por vez | Fuerza rotación: si ya estuvo en BATIK 2 veces, pierde 800 pts para BATIK |
| **Carga Laboral Global** | `-100` por día | Distribuye días: quien trabajó más días tiene Score más bajo globalmente |
| **Saturación (solo Fase 3)** | `-200` por ocupante extra | Penaliza asignar a un dispositivo ya lleno |

## 3. Heurística de Escasez (Innovación Clave)

**Antes de asignar**, el motor **ordena los dispositivos** por "escasez de candidatos capacitados":

```python
dispos_hoy = sorted(dispos_hoy_base, key=lambda d: contar_capacitados(d))
```

Los dispositivos con **menos gente capacitada eligen primero**, evitando que un dispositivo "difícil" se quede sin candidatos porque un dispositivo "fácil" los absorbió antes.

## 4. Cupos Configurados (Hardcodeados)

El motor tiene reglas de cupo diferenciadas por fecha:

- **7 y 8 de marzo**: Dispositivos simples (Lectura, Río Juegos M/T, Autorretratate) a cupo 1; el resto a cupo 2.
- **Resto del mes**: TARIMA y MESA DE PINTURA fijos en 2. BATIK, CONVIVENCIA, FÁBRICA DE PAPEL, MESA DE ENSAMBLE opcionales 1-2. Todos los demás en 1.

> [!WARNING]
> Estos cupos están hardcodeados en la función `obtener_cupos()`. Para meses futuros se necesita parametrizar o leer de `calendario_dispositivos`.

## 5. Flujo de Ejecución Técnica

1. **Extraer Capacitaciones**: Lee `vista_historial_capacitaciones` vía REST API (no SDK).
2. **Extraer Convocatorias**: Lee `vista_convocatoria_completa` filtrando descansos (`id_turno = 20`).
3. **Simular Capacitaciones Futuras**: Inyecta capacitaciones planificadas para el 10, 11 y 20 de marzo (hardcodeadas en `nuevos`).
4. **Loop de Asignación**: Itera día × dispositivo (ordenado por escasez) × candidato (ordenado por Score).
5. **Salida**: Genera `matriz_rotacion_completa.md` con la tabla Markdown de asignaciones.

## 6. Script de Producción vs. Script de Planificación

| Script | Uso | Invocado desde |
|---|---|---|
| `motor_asignacion_apertura5.py` | Genera la matriz Markdown de planificación | Manual (CLI) |
| `motor_asignaciones_supabase.py` | Escribe directamente en la tabla `menu` de Supabase | `route.ts` (botón "Generar") |

> [!IMPORTANT]
> El frontend invoca `motor_asignaciones_supabase.py` (no la versión `apertura5`). Ambos deben mantener la misma lógica de scoring.

## 7. Scripts de Mantenimiento

| Script | Propósito |
|---|---|
| `undo_menu_marzo.py` | Borra asignaciones desde una fecha hacia adelante (antes de regenerar) |
| `diagnostico_limpieza_ab.py` | Verifica consistencia de la división alfabética de grupos |
| `check_descansos.py` | Valida que nadie esté asignado en su franco |
| `fix_duplicates_2026.py` | Limpia registros duplicados de la tabla `menu` |
| `fix_capacitacion_dates.py` | Corrige fechas de capacitación mal formateadas |
