# 🌐 Guía de Operación: Entorno Híbrido (SQLite + Supabase)

**Bienvenido a la arquitectura híbrida.**

Esta guía está diseñada para explicar cómo funciona tu sistema actual, que media entre una base de datos local (**SQLite**) y una base de datos en la nube (**Supabase PostgreSQL**).

---

## 1. ¿Cómo funciona el sistema? (La "Magia" detrás)

Imagina que tienes dos archivadores:
1.  **Archivo Local (SQLite):** Está en tu disco duro. Es rapidísimo, funciona sin internet, pero solo tú lo ves. Aquí guardamos el **historial antiguo**.
2.  **Archivo en la Nube (Supabase):** Está en internet. Es seguro, accesible desde cualquier lugar, pero requiere conexión. Aquí guardamos los **datos del año actual**.

### El "Cerebro": `UnifiedDBManager`

No tienes que elegir manualmente qué base de datos usar cada vez. El script `unified_db_manager.py` actúa como un policía de tráfico:
El `dashboard_rrhh_5.py` implementa una lógica similar:

*   Si pides datos de **2025 o posterior** → Te conecta a **Supabase**.
*   Si pides datos de **2024 o anterior** → Te conecta a **SQLite**.
*   Si se corta internet → Intenta usar la copia local (caché).

---

## 2. Casos de Uso Comunes

### A. Operación Diaria (Online)
*   **Acción:** Registrar una nueva inasistencia o cambiar un turno hoy.
*   **Flujo:** El sistema detecta que la fecha es actual. Envía los datos directamente a Supabase.
*   **Ventaja:** Los cambios son visibles inmediatamente para todos los usuarios/dispositivos conectados.

### B. Consulta Histórica
*   **Acción:** Generar un reporte de horas del año 2023.
*   **Flujo:** El sistema detecta una fecha antigua. Consulta el archivo `gestion_rrhh.db` local.
*   **Ventaja:** No consume datos ni conexiones de la nube; es instantáneo.

### C. Modo "Sin Conexión" (Offline)
*   **Situación:** Se cae internet en el centro cultural.
*   **Flujo:** El sistema detecta el error de conexión y cambia a modo `SQLITE`. Puedes seguir consultando datos (lectura), pero las escrituras (guardar datos nuevos) se guardan localmente para sincronizarse después.

---

## 3. ⚠️ Atenciones y Cuidados (Lo que NO debes hacer)

Al trabajar con Supabase (PostgreSQL), las reglas son más estrictas que con SQLite.

### 1. Tipos de Datos Estrictos
*   **SQLite:** Es permisivo. Puedes guardar texto en un campo de fecha.
*   **Supabase:** Es estricto. Si el campo es `DATE`, debe ser `YYYY-MM-DD`. Si intentas guardar "30 de febrero", **explotará**.
*   **Consejo:** Valida siempre los datos en Python antes de enviarlos.

### 2. Gestión de Conexiones (El "Pooler")
*   **El Problema:** En la nube, abrir y cerrar conexiones es costoso y lento.
*   **La Solución:** Usamos el puerto **6543** (Transaction Pooler).
*   **Cuidado:** Nunca dejes conexiones abiertas (`conn`) si no las estás usando. Usa siempre los bloques `with` en Python o asegúrate de llamar a `.close()`.

### 3. Seguridad (RLS - Row Level Security)
*   **El Peligro:** A diferencia de tu archivo local, Supabase está en internet.
*   **La Regla:** Nunca desactives RLS (`ALTER TABLE ... DISABLE ROW LEVEL SECURITY`) en producción. Las políticas de seguridad son las que impiden que un extraño lea tus datos aunque tenga la URL de tu proyecto.

### 4. Migraciones (Cambios en la estructura)
*   Si agregas una columna en SQLite, **NO** aparece mágicamente en Supabase.
*   Debes ejecutar el comando SQL `ALTER TABLE...` en el Editor SQL de Supabase para mantener ambas bases sincronizadas.

---

## 4. Lista de Comandos Útiles

Usa estos scripts desde tu terminal en VSCode para gestionar el entorno.

### 🔍 Diagnóstico y Estado
Verifica si estás conectado y la salud de las tablas.
```bash
python3 remote_troubleshoot.py --status
```

### 🛠️ Consola SQL Remota
Para ejecutar consultas rápidas directamente en Supabase sin abrir el navegador.
```bash
python3 remote_troubleshoot.py --sql
```
*Dentro de la consola:*
*   `.tables` : Lista todas las tablas.
*   `.count nombre_tabla` : Cuenta registros.
*   `.exit` : Salir.

### 🔄 Sincronización (Sync)
Fuerza el envío de datos locales a la nube o viceversa.
```bash
# Ver qué pasaría (simulacro)
python3 sync_manager.py --preview

# Ejecutar sincronización real
python3 sync_manager.py --sync
```

### 🧪 Test de Conexión Unificado
Prueba la lógica de decisión de año.
```bash
python3 unified_db_manager.py
```

---

## 5. Acceso a Vistas (Reportes Automáticos)

Las "Vistas" son tablas virtuales que ya tienen los cálculos hechos (como los JOINs complejos). Úsalas para tus reportes.

### Principales Vistas Disponibles:

| Nombre de la Vista | Descripción | Uso Principal |
| :--- | :--- | :--- |
| `vista_convocatorias_activas` | Lista limpia de quién trabaja hoy, con nombres y horarios. | Dashboard diario, Cartelera. |
| `vista_saldos_actuales` | Horas acumuladas por agente, calculadas automáticamente. | Reportes mensuales, Liquidación. |
| `vista_inasistencias_mes` | Faltas del mes actual con estado de justificación. | Control de ausentismo. |
| `vista_salud_sistema` | Muestra errores técnicos y estado de la conexión. | Monitoreo técnico. |

### Cómo consultar una vista (Ejemplo Python):

```python
from unified_db_manager import UnifiedDBManager

db = UnifiedDBManager()

# Obtener datos ya procesados
resultado = db.query("SELECT * FROM vista_saldos_actuales WHERE nivel = 'BAJO'")

for fila in resultado.data:
    print(f"Agente: {fila['nombre_completo']} - Horas: {fila['horas_mes']}")
```

### Cómo consultar una vista (SQL Directo):

```sql
-- En la consola SQL de Supabase o remote_troubleshoot.py
SELECT * FROM vista_convocatorias_activas 
WHERE fecha_convocatoria = CURRENT_DATE;
```

---

## Resumen de Emergencia

1.  **¿Error de conexión?** Revisa tu archivo `.env` y asegúrate de usar el puerto `6543`.
2.  **¿Datos duplicados?** Ejecuta `python3 remote_troubleshoot.py --diagnose`.
3.  **¿No se guardan los cambios?** Verifica si estás editando una Vista (son de solo lectura) en lugar de la Tabla real.