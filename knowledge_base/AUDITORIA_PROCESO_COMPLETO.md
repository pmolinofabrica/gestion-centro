# 🔍 Auditoría Integral del Proceso de Trabajo (Actualizada)

**Fecha**: 2026-03-01  
**Versión**: 2.0 (Post-correcciones)

---

## 1. Bugs Detectados y Corregidos

### ✅ Bug 1: UndoStack fallaba para acciones de "Quitar"
- **Problema**: `handleUndoLastAction` usaba `.eq('id_asignacion')` pero las acciones de Remove no guardaban ese campo → el undo era `undefined`.
- **Solución**: Se implementaron dos rutas de undo: **Ruta A** (por `id_asignacion`, para AssignVacant) y **Ruta B** (por `id_agente` + `fecha_asignacion`, para Remove/Swap/Quitar-inline).

### ✅ Bug 2: Swap no registraba en UndoStack
- **Problema**: `handleSwapResident` actualizaba la DB sin guardar estado previo.
- **Solución**: Se agregó `setUndoStack(prev => [...prev, { ... }])` antes del UPDATE con `action_type: 'swap'`.

### ✅ Bug 3: Quitar-inline de Apertura no registraba en UndoStack
- **Problema**: El botón "Quitar" de la pestaña Apertura (inline) hacía el UPDATE pero no apilaba la acción.
- **Solución**: Se agregó push al undoStack con `action_type: 'quitar_inline'` tras el UPDATE exitoso.

### ✅ Bug 4: Modal de Descansos hardcodeado
- **Problema**: El modal "Plantilla en Descanso" mostraba siempre a "Zárate" y "Mendicino" sin conexión a la DB.
- **Solución**: Se reemplazó el contenido estático por un render dinámico que consulta `allResidentsDb` filtrando los que NO están en `convocadosDb[fecha]`. El botón "Llamar y Asignar" ahora ejecuta `handleAssignFromPool()`.

---

## 2. Documentos Corregidos

| Documento | Corrección |
|---|---|
| **Fase 1** | Agregadas 4 tablas de capacitaciones + 3 vistas que faltaban |
| **Fase 2** | Reescrita completamente: fórmula de scoring exacta, 3 fases del algoritmo, heurística de escasez, distinción `apertura5.py` vs `supabase.py` |
| **Fase 3** | Reescrita completamente: ~200% más detalle. Incluye cada sidebar, modal, variable de estado, estructura del UndoStack, route.ts, y Panel de Dispositivos |
| **Handover** | Corregido: dos scripts Python, advertencia sobre route.ts y datos mock |

---

## 3. Auditoría de Seguridad Pre-GitHub (99 archivos pendientes)

### 🔴 CRÍTICO: URLs de Proyecto Supabase Hardcodeadas

Dos IDs de proyecto Supabase están expuestos en texto plano:

| ID de Proyecto | Archivos |
|---|---|
| `zgzqeusbpobrwanvktyz` | `check_agent_duplicates.py`, `execute_migration.py`, `manager.py` |
| `hyjelbdkklvhiwlnyzng` | `apply_migration_remove_col.py`, `inspect_convocatoria_cols.py` |

> [!CAUTION]
> Estos IDs permiten identificar tu instancia de Supabase. Combinados con una key filtrada, darían acceso total a la base de datos.

### 🔴 CRÍTICO: Archivos de Test en Raíz del Proyecto

Los siguientes archivos en la **raíz** del proyecto leen `config/supabase.json` y hacen requests directas a la API REST de Supabase. Si `config/supabase.json` se filtra en algún momento, estos scripts muestran exactamente cómo usarla:

```
test.js, test2.js, test3.js, test4.js, test5.js, test6.js, test7.js,
test8.js, test9.js, test10.js, test11.js, test12.js, test13.js, test14.js
test.py, test2.py, test_db.py, test_pd_style.py
```

**Recomendación**: Agregar `test*.js`, `test*.py`, `test_db.py`, `test_pd_style.py` al `.gitignore` o eliminarlos antes del push.

### 🟡 ADVERTENCIA: Rutas Absolutas Personales

Más de 30 archivos Python contienen la ruta `/home/pablo/Documentos/gestion-centro/config/supabase.json`. Aunque no exponen la key directamente, revelan:
- El nombre de usuario del sistema operativo (`pablo`).
- La estructura exacta del filesystem del servidor de desarrollo.

### 🟡 ADVERTENCIA: `route.ts` con Ruta Absoluta

```typescript
const scriptsPath = '/home/pablo/Documentos/gestion-centro/scripts/python';
```

Esto no solo expone la ruta del sistema, sino que **no funcionará** si el proyecto se clona en otra máquina.

### 🟡 ADVERTENCIA: `schema_dump.txt` y `streamlit.log`

Archivos de infraestructura que pueden contener información sobre la estructura de la DB o logs con datos sensibles.

### ✅ Protecciones que SÍ funcionan

| Protección | Estado |
|---|---|
| `config/supabase.json` en `.gitignore` | ✅ Protegido |
| `config/*.json` en `.gitignore` | ✅ Protegido |
| `frontend/.env.local` en `frontend/.gitignore` | ✅ Protegido (regla `.env*`) |
| `.env` y `*.env` en `.gitignore` raíz | ✅ Protegido |
| `service_account.json` en `.gitignore` | ✅ Protegido |
| `node_modules/` en `.gitignore` | ✅ Protegido |
| `__pycache__/` en `.gitignore` | ✅ Protegido |

---

## 4. Recomendaciones de Acción Inmediata

### Antes de hacer `git push`:

1. **Agregar al `.gitignore`**:
```
# Test files (contain API patterns)
test*.js
test*.py
test_db.py
test_pd_style.py

# Infrastructure dumps
schema_dump.txt
streamlit.log
analyze_2026_data.py
```

2. **Sanitizar URLs hardcodeadas** en los 5 archivos que contienen IDs de proyecto Supabase. Reemplazar por lectura de `config/supabase.json`.

3. **Evaluar si `app_asignaciones/`** (el prototipo Streamlit) debe subirse. Contiene `app.py` con patrones de acceso a la service_role_key.

4. **Considerar un `.gitignore` para scripts de debug**: Los archivos `debug_*.py`, `diagnose_*.py`, `fix_*.py` son herramientas internas que quizás no valga la pena exponer públicamente.
