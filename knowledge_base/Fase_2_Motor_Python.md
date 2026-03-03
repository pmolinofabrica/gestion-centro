# Fase 2: El Cerebro - Motor de Asignación (Python v2.0)

Esta fase documenta la lógica algorítmica del motor de asignación actualizado (`motor_asignaciones_supabase.py`), el corazón de la distribución de residentes en dispositivos.

## 1. El Algoritmo de Asignación (Secuencial Multi-criterio)

El motor funciona como un optimizador greedy iterativo que procesa día por día, dispositivo por dispositivo, priorizando aquellos con **mayor escasez de personal capacitado**.

A diferencia de versiones anteriores, **no inventa cupos**. Lee estrictamente la base de datos:
1. Extrae los cupos específicos guardados por el usuario en `calendario_dispositivos` para el mes entero.
2. Si un dispositivo/día no tiene un registro explícito en `calendario_dispositivos`, el motor asume **cupo = 0** y no asigna a nadie allí (evita sobrescribir silenciosamente con valores predeterminados no deseados).

## 2. Constraints y Reglas de Negocio

El motor respeta rigurosamente 4 "Hard Constraints" (Reglas inquebrantables):
* **Constraint A (Disponibilidad):** El agente debe estar convocado ese día (existir en la tabla `convocatoria` para la fecha/turno dada).
* **Constraint B (Capacitación):** El agente debe tener una capacitación aprobada para el dispositivo objetivo con fecha igual o anterior al día de la asignación.
* **Constraint C (Unicidad):** Un agente no puede ser asignado a más de un dispositivo el mismo día.
* **Constraint D (Inasistencias):** **[NUEVO]** Si el agente figura en la tabla `inasistencias` para ese día específico, queda automáticamente descalificado (ignorado) en el proceso de asignación.

## 3. Fórmula de Scoring Multicriterio (Soft Constraints)

Para decidir quién va a qué dispositivo de entre los candidatos aptos, el motor calcula un puntaje (Score) para cada candidato, seleccionando al que tenga el score más alto.

```python
Score = 1000
      - (veces_asignado_a_ESTE_dispositivo_en_el_mes × 500)
      - (total_días_asignados_globalmente_en_el_mes × 80)
      + Random(0, 5) # Tie-breaker reproducible
```

| Factor | Peso | Objetivo Estratégico |
|---|---|---|
| **Base** | `1000` | Punto de partida constante. |
| **Fatiga Local** | `-500` por repetición | Penalización ultra-severa para forzar la rotación. Si un residente ya estuvo en BATIK, es casi imposible que vuelva a ir si hay otro disponible. |
| **Carga Global** | `-80` por día | Distribución equitativa. Quien trabajó menos días en el mes tiene prioridad sobre quien acumula más días trabajados. |
| **Reproducibilidad** | `+0 a 5` | Desempate pseudo-aleatorio con semilla (`random.seed(dia-agente-dispositivo)`). Garantiza que correr el algoritmo 10 veces con los mismos datos genere **exactamente la misma salida**, mejorando el testing. |

> [!CAUTION]
> **Crash de Postgres (`chk_orden`)**: El multicriterio puede generar puntajes negativos. Como el modelo de datos de `menu` requiere un campo `orden` numérico positivo, el motor inyecta `max(1, score)` antes de enviar a Supabase para prevenir una falla de integridad (Error 23514).

## 4. Heurística de Escasez Diaria (Fase 1)

Antes de realizar cruces, el motor evalúa cuántas personas capacitadas *y disponibles hoy* hay para cada dispositivo. 
Luego, ordena los dispositivos de **menor a mayor cantidad de candidatos aptos**. 

*Efecto:* Los dispositivos "difíciles" (ej: TELA COLECTIVA, que tiene pocos capacitados) eligen primero. Los dispositivos "fáciles" (ej: SECTOR DE LECTURA) eligen últimos, absorbiendo al excedente de personal.

## 5. Lecciones Aprendidas de Datos (Bugs Históricos)

### El Fallo de las 1000 filas de Supabase
Supabase (PostgREST) implementa un límite estricto de seguridad de 1000 filas (paginación) para consultas sin filtrar. 
En versiones previas, el motor ejecutaba `supabase.table("calendario_dispositivos").select("*").execute()`. Como la tabla pasó las 22.000 filas históricas, el API **truncaba silenciosamente** la respuesta, devolviendo registros del 2024. 
El motor "creía" que el mes actual no tenía configuraciones de cupo, asignaba 0 residentes, y la UI visualizaba esto como si el motor hubiese borrado el `.length` de la matriz.
**Solución:** Uso estricto de filtros temporales (`.gte("fecha", inicio).lte("fecha", fin)`) en todas las tablas transaccionales masivas antes del `.execute()`.

### El Fallo del Fallback Cero
Nunca permitir que la UI invente el valor `matriz.length` como sustituto visual de la base de datos si el motor no asigna. La UI y el Motor deben leer la misma fuente de verdad: lo que el humano haya guardado explícitamente en `calendario_dispositivos`.
