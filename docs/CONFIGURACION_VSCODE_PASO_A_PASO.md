# 🚀 Configuración del Entorno en VSCode - Paso a Paso

**Sistema RRHH v2.0**  
**Guía completa desde cero hasta proyecto funcionando**

---

## 📋 Tabla de Contenidos

1. [Requisitos previos](#requisitos-previos)
2. [Paso 1: Preparar el entorno](#paso-1-preparar-el-entorno)
3. [Paso 2: Configurar VSCode](#paso-2-configurar-vscode)
4. [Paso 3: Crear estructura del proyecto](#paso-3-crear-estructura-del-proyecto)
5. [Paso 4: Configurar Python](#paso-4-configurar-python)
6. [Paso 5: Inicializar base de datos](#paso-5-inicializar-base-de-datos)
7. [Paso 6: Verificar instalación](#paso-6-verificar-instalación)
8. [Paso 7: Primera prueba](#paso-7-primera-prueba)
9. [Configuración opcional](#configuración-opcional)
10. [Solución de problemas](#solución-de-problemas)

---

## 📦 REQUISITOS PREVIOS

### Software necesario:

- [x] **VSCode** instalado ([descargar](https://code.visualstudio.com/))
- [x] **Python 3.8+** instalado ([descargar](https://www.python.org/downloads/))
- [x] **Git** instalado (opcional pero recomendado)
- [x] Los archivos del sistema descargados

### Verificar instalaciones:

Abre una terminal y ejecuta:

```bash
# Verificar Python
python3 --version
# Debe mostrar: Python 3.8.x o superior

# Verificar pip
pip3 --version
# Debe mostrar: pip 20.x.x o superior

# Verificar SQLite
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"
# Debe mostrar: 3.35.x o superior
```

---

## 🔧 PASO 1: PREPARAR EL ENTORNO

### 1.1 Crear directorio del proyecto

```bash
# En Linux/Mac:
cd ~
mkdir -p proyectos/gestion-rrhh-centro
cd proyectos/gestion-rrhh-centro

# En Windows (PowerShell):
cd $HOME
mkdir proyectos\gestion-rrhh-centro
cd proyectos\gestion-rrhh-centro
```

### 1.2 Crear estructura de carpetas

```bash
# Linux/Mac:
mkdir -p {sql,python,logs,backups,config,docs,tests,data}

# Windows (PowerShell):
mkdir sql, python, logs, backups, config, docs, tests, data
```

**Resultado esperado:**
```
gestion-rrhh-centro/
├── sql/          # Archivos SQL
├── python/       # Scripts Python
├── logs/         # Logs del sistema
├── backups/      # Backups automáticos
├── config/       # Configuración
├── docs/         # Documentación
├── tests/        # Tests
└── data/         # Base de datos
```

### 1.3 Copiar archivos del sistema

Copia los archivos descargados a sus carpetas:

```bash
# Archivos SQL
cp /ruta/descarga/schema_final_completo.sql sql/

# Archivos Python
cp /ruta/descarga/error_logger_python.py python/
cp /ruta/descarga/verificar_sistema.py python/
cp /ruta/descarga/database_manager.py python/  # si lo tienes

# Scripts
cp /ruta/descarga/inicio_rapido.sh .

# Documentación
cp /ruta/descarga/*.md docs/
```

---

## 📝 PASO 2: CONFIGURAR VSCODE

### 2.1 Abrir proyecto en VSCode

```bash
# Abrir VSCode en la carpeta del proyecto
code .
```

O desde VSCode: `File > Open Folder` → Seleccionar `gestion-rrhh-centro`

### 2.2 Instalar extensiones recomendadas

Presiona `Ctrl+Shift+X` (o `Cmd+Shift+X` en Mac) y busca e instala:

#### Esenciales:
1. **Python** (Microsoft)
   - ID: ms-python.python
   - Para desarrollo Python

2. **SQLite** (alexcvzz)
   - ID: alexcvzz.vscode-sqlite
   - Para ver y editar base de datos

3. **SQLTools** (Matheus Teixeira)
   - ID: mtxr.sqltools
   - Cliente SQL avanzado

#### Recomendadas:
4. **Pylance** (Microsoft)
   - ID: ms-python.vscode-pylance
   - IntelliSense mejorado

5. **Python Indent** (Kevin Rose)
   - ID: KevinRose.vsc-python-indent
   - Indentación automática

6. **Rainbow CSV** (mechatroner)
   - ID: mechatroner.rainbow-csv
   - Para trabajar con CSVs

7. **Better Comments** (Aaron Bond)
   - ID: aaron-bond.better-comments
   - Comentarios coloreados

### 2.3 Configurar workspace

Crea el archivo `.vscode/settings.json`:

```bash
mkdir .vscode
```

Crea `.vscode/settings.json` con este contenido:

```json
{
    // Python
    "python.defaultInterpreterPath": "python3",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.analysis.typeCheckingMode": "basic",
    
    // Editor
    "editor.formatOnSave": true,
    "editor.rulers": [80, 120],
    "editor.tabSize": 4,
    "editor.insertSpaces": true,
    
    // Files
    "files.trimTrailingWhitespace": true,
    "files.insertFinalNewline": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/.DS_Store": true,
        "**/backups/*.db": true
    },
    
    // Terminal
    "terminal.integrated.defaultProfile.linux": "bash",
    "terminal.integrated.defaultProfile.windows": "PowerShell",
    
    // SQLite
    "sqlite.sqlite3": "sqlite3",
    "sqlite.logLevel": "INFO",
    
    // SQLTools
    "sqltools.useNodeRuntime": false,
    "sqltools.connections": [
        {
            "name": "RRHH Database",
            "driver": "SQLite",
            "database": "${workspaceFolder}/data/gestion_rrhh.db",
            "connectionTimeout": 30
        }
    ]
}
```

### 2.4 Crear archivo de tareas

Crea `.vscode/tasks.json`:

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Crear Base de Datos",
            "type": "shell",
            "command": "sqlite3 data/gestion_rrhh.db < sql/schema_final_completo.sql",
            "group": "build",
            "presentation": {
                "reveal": "always",
                "panel": "new"
            }
        },
        {
            "label": "Verificar Sistema",
            "type": "shell",
            "command": "python3 python/verificar_sistema.py data/gestion_rrhh.db",
            "group": "test",
            "presentation": {
                "reveal": "always",
                "panel": "new"
            }
        },
        {
            "label": "Backup Base de Datos",
            "type": "shell",
            "command": "cp data/gestion_rrhh.db backups/gestion_rrhh_$(date +%Y%m%d_%H%M%S).db",
            "group": "none"
        },
        {
            "label": "Abrir SQLite Browser",
            "type": "shell",
            "command": "sqlite3 data/gestion_rrhh.db",
            "group": "none"
        }
    ]
}
```

**Usar tareas:** `Ctrl+Shift+P` → "Tasks: Run Task"

---

## 🐍 PASO 3: CREAR ESTRUCTURA DEL PROYECTO

### 3.1 Crear archivos de configuración

#### `requirements.txt`

```txt
# Dependencias base
pandas>=1.3.0
plotly>=5.0.0

# Para Google Sheets (opcional)
gspread>=5.0.0
oauth2client>=4.1.3

# Para desarrollo
pytest>=7.0.0
black>=22.0.0
pylint>=2.12.0
ipython>=8.0.0

# Para visualización
matplotlib>=3.5.0
seaborn>=0.11.0
```

#### `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
*.egg-info/
dist/
build/

# Base de datos
data/*.db
data/*.db-journal
*.sqlite
*.sqlite3

# Backups
backups/*.db
backups/*.sql

# Logs
logs/*.log
logs/*.txt

# Configuración sensible
config/credentials.json
config/config.local.json
.env

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Tests
.pytest_cache/
.coverage
htmlcov/
```

#### `README.md` del proyecto

```markdown
# Sistema de Gestión RRHH - Centro Cultural

Sistema completo de gestión de recursos humanos para centros culturales con rotación anual del 100%.

## Quick Start

```bash
# Crear base de datos
sqlite3 data/gestion_rrhh.db < sql/schema_final_completo.sql

# Verificar instalación
python3 python/verificar_sistema.py data/gestion_rrhh.db
```

## Documentación

Ver carpeta `docs/` para guías completas.

## Estructura

- `sql/` - Schemas y scripts SQL
- `python/` - Scripts Python
- `data/` - Base de datos
- `docs/` - Documentación
- `logs/` - Logs del sistema
- `backups/` - Backups automáticos
```

---

## 🔨 PASO 4: CONFIGURAR PYTHON

### 4.1 Crear entorno virtual (RECOMENDADO)

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
# En Linux/Mac:
source venv/bin/activate

# En Windows:
venv\Scripts\activate

# Debes ver (venv) en tu prompt
```

### 4.2 Instalar dependencias

```bash
# Actualizar pip
pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt
```

### 4.3 Verificar instalación de paquetes

```bash
pip list
```

Deberías ver:
```
pandas        1.5.x
plotly        5.x.x
pytest        7.x.x
...
```

### 4.4 Configurar VSCode para usar el venv

1. Presiona `Ctrl+Shift+P`
2. Escribe: "Python: Select Interpreter"
3. Selecciona: `./venv/bin/python` (o `.\venv\Scripts\python.exe` en Windows)

Verifica en la barra inferior de VSCode que dice: `Python 3.x.x ('venv')`

---

## 💾 PASO 5: INICIALIZAR BASE DE DATOS

### 5.1 Crear la base de datos

**Opción A: Desde terminal integrada de VSCode**

1. Abre terminal: `Ctrl+ñ` (o `` Ctrl+` `` )
2. Ejecuta:

```bash
sqlite3 data/gestion_rrhh.db < sql/schema_final_completo.sql
```

**Opción B: Usando tareas de VSCode**

1. Presiona `Ctrl+Shift+P`
2. Escribe: "Tasks: Run Task"
3. Selecciona: "Crear Base de Datos"

**Opción C: Script Python automatizado**

Crea `python/init_database.py`:

```python
#!/usr/bin/env python3
"""
Script de inicialización de base de datos
"""
import sqlite3
import os
from pathlib import Path

def init_database():
    """Inicializa la base de datos desde el schema"""
    
    # Rutas
    project_root = Path(__file__).parent.parent
    schema_path = project_root / 'sql' / 'schema_final_completo.sql'
    db_path = project_root / 'data' / 'gestion_rrhh.db'
    
    # Verificar que existe el schema
    if not schema_path.exists():
        print(f"❌ ERROR: No se encuentra {schema_path}")
        return False
    
    # Crear directorio data si no existe
    db_path.parent.mkdir(exist_ok=True)
    
    # Leer schema
    print(f"📖 Leyendo schema desde {schema_path}...")
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    # Crear base de datos
    print(f"💾 Creando base de datos en {db_path}...")
    try:
        conn = sqlite3.connect(db_path)
        conn.executescript(schema_sql)
        conn.close()
        print("✅ Base de datos creada exitosamente!")
        return True
    except sqlite3.Error as e:
        print(f"❌ ERROR al crear base de datos: {e}")
        return False

if __name__ == '__main__':
    init_database()
```

Ejecuta:
```bash
python3 python/init_database.py
```

### 5.2 Verificar que la BD se creó

```bash
# Verificar que existe
ls -lh data/gestion_rrhh.db

# Ver tablas
sqlite3 data/gestion_rrhh.db ".tables"
```

Deberías ver:
```
cambio_transaccion            dispositivos
cambio_transaccion_detalle    error_patterns
cambio_validacion             inasistencias
capacitaciones                menu
capacitaciones_dispositivos   planificacion
capacitaciones_participantes  saldos
certificados                  system_errors
configuracion                 turnos
convocatoria                  vista_agentes_capacitados
convocatoria_historial        vista_cambios_pendientes
datos_personales              ...
descansos
dias
disponibilidad
```

---

## ✅ PASO 6: VERIFICAR INSTALACIÓN

### 6.1 Ejecutar script de verificación

```bash
python3 python/verificar_sistema.py data/gestion_rrhh.db
```

**Salida esperada:**

```
======================================================================
  VERIFICACIÓN SISTEMA RRHH v2.0 FINAL
======================================================================
Base de datos: data/gestion_rrhh.db
Fecha: 2025-12-09 ...

======================================================================
  1. ESTRUCTURA DE BASE DE DATOS
======================================================================
  ✓ Tablas creadas: OK (esperado: 19, encontrado: 19)
  ✓ Vistas creadas: OK (esperado: 11, encontrado: 11)
  ✓ Triggers creados: OK (esperado: 13, encontrado: 13)
  ✓ Índices creados: OK (esperado: 60+, encontrado: 63)

...

======================================================================
  RESULTADO FINAL
======================================================================

  🎉 ¡SISTEMA VERIFICADO EXITOSAMENTE!
  ✅ Todos los componentes están operativos
  ✅ El sistema está listo para usar
```

### 6.2 Ver base de datos en VSCode

**Opción A: Extensión SQLite**

1. Presiona `Ctrl+Shift+P`
2. Escribe: "SQLite: Open Database"
3. Selecciona: `data/gestion_rrhh.db`
4. Explora las tablas en la barra lateral

**Opción B: SQLTools**

1. Click en el ícono de SQLTools en la barra lateral
2. Click en "RRHH Database"
3. Click en "Connect"
4. Explora tablas, ejecuta queries

---

## 🧪 PASO 7: PRIMERA PRUEBA

### 7.1 Crear script de prueba

Crea `python/test_basico.py`:

```python
#!/usr/bin/env python3
"""
Test básico del sistema
"""
import sqlite3
from pathlib import Path

def test_basico():
    """Prueba básica del sistema"""
    
    # Conectar a BD
    db_path = Path(__file__).parent.parent / 'data' / 'gestion_rrhh.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("="*70)
    print("TEST BÁSICO DEL SISTEMA")
    print("="*70)
    
    # 1. Ver configuración
    print("\n1. CONFIGURACIÓN DEL SISTEMA:")
    cursor.execute("SELECT * FROM configuracion")
    for row in cursor.fetchall():
        print(f"   • {row['clave']}: {row['valor']}")
    
    # 2. Ver salud del sistema
    print("\n2. SALUD DEL SISTEMA:")
    cursor.execute("SELECT * FROM vista_salud_sistema")
    salud = cursor.fetchone()
    print(f"   • Estado: {salud['estado_sistema']}")
    print(f"   • Errores 24h: {salud['errores_24h']}")
    print(f"   • Errores semana: {salud['errores_semana']}")
    print(f"   • Tasa resolución: {salud['tasa_resolucion_porcentaje']}%")
    
    # 3. Agregar un agente de prueba
    print("\n3. AGREGANDO AGENTE DE PRUEBA:")
    try:
        cursor.execute("""
            INSERT INTO datos_personales 
            (nombre, apellido, dni, fecha_nacimiento, email)
            VALUES (?, ?, ?, ?, ?)
        """, ('Juan', 'Pérez', '12345678', '1990-01-01', 'juan@ejemplo.com'))
        conn.commit()
        
        id_agente = cursor.lastrowid
        print(f"   ✅ Agente creado con ID: {id_agente}")
        
        # Verificar
        cursor.execute("""
            SELECT nombre, apellido, email 
            FROM datos_personales 
            WHERE id_agente = ?
        """, (id_agente,))
        agente = cursor.fetchone()
        print(f"   • Nombre: {agente['nombre']} {agente['apellido']}")
        print(f"   • Email: {agente['email']}")
        
    except sqlite3.Error as e:
        print(f"   ❌ Error: {e}")
    
    # 4. Listar tablas vacías
    print("\n4. ESTADO DE TABLAS:")
    tablas = [
        'datos_personales', 'dispositivos', 'dias', 
        'turnos', 'convocatoria', 'capacitaciones'
    ]
    for tabla in tablas:
        cursor.execute(f"SELECT COUNT(*) as n FROM {tabla}")
        count = cursor.fetchone()['n']
        print(f"   • {tabla}: {count} registro(s)")
    
    print("\n" + "="*70)
    print("TEST COMPLETADO ✅")
    print("="*70)
    
    conn.close()

if __name__ == '__main__':
    test_basico()
```

### 7.2 Ejecutar el test

```bash
python3 python/test_basico.py
```

### 7.3 Consultar la BD con SQL

En terminal integrada:

```bash
sqlite3 data/gestion_rrhh.db
```

Prueba estos comandos:

```sql
-- Ver configuración
SELECT * FROM configuracion;

-- Ver agentes
SELECT * FROM datos_personales;

-- Ver salud del sistema
SELECT * FROM vista_salud_sistema;

-- Ver vistas disponibles
SELECT name FROM sqlite_master WHERE type='view';

-- Salir
.quit
```

---

## ⚙️ CONFIGURACIÓN OPCIONAL

### 1. Snippets de código

Crea `.vscode/python.code-snippets`:

```json
{
    "Conectar Base de Datos": {
        "prefix": "dbconnect",
        "body": [
            "import sqlite3",
            "from pathlib import Path",
            "",
            "db_path = Path(__file__).parent.parent / 'data' / 'gestion_rrhh.db'",
            "conn = sqlite3.connect(db_path)",
            "conn.row_factory = sqlite3.Row",
            "cursor = conn.cursor()",
            "",
            "# Tu código aquí",
            "",
            "conn.close()"
        ],
        "description": "Template para conectar a la base de datos"
    },
    
    "Query con manejo de errores": {
        "prefix": "dbquery",
        "body": [
            "try:",
            "    cursor.execute(\"\"\"",
            "        ${1:SELECT * FROM tabla}",
            "    \"\"\")",
            "    results = cursor.fetchall()",
            "    for row in results:",
            "        print(row)",
            "except sqlite3.Error as e:",
            "    print(f'Error en query: {e}')"
        ],
        "description": "Query con manejo de errores"
    }
}
```

### 2. Launch configurations para debugging

Crea `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Verificar Sistema",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/python/verificar_sistema.py",
            "args": ["${workspaceFolder}/data/gestion_rrhh.db"],
            "console": "integratedTerminal"
        },
        {
            "name": "Python: Test Básico",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/python/test_basico.py",
            "console": "integratedTerminal"
        },
        {
            "name": "Python: Archivo Actual",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal"
        }
    ]
}
```

**Usar:** Presiona `F5` para ejecutar con debugger

### 3. Script de backup automático

Crea `python/backup_automatico.py`:

```python
#!/usr/bin/env python3
"""
Backup automático de la base de datos
"""
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

def backup_database():
    """Crea backup de la base de datos"""
    
    project_root = Path(__file__).parent.parent
    source_db = project_root / 'data' / 'gestion_rrhh.db'
    backup_dir = project_root / 'backups'
    
    # Crear directorio si no existe
    backup_dir.mkdir(exist_ok=True)
    
    # Nombre con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f'gestion_rrhh_{timestamp}.db'
    
    print(f"📦 Creando backup...")
    print(f"   Origen: {source_db}")
    print(f"   Destino: {backup_file}")
    
    # Backup usando SQLite API
    try:
        source = sqlite3.connect(source_db)
        backup = sqlite3.connect(backup_file)
        source.backup(backup)
        backup.close()
        source.close()
        
        size = backup_file.stat().st_size / 1024  # KB
        print(f"✅ Backup creado: {backup_file.name} ({size:.1f} KB)")
        return True
        
    except Exception as e:
        print(f"❌ Error al crear backup: {e}")
        return False

if __name__ == '__main__':
    backup_database()
```

### 4. Configurar Jupyter Notebook (opcional)

```bash
pip install jupyter ipykernel

# Agregar kernel del venv
python -m ipykernel install --user --name=rrhh-venv --display-name="RRHH (Python 3)"
```

Crea `notebooks/exploracion.ipynb` para análisis interactivo.

---

## 🔍 SOLUCIÓN DE PROBLEMAS

### Error: "command not found: sqlite3"

**Linux:**
```bash
sudo apt-get install sqlite3
```

**Mac:**
```bash
brew install sqlite3
```

**Windows:**
Descargar desde [sqlite.org/download.html](https://sqlite.org/download.html)

### Error: "No module named 'sqlite3'"

Python no incluye sqlite3. Reinstala Python con soporte SQLite.

### Error: "Permission denied" al crear archivos

```bash
# Dar permisos
chmod +x python/*.py
chmod +x *.sh
```

### VSCode no detecta el intérprete Python

1. `Ctrl+Shift+P` → "Python: Select Interpreter"
2. Si no aparece el venv, reinicia VSCode
3. Verifica que el venv existe: `ls venv/bin/python`

### La base de datos está bloqueada

```bash
# Cerrar todas las conexiones
fuser data/gestion_rrhh.db  # Linux
lsof data/gestion_rrhh.db    # Mac

# O simplemente cerrar VSCode y SQLite browser
```

---

## ✅ CHECKLIST FINAL

- [ ] VSCode instalado y configurado
- [ ] Python 3.8+ instalado
- [ ] Extensiones de VSCode instaladas
- [ ] Estructura de carpetas creada
- [ ] Archivos copiados a sus carpetas
- [ ] Entorno virtual creado y activado
- [ ] Dependencias instaladas
- [ ] Base de datos creada
- [ ] Verificación ejecutada exitosamente
- [ ] Test básico ejecutado
- [ ] Puedo consultar la BD desde VSCode

---

## 🎉 ¡LISTO!

Tu entorno está configurado. Ahora puedes:

1. **Consultar la BD:** SQLTools en barra lateral
2. **Ejecutar scripts:** Terminal integrada
3. **Debuggear:** Presiona F5
4. **Crear backups:** `python3 python/backup_automatico.py`
5. **Explorar datos:** Jupyter notebooks

**Próximos pasos:**
- Lee `docs/GUIA_INSTALACION_FINAL.md`
- Carga datos iniciales (dispositivos, días, turnos)
- Empieza a desarrollar funcionalidades

---

## 📚 Referencias Rápidas

### Atajos de VSCode útiles:

- `Ctrl+ñ` - Toggle terminal
- `Ctrl+Shift+P` - Command palette
- `F5` - Start debugging
- `Ctrl+F5` - Run without debugging
- `Ctrl+K Ctrl+S` - Keyboard shortcuts
- `Ctrl+B` - Toggle sidebar

### Comandos SQLite útiles:

```sql
.tables           -- Listar tablas
.schema tabla     -- Ver estructura de tabla
.mode column      -- Formato columnar
.headers on       -- Mostrar headers
.output file.txt  -- Guardar output a archivo
```

---

**Autor:** Pablo - Data Analyst  
**Última actualización:** 2025-12-09  
**Versión:** 1.0
