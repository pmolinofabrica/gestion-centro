#!/usr/bin/env python3
"""
Script de organización final del proyecto
Mueve archivos a sus ubicaciones correctas y hace ajustes
"""

import shutil
from pathlib import Path

def organizar_proyecto():
    """Organiza archivos y hace ajustes finales"""
    
    print("="*70)
    print("  ORGANIZACIÓN FINAL DEL PROYECTO")
    print("="*70)
    
    project_root = Path.cwd()
    
    # 1. Mover helper a python/
    print("\n1. Organizando archivos...")
    helper_root = project_root / 'db_connection_helper.py'
    helper_python = project_root / 'python' / 'db_connection_helper.py'
    
    if helper_root.exists():
        shutil.move(str(helper_root), str(helper_python))
        print(f"   ✓ Movido: db_connection_helper.py → python/")
    elif helper_python.exists():
        print(f"   ✓ Helper ya está en python/")
    else:
        print(f"   ⚠ Helper no encontrado")
    
    # 2. Actualizar verificar_sistema.py para activar FKs
    print("\n2. Actualizando verificar_sistema.py...")
    verificar_path = project_root / 'python' / 'verificar_sistema.py'
    
    if verificar_path.exists():
        with open(verificar_path, 'r') as f:
            content = f.read()
        
        # Buscar la línea de conexión y añadir PRAGMA si no está
        if 'PRAGMA foreign_keys' not in content:
            # Reemplazar la línea de conexión
            content = content.replace(
                'conn = sqlite3.connect(db_path)',
                'conn = sqlite3.connect(db_path)\n        conn.execute("PRAGMA foreign_keys = ON")'
            )
            
            with open(verificar_path, 'w') as f:
                f.write(content)
            print("   ✓ verificar_sistema.py actualizado con PRAGMA foreign_keys")
        else:
            print("   ✓ verificar_sistema.py ya tiene PRAGMA foreign_keys")
    
    # 3. Crear script de prueba
    print("\n3. Creando script de prueba...")
    test_path = project_root / 'python' / 'test_conexion.py'
    
    test_code = '''#!/usr/bin/env python3
"""
Script de prueba de conexión con Foreign Keys
"""

from db_connection_helper import get_connection

def test_conexion():
    """Prueba la conexión y las Foreign Keys"""
    
    print("="*70)
    print("  TEST DE CONEXIÓN")
    print("="*70)
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Verificar Foreign Keys
            cursor.execute("PRAGMA foreign_keys")
            fk_status = cursor.fetchone()[0]
            print(f"\\n1. Foreign Keys: {'✓ ACTIVADAS' if fk_status else '✗ DESACTIVADAS'}")
            
            # 2. Ver configuración
            print("\\n2. Configuración del sistema:")
            cursor.execute("SELECT clave, valor FROM configuracion LIMIT 3")
            for row in cursor.fetchall():
                print(f"   • {row['clave']}: {row['valor']}")
            
            # 3. Contar tablas
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM datos_personales) as agentes,
                    (SELECT COUNT(*) FROM dispositivos) as dispositivos,
                    (SELECT COUNT(*) FROM dias) as dias,
                    (SELECT COUNT(*) FROM turnos) as turnos
            """)
            counts = cursor.fetchone()
            
            print("\\n3. Estado de las tablas:")
            print(f"   • Agentes: {counts['agentes']}")
            print(f"   • Dispositivos: {counts['dispositivos']}")
            print(f"   • Días generados: {counts['dias']}")
            print(f"   • Turnos: {counts['turnos']}")
            
            # 4. Salud del sistema
            cursor.execute("SELECT estado_sistema FROM vista_salud_sistema")
            salud = cursor.fetchone()['estado_sistema']
            print(f"\\n4. Estado del sistema: {salud}")
            
            print("\\n" + "="*70)
            print("✅ CONEXIÓN FUNCIONANDO CORRECTAMENTE")
            print("="*70)
            
    except Exception as e:
        print(f"\\n❌ Error: {e}")
        return False
    
    return True

if __name__ == '__main__':
    import sys
    success = test_conexion()
    sys.exit(0 if success else 1)
'''
    
    with open(test_path, 'w') as f:
        f.write(test_code)
    print(f"   ✓ Creado: python/test_conexion.py")
    
    # 4. Crear README en python/
    print("\n4. Creando README en python/...")
    readme_path = project_root / 'python' / 'README.md'
    
    readme_content = '''# Scripts Python - Sistema RRHH

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
'''
    
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    print(f"   ✓ Creado: python/README.md")
    
    # 5. Resumen final
    print("\n" + "="*70)
    print("✅ ORGANIZACIÓN COMPLETA")
    print("="*70)
    print("""
Estructura actualizada:
  python/
  ├── db_connection_helper.py     ⭐ Usar en todos tus scripts
  ├── verificar_sistema.py         (actualizado con PRAGMA)
  ├── test_conexion.py             (nuevo)
  ├── setup_proyecto.py
  ├── error_logger_python.py
  ├── activar_foreign_keys.py
  ├── corregir_schema.py
  └── README.md                    (nuevo)

Próximos pasos:
  1. cd ~/gestion-rrhh-centro
  2. python3 python/test_conexion.py
  3. python3 python/verificar_sistema.py data/gestion_rrhh.db
  4. ¡Empezar a desarrollar!
""")

if __name__ == '__main__':
    organizar_proyecto()
