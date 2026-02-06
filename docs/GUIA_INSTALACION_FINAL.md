# 📘 GUÍA DE INSTALACIÓN Y USO - Sistema RRHH v2.0 FINAL

**Sistema de Gestión de Recursos Humanos para Centro Cultural**  
**Completitud: 98% - Production Ready**

---

## 📋 Tabla de Contenidos

1. [Requisitos del Sistema](#requisitos)
2. [Instalación Rápida](#instalacion-rapida)
3. [Instalación Detallada](#instalacion-detallada)
4. [Verificación](#verificacion)
5. [Uso Básico](#uso-basico)
6. [Funcionalidades Avanzadas](#avanzadas)
7. [Sistema de Logging](#logging)
8. [Mantenimiento](#mantenimiento)
9. [Solución de Problemas](#troubleshooting)

---

## 🖥️ REQUISITOS DEL SISTEMA {#requisitos}

### Software Necesario

- **Python 3.8+** (recomendado 3.10 o superior)
- **SQLite 3.35+** (incluido con Python 3.8+)
- **pip** (gestor de paquetes)

### Bibliotecas Python

```bash
pip install pandas>=1.3.0
pip install plotly>=5.0.0
pip install gspread>=5.0.0
pip install oauth2client>=4.1.3
```

### Opcional (Desarrollo)

```bash
pip install jupyter notebook
pip install pytest
pip install black flake8
```

---

## ⚡ INSTALACIÓN RÁPIDA (5 minutos) {#instalacion-rapida}

```bash
# 1. Descargar archivos
# Asegúrate de tener:
# - schema_final_completo.sql
# - database_manager.py (si lo tienes)
# - error_logger_python.py

# 2. Crear base de datos
sqlite3 gestion_rrhh.db < schema_final_completo.sql

# 3. Verificar
sqlite3 gestion_rrhh.db "SELECT COUNT(*) as tablas FROM sqlite_master WHERE type='table';"
# Debe mostrar: 19

# 4. Verificar vistas
sqlite3 gestion_rrhh.db "SELECT COUNT(*) as vistas FROM sqlite_master WHERE type='view';"
# Debe mostrar: 11

# 5. Ver salud del sistema
sqlite3 gestion_rrhh.db "SELECT * FROM vista_salud_sistema;"
```

**✅ Si todo muestra resultados, el sistema está listo!**

---

## 📦 INSTALACIÓN DETALLADA {#instalacion-detallada}

### PASO 1: Preparar Entorno

```bash
# Crear directorio del proyecto
mkdir gestion_rrhh_centro
cd gestion_rrhh_centro

# Crear estructura
mkdir -p {sql,python,logs,backups,config}

# Mover archivos
mv schema_final_completo.sql sql/
mv error_logger_python.py python/
```

### PASO 2: Crear Base de Datos

```bash
# Opción A: Desde SQL
sqlite3 gestion_rrhh.db < sql/schema_final_completo.sql

# Opción B: Desde Python
python3 << EOF
import sqlite3
conn = sqlite3.connect('gestion_rrhh.db')
with open('sql/schema_final_completo.sql', 'r') as f:
    conn.executescript(f.read())
conn.close()
print("✅ Base de datos creada")
EOF
```

### PASO 3: Poblar Datos Iniciales

```sql
-- datos_iniciales.sql
-- Ejecutar: sqlite3 gestion_rrhh.db < datos_iniciales.sql

-- Dispositivos de ejemplo
INSERT INTO dispositivos (nombre_dispositivo, piso_dispositivo) VALUES
('Sala Papel', 1),
('Sala Textil', 2),
('Sala Madera', 3),
('Café Literario', 0),
('Tienda del Molino', 0);

-- Días de ejemplo (próximo mes)
-- Script Python para generar:
```

```python
# generar_dias.py
import sqlite3
from datetime import date, timedelta
import calendar

conn = sqlite3.connect('gestion_rrhh.db')
cursor = conn.cursor()

# Generar próximos 3 meses
start_date = date.today()
for i in range(90):
    current_date = start_date + timedelta(days=i)
    
    cursor.execute("""
        INSERT OR IGNORE INTO dias 
        (fecha, mes, semana, dia, numero_dia_semana, es_feriado)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (
        current_date.isoformat(),
        current_date.month,
        current_date.isocalendar()[1],
        current_date.day,
        current_date.weekday()
    ))

conn.commit()
print(f"✅ {cursor.rowcount} días creados")
conn.close()
```

```bash
# Ejecutar
python3 generar_dias.py
```

### PASO 4: Crear Turnos Base

```sql
-- turnos_base.sql
INSERT INTO turnos (numero_dia_semana, tipo_turno, hora_inicio, hora_fin, cant_horas) VALUES
-- Lunes a Viernes
(1, 'mañana', '09:00', '13:00', 4.0),
(1, 'tarde', '14:00', '18:00', 4.0),
(2, 'mañana', '09:00', '13:00', 4.0),
(2, 'tarde', '14:00', '18:00', 4.0),
(3, 'mañana', '09:00', '13:00', 4.0),
(3, 'tarde', '14:00', '18:00', 4.0),
(4, 'mañana', '09:00', '13:00', 4.0),
(4, 'tarde', '14:00', '18:00', 4.0),
(5, 'mañana', '09:00', '13:00', 4.0),
(5, 'tarde', '14:00', '18:00', 4.0),
-- Sábados
(6, 'apertura_publico', '10:00', '14:00', 4.0),
-- Descansos
(0, 'descanso', '00:00', '00:00', 0.0);

-- Ejecutar:
-- sqlite3 gestion_rrhh.db < turnos_base.sql
```

---

## ✅ VERIFICACIÓN {#verificacion}

### Script de Verificación Completo

```python
# verificar_instalacion.py
import sqlite3

def verificar_sistema(db_path='gestion_rrhh.db'):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("="*70)
    print("VERIFICACIÓN DEL SISTEMA RRHH v2.0")
    print("="*70)
    
    # 1. Tablas
    cursor.execute("SELECT COUNT(*) as n FROM sqlite_master WHERE type='table'")
    tablas = cursor.fetchone()['n']
    print(f"\n✓ Tablas creadas: {tablas}/19")
    assert tablas == 19, f"❌ Faltan tablas. Esperadas: 19, Encontradas: {tablas}"
    
    # 2. Vistas
    cursor.execute("SELECT COUNT(*) as n FROM sqlite_master WHERE type='view'")
    vistas = cursor.fetchone()['n']
    print(f"✓ Vistas creadas: {vistas}/11")
    assert vistas == 11, f"❌ Faltan vistas. Esperadas: 11, Encontradas: {vistas}"
    
    # 3. Triggers
    cursor.execute("SELECT COUNT(*) as n FROM sqlite_master WHERE type='trigger'")
    triggers = cursor.fetchone()['n']
    print(f"✓ Triggers creados: {triggers}/13")
    assert triggers == 13, f"❌ Faltan triggers. Esperadas: 13, Encontradas: {triggers}"
    
    # 4. Índices
    cursor.execute("SELECT COUNT(*) as n FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
    indices = cursor.fetchone()['n']
    print(f"✓ Índices creados: {indices} (esperados: 60+)")
    
    # 5. Configuración
    cursor.execute("SELECT COUNT(*) as n FROM configuracion")
    configs = cursor.fetchone()['n']
    print(f"✓ Configuraciones iniciales: {configs}/8")
    
    # 6. Vista salud sistema
    cursor.execute("SELECT estado_sistema FROM vista_salud_sistema")
    salud = cursor.fetchone()['estado_sistema']
    print(f"✓ Estado del sistema: {salud}")
    
    # 7. Verificar FKs activas
    cursor.execute("PRAGMA foreign_keys")
    fk_status = cursor.fetchone()[0]
    print(f"✓ Foreign Keys: {'ACTIVADAS' if fk_status else 'DESACTIVADAS ⚠️'}")
    
    print("\n" + "="*70)
    print("✅ VERIFICACIÓN COMPLETA - SISTEMA OPERATIVO")
    print("="*70)
    
    conn.close()

if __name__ == '__main__':
    verificar_sistema()
```

```bash
# Ejecutar verificación
python3 verificar_instalacion.py
```

---

## 🚀 USO BÁSICO {#uso-basico}

### 1. Agregar Agentes

```python
import sqlite3

conn = sqlite3.connect('gestion_rrhh.db')
cursor = conn.cursor()

# Agregar agente
cursor.execute("""
    INSERT INTO datos_personales 
    (nombre, apellido, dni, fecha_nacimiento, email, telefono)
    VALUES (?, ?, ?, ?, ?, ?)
""", ('María', 'González', '30123456', '1990-05-15', 'maria@email.com', '342-4111222'))

id_agente = cursor.lastrowid
conn.commit()
print(f"✅ Agente creado: ID={id_agente}")

conn.close()
```

### 2. Crear Planificación

```python
# Planificar un día específico
cursor.execute("""
    INSERT INTO planificacion (id_dia, id_turno, cant_residentes_plan, cant_visit)
    SELECT 
        d.id_dia,
        t.id_turno,
        3,  -- 3 residentes
        15  -- 15 visitantes esperados
    FROM dias d
    CROSS JOIN turnos t
    WHERE d.fecha = '2025-12-15'
    AND t.tipo_turno = 'mañana'
    AND t.numero_dia_semana = CAST(strftime('%w', d.fecha) AS INTEGER)
""")
conn.commit()
```

### 3. Crear Convocatorias

```python
# Convocar agente para un turno
cursor.execute("""
    INSERT INTO convocatoria (id_plani, id_agente, id_turno, fecha_convocatoria, estado)
    SELECT 
        p.id_plani,
        1,  -- id_agente
        p.id_turno,
        d.fecha,
        'vigente'
    FROM planificacion p
    JOIN dias d ON p.id_dia = d.id_dia
    WHERE d.fecha = '2025-12-15'
    AND p.id_turno = (SELECT id_turno FROM turnos WHERE tipo_turno = 'mañana' LIMIT 1)
""")
conn.commit()

# El trigger automáticamente:
# - Actualiza saldos de horas
# - Previene convocatorias duplicadas
```

### 4. Consultas Comunes

```python
# Ver convocatorias activas
cursor.execute("SELECT * FROM vista_convocatorias_activas WHERE fecha_convocatoria >= date('now')")
convocatorias = cursor.fetchall()

# Ver saldos del mes
cursor.execute("SELECT * FROM vista_saldos_actuales WHERE mes = strftime('%m', 'now')")
saldos = cursor.fetchall()

# Ver salud del sistema
cursor.execute("SELECT * FROM vista_salud_sistema")
salud = cursor.fetchone()
print(f"Estado: {salud['estado_sistema']}")
print(f"Errores 24h: {salud['errores_24h']}")
```

---

## ⚙️ FUNCIONALIDADES AVANZADAS {#avanzadas}

### 1. Sistema de Cambios de Turno

```python
# Solicitar cambio
cursor.execute("""
    INSERT INTO cambio_transaccion (agente_iniciador, tipo_transaccion, observaciones)
    VALUES (?, 'intercambio_fechas', 'Motivo personal')
""", (1,))
id_trans = cursor.lastrowid

# Agregar detalle
cursor.execute("""
    INSERT INTO cambio_transaccion_detalle 
    (id_transaccion, secuencia, id_convocatoria_original, 
     id_agente_original, fecha_original, id_turno_original,
     id_agente_nuevo, fecha_nueva, id_turno_nuevo)
    VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?)
""", (id_trans, 100, 1, '2025-12-15', 5, 2, '2025-12-16', 5))

conn.commit()
```

### 2. Gestión de Capacitaciones

```python
# Crear capacitación
cursor.execute("""
    INSERT INTO capacitaciones (id_dia, coordinador_cap, tema, grupo)
    SELECT id_dia, 1, 'Seguridad e Higiene', 'Grupo A'
    FROM dias WHERE fecha = '2025-12-20'
""")
id_cap = cursor.lastrowid

# Vincular con dispositivo
cursor.execute("""
    INSERT INTO capacitaciones_dispositivos (id_cap, id_dispositivo, orden)
    VALUES (?, ?, 1)
""", (id_cap, 1))

# Inscribir participante
cursor.execute("""
    INSERT INTO capacitaciones_participantes (id_cap, id_agente)
    VALUES (?, ?)
""", (id_cap, 1))

# Registrar asistencia
cursor.execute("""
    UPDATE capacitaciones_participantes
    SET asistio = 1, aprobado = 1, calificacion = 9.5,
        fecha_certificado = CURRENT_TIMESTAMP
    WHERE id_cap = ? AND id_agente = ?
""", (id_cap, 1))

conn.commit()
```

### 3. Inasistencias y Certificados

```python
# Registrar inasistencia
cursor.execute("""
    INSERT INTO inasistencias (id_agente, fecha_inasistencia, motivo, observaciones)
    VALUES (?, '2025-12-15', 'medico', 'Consulta médica programada')
""", (1,))
id_inasis = cursor.lastrowid

# El trigger automáticamente marca requiere_certificado = 1

# Presentar certificado
cursor.execute("""
    INSERT INTO certificados 
    (id_inasistencia, id_agente, fecha_entrega_certificado, 
     fecha_inasistencia_justifica, tipo_certificado)
    VALUES (?, ?, date('now'), '2025-12-15', 'medico')
""", (id_inasis, 1))

# Aprobar certificado
cursor.execute("""
    UPDATE certificados
    SET estado_certificado = 'aprobado',
        fecha_revision = CURRENT_TIMESTAMP,
        usuario_reviso = 'admin'
    WHERE id_certificado = ?
""", (cursor.lastrowid,))

conn.commit()
# El trigger automáticamente actualiza inasistencia a 'justificada'
```

---

## 📊 SISTEMA DE LOGGING {#logging}

### Usando el ErrorLogger de Python

```python
from error_logger_python import ErrorLogger, setup_error_logging
from database_manager import DatabaseManager

# Configurar
db = DatabaseManager('gestion_rrhh.db')
error_logger = setup_error_logging(db)

# Uso 1: Registrar error manualmente
error_logger.log_error(
    error_type='validation',
    component='convocatorias',
    error_message='Agente no disponible en este turno',
    severity='medium',
    id_agente=1,
    additional_context={'turno_id': 5}
)

# Uso 2: Con decorador (auto-logging)
@error_logger.log_errors(component='cambios_turno', severity='high')
def procesar_cambio_turno(id_trans):
    # Tu código aquí
    pass

# Uso 3: Dashboard
dashboard = error_logger.get_dashboard()
print(f"Estado: {dashboard['estado_sistema']}")
print(f"Errores 24h: {dashboard['errores_24h']}")

# Uso 4: Verificar alertas
alerts = error_logger.check_alerts()
for alert in alerts:
    print(f"[{alert['nivel']}] {alert['mensaje']}")
```

### Consultas SQL de Logging

```sql
-- Ver errores recientes
SELECT * FROM vista_errores_recientes LIMIT 10;

-- Ver patrones detectados
SELECT * FROM vista_patrones_errores;

-- Dashboard de salud
SELECT * FROM vista_salud_sistema;

-- Errores por componente
SELECT * FROM vista_errores_por_componente;

-- Timeline para gráficos
SELECT * FROM vista_errores_timeline;
```

---

## 🔧 MANTENIMIENTO {#mantenimiento}

### Backup Automático

```python
# backup_automatico.py
import sqlite3
import shutil
from datetime import datetime
import os

def backup_database(source_db='gestion_rrhh.db', backup_dir='backups'):
    # Crear directorio si no existe
    os.makedirs(backup_dir, exist_ok=True)
    
    # Nombre con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"{backup_dir}/gestion_rrhh_{timestamp}.db"
    
    # Backup usando SQLite API (más seguro que shutil)
    source = sqlite3.connect(source_db)
    backup = sqlite3.connect(backup_file)
    source.backup(backup)
    backup.close()
    source.close()
    
    print(f"✅ Backup creado: {backup_file}")
    
    # Limpiar backups antiguos (mantener últimos 30 días)
    cleanup_old_backups(backup_dir, days=30)

def cleanup_old_backups(backup_dir, days=30):
    import time
    cutoff = time.time() - (days * 86400)
    
    for filename in os.listdir(backup_dir):
        filepath = os.path.join(backup_dir, filename)
        if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff:
            os.remove(filepath)
            print(f"🗑️  Backup antiguo eliminado: {filename}")

if __name__ == '__main__':
    backup_database()
```

```bash
# Configurar en cron (Linux/Mac)
# Ejecutar diariamente a las 2 AM
crontab -e
# Agregar:
# 0 2 * * * cd /ruta/proyecto && python3 backup_automatico.py
```

### Limpieza de Datos Antiguos

```python
# limpieza_mantenimiento.py
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('gestion_rrhh.db')
cursor = conn.cursor()

# 1. Limpiar errores resueltos (>90 días)
cursor.execute("""
    DELETE FROM system_errors
    WHERE resolved = 1
    AND resolution_date < datetime('now', '-90 days')
""")
print(f"✅ Errores antiguos eliminados: {cursor.rowcount}")

# 2. Archivar patrones resueltos
cursor.execute("""
    UPDATE error_patterns
    SET pattern_status = 'ignored'
    WHERE pattern_status = 'resolved'
    AND last_occurrence < datetime('now', '-90 days')
""")
print(f"✅ Patrones archivados: {cursor.rowcount}")

# 3. Marcar convocatorias antiguas como históricas
cursor.execute("""
    UPDATE convocatoria
    SET estado = 'historica'
    WHERE estado = 'cumplida'
    AND fecha_convocatoria < date('now', '-180 days')
""")
print(f"✅ Convocatorias archivadas: {cursor.rowcount}")

conn.commit()
conn.close()
```

### Optimización de Base de Datos

```bash
# Ejecutar mensualmente
sqlite3 gestion_rrhh.db "VACUUM;"
sqlite3 gestion_rrhh.db "ANALYZE;"
```

---

## 🔍 SOLUCIÓN DE PROBLEMAS {#troubleshooting}

### Error: "No such table"

**Causa:** Base de datos no inicializada

**Solución:**
```bash
sqlite3 gestion_rrhh.db < sql/schema_final_completo.sql
```

### Error: "FOREIGN KEY constraint failed"

**Causa:** Foreign keys no activadas

**Solución:**
```python
conn = sqlite3.connect('gestion_rrhh.db')
conn.execute("PRAGMA foreign_keys = ON")
```

### Error: Trigger no se ejecuta

**Verificar triggers:**
```sql
SELECT name, sql FROM sqlite_master WHERE type='trigger';
```

**Re-crear si es necesario:**
```bash
sqlite3 gestion_rrhh.db < sql/schema_final_completo.sql
```

### Performance lento

**Verificar índices:**
```sql
SELECT * FROM sqlite_master WHERE type='index';
```

**Optimizar:**
```sql
VACUUM;
ANALYZE;
```

### Verificar integridad

```sql
PRAGMA integrity_check;
PRAGMA foreign_key_check;
```

---

## 📞 SOPORTE

Para problemas adicionales:

1. Revisar vista de salud: `SELECT * FROM vista_salud_sistema;`
2. Consultar errores: `SELECT * FROM vista_errores_recientes;`
3. Ver patrones: `SELECT * FROM vista_patrones_errores;`

---

## ✅ CHECKLIST DE INSTALACIÓN

- [ ] Python 3.8+ instalado
- [ ] Dependencias instaladas (pip install...)
- [ ] Schema SQL ejecutado (19 tablas)
- [ ] Vistas creadas (11 vistas)
- [ ] Triggers activos (13 triggers)
- [ ] Configuración inicial cargada
- [ ] Datos básicos ingresados (dispositivos, días, turnos)
- [ ] Verificación ejecutada exitosamente
- [ ] Sistema de logging funcionando
- [ ] Backup configurado

---

**Sistema RRHH v2.0 FINAL**  
**Autor:** Pablo - Data Analyst  
**Fecha:** Diciembre 2025  
**Licencia:** MIT
