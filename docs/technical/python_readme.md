# Scripts Python - Sistema RRHH

## 📚 Archivos Principales

### Conexión a Base de Datos

**db_connection_helper.py** ⭐⭐⭐
- Helper para conexiones con Foreign Keys activadas automáticamente
- Uso recomendado en todos tus scripts

```python
from db_connection_helper import get_connection

with get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tabla")
```

### Scripts de Sistema

**verificar_sistema.py** ⭐⭐⭐
- Verificación completa del sistema
- Uso: `python3 verificar_sistema.py ../data/gestion_rrhh.db`

**setup_proyecto.py** ⭐⭐
- Inicialización automática del proyecto
- Genera estructura, días, datos de ejemplo
- Uso: `python3 setup_proyecto.py`

**error_logger_python.py** ⭐⭐⭐
- Sistema de logging automático (600+ líneas)
- Decoradores para funciones
- Dashboard de salud

**test_conexion.py** ⭐
- Prueba rápida de conexión y Foreign Keys
- Uso: `python3 test_conexion.py`

### Scripts de Utilidades

**activar_foreign_keys.py**
- Activa Foreign Keys y crea el helper
- Uso: `python3 activar_foreign_keys.py ../data/gestion_rrhh.db`

**corregir_schema.py**
- Corrige sintaxis de triggers para SQLite
- Uso: `python3 corregir_schema.py ../sql/schema_original.sql`

## 🚀 Quick Start

```bash
# Probar conexión
python3 test_conexion.py

# Verificar sistema
python3 verificar_sistema.py ../data/gestion_rrhh.db

# Usar en tus scripts
from db_connection_helper import get_connection
```

## ⚠️ IMPORTANTE

**SIEMPRE** usa `db_connection_helper.get_connection()` para conectarte a la BD.

Esto garantiza que las Foreign Keys estén activadas.
