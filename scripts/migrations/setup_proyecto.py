#!/usr/bin/env python3
"""
Script de Inicialización Completa del Proyecto
Automatiza toda la configuración inicial del sistema RRHH
"""

import sqlite3
import os
import sys
from pathlib import Path
from datetime import date, timedelta
import shutil

class ProyectoInitializer:
    """Inicializador completo del proyecto"""
    
    def __init__(self, project_root=None):
        if project_root:
            self.root = Path(project_root)
        else:
            self.root = Path.cwd()
        
        self.dirs = {
            'sql': self.root / 'sql',
            'python': self.root / 'python',
            'data': self.root / 'data',
            'logs': self.root / 'logs',
            'backups': self.root / 'backups',
            'config': self.root / 'config',
            'docs': self.root / 'docs',
            'tests': self.root / 'tests'
        }
        
        self.db_path = self.dirs['data'] / 'gestion_rrhh.db'
        self.schema_path = self.dirs['sql'] / 'schema_final_completo.sql'
    
    def print_header(self, text):
        """Imprime encabezado formateado"""
        print("\n" + "="*70)
        print(f"  {text}")
        print("="*70)
    
    def print_step(self, step, total, text):
        """Imprime paso actual"""
        print(f"\n[{step}/{total}] {text}")
    
    def print_success(self, text):
        """Imprime mensaje de éxito"""
        print(f"  ✓ {text}")
    
    def print_error(self, text):
        """Imprime mensaje de error"""
        print(f"  ✗ {text}")
    
    def print_warning(self, text):
        """Imprime advertencia"""
        print(f"  ⚠ {text}")
    
    def crear_estructura(self):
        """Crea estructura de carpetas"""
        self.print_step(1, 6, "Creando estructura de carpetas...")
        
        for name, path in self.dirs.items():
            if path.exists():
                self.print_warning(f"{name}/ ya existe")
            else:
                path.mkdir(parents=True, exist_ok=True)
                self.print_success(f"{name}/ creado")
    
    def crear_base_datos(self):
        """Crea la base de datos desde el schema"""
        self.print_step(2, 6, "Creando base de datos...")
        
        # Verificar schema
        if not self.schema_path.exists():
            self.print_error(f"Schema no encontrado: {self.schema_path}")
            self.print_warning("Asegúrate de copiar schema_final_completo.sql a sql/")
            return False
        
        # Crear BD
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            conn = sqlite3.connect(self.db_path)
            conn.executescript(schema_sql)
            conn.close()
            
            size = self.db_path.stat().st_size / 1024  # KB
            self.print_success(f"Base de datos creada: {self.db_path.name} ({size:.1f} KB)")
            return True
            
        except sqlite3.Error as e:
            self.print_error(f"Error al crear BD: {e}")
            return False
        except Exception as e:
            self.print_error(f"Error inesperado: {e}")
            return False
    
    def generar_dias(self, dias=90):
        """Genera tabla de días automáticamente"""
        self.print_step(3, 6, f"Generando {dias} días en calendario...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            start_date = date.today()
            count = 0
            
            for i in range(dias):
                current_date = start_date + timedelta(days=i)
                
                try:
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
                    if cursor.rowcount > 0:
                        count += 1
                except sqlite3.IntegrityError:
                    pass  # Ya existe
            
            conn.commit()
            conn.close()
            
            self.print_success(f"{count} días generados")
            return True
            
        except Exception as e:
            self.print_error(f"Error al generar días: {e}")
            return False
    
    def crear_datos_ejemplo(self):
        """Crea datos de ejemplo"""
        self.print_step(4, 6, "Creando datos de ejemplo...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Dispositivos de ejemplo
            dispositivos = [
                ('Sala Papel', 1),
                ('Sala Textil', 2),
                ('Sala Madera', 3),
                ('Café Literario', 0),
                ('Tienda del Molino', 0),
                ('Laboratorio Observación', 1)
            ]
            
            count_disp = 0
            for nombre, piso in dispositivos:
                try:
                    cursor.execute("""
                        INSERT INTO dispositivos (nombre_dispositivo, piso_dispositivo)
                        VALUES (?, ?)
                    """, (nombre, piso))
                    count_disp += 1
                except sqlite3.IntegrityError:
                    pass
            
            # Turnos base
            turnos = [
                # Lunes a Viernes - Mañana
                (1, 'mañana', '09:00', '13:00', 4.0),
                (2, 'mañana', '09:00', '13:00', 4.0),
                (3, 'mañana', '09:00', '13:00', 4.0),
                (4, 'mañana', '09:00', '13:00', 4.0),
                (5, 'mañana', '09:00', '13:00', 4.0),
                # Lunes a Viernes - Tarde
                (1, 'tarde', '14:00', '18:00', 4.0),
                (2, 'tarde', '14:00', '18:00', 4.0),
                (3, 'tarde', '14:00', '18:00', 4.0),
                (4, 'tarde', '14:00', '18:00', 4.0),
                (5, 'tarde', '14:00', '18:00', 4.0),
                # Sábado
                (6, 'apertura_publico', '10:00', '14:00', 4.0),
                # Descanso
                (0, 'descanso', '00:00', '00:00', 0.0),
            ]
            
            count_turnos = 0
            for numero_dia, tipo, inicio, fin, horas in turnos:
                try:
                    cursor.execute("""
                        INSERT INTO turnos 
                        (numero_dia_semana, tipo_turno, hora_inicio, hora_fin, cant_horas)
                        VALUES (?, ?, ?, ?, ?)
                    """, (numero_dia, tipo, inicio, fin, horas))
                    count_turnos += 1
                except sqlite3.IntegrityError:
                    pass
            
            # Agente de ejemplo
            try:
                cursor.execute("""
                    INSERT INTO datos_personales 
                    (nombre, apellido, dni, fecha_nacimiento, email, telefono)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    'Usuario', 'Ejemplo', '00000000', '1990-01-01', 
                    'ejemplo@sistema.com', '342-0000000'
                ))
                count_agentes = 1
            except sqlite3.IntegrityError:
                count_agentes = 0
            
            conn.commit()
            conn.close()
            
            self.print_success(f"{count_disp} dispositivos creados")
            self.print_success(f"{count_turnos} turnos creados")
            self.print_success(f"{count_agentes} agente de ejemplo creado")
            return True
            
        except Exception as e:
            self.print_error(f"Error al crear datos: {e}")
            return False
    
    def verificar_sistema(self):
        """Verifica que todo esté correcto"""
        self.print_step(5, 6, "Verificando sistema...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Verificar tablas
            cursor.execute("SELECT COUNT(*) as n FROM sqlite_master WHERE type='table'")
            tablas = cursor.fetchone()['n']
            
            if tablas == 19:
                self.print_success(f"Tablas: {tablas}/19")
            else:
                self.print_error(f"Tablas: {tablas}/19 (esperadas: 19)")
            
            # Verificar vistas
            cursor.execute("SELECT COUNT(*) as n FROM sqlite_master WHERE type='view'")
            vistas = cursor.fetchone()['n']
            
            if vistas == 11:
                self.print_success(f"Vistas: {vistas}/11")
            else:
                self.print_warning(f"Vistas: {vistas}/11 (esperadas: 11)")
            
            # Verificar triggers
            cursor.execute("SELECT COUNT(*) as n FROM sqlite_master WHERE type='trigger'")
            triggers = cursor.fetchone()['n']
            
            if triggers == 13:
                self.print_success(f"Triggers: {triggers}/13")
            else:
                self.print_warning(f"Triggers: {triggers}/13 (esperadas: 13)")
            
            # Verificar datos
            cursor.execute("SELECT COUNT(*) as n FROM dispositivos")
            disp = cursor.fetchone()['n']
            self.print_success(f"Dispositivos: {disp}")
            
            cursor.execute("SELECT COUNT(*) as n FROM dias")
            dias = cursor.fetchone()['n']
            self.print_success(f"Días generados: {dias}")
            
            cursor.execute("SELECT COUNT(*) as n FROM turnos")
            turnos = cursor.fetchone()['n']
            self.print_success(f"Turnos: {turnos}")
            
            # Verificar salud
            cursor.execute("SELECT estado_sistema FROM vista_salud_sistema")
            salud = cursor.fetchone()['estado_sistema']
            self.print_success(f"Estado sistema: {salud}")
            
            conn.close()
            return True
            
        except Exception as e:
            self.print_error(f"Error en verificación: {e}")
            return False
    
    def crear_archivos_config(self):
        """Crea archivos de configuración"""
        self.print_step(6, 6, "Creando archivos de configuración...")
        
        # requirements.txt
        requirements = """# Dependencias base
pandas>=1.3.0
plotly>=5.0.0
streamlit>=1.24.0

# Para Google Sheets (opcional)
gspread>=5.0.0
oauth2client>=4.1.3

# Para desarrollo
pytest>=7.0.0
black>=22.0.0
pylint>=2.12.0
"""
        
        req_path = self.root / 'requirements.txt'
        if not req_path.exists():
            req_path.write_text(requirements)
            self.print_success("requirements.txt creado")
        else:
            self.print_warning("requirements.txt ya existe")
        
        # .gitignore
        gitignore = """# Python
__pycache__/
*.pyc
venv/

# Base de datos
data/*.db
data/*.db-journal

# Backups
backups/*.db

# Logs
logs/*.log

# Config sensible
config/credentials.json
.env
"""
        
        git_path = self.root / '.gitignore'
        if not git_path.exists():
            git_path.write_text(gitignore)
            self.print_success(".gitignore creado")
        else:
            self.print_warning(".gitignore ya existe")
        
        return True
    
    def mostrar_resumen(self):
        """Muestra resumen final"""
        self.print_header("INICIALIZACIÓN COMPLETADA")
        
        print(f"""
Proyecto inicializado en: {self.root}

📁 Estructura creada:
   ├── sql/          - Schemas SQL
   ├── python/       - Scripts Python
   ├── data/         - Base de datos ({self.db_path.name})
   ├── logs/         - Logs del sistema
   ├── backups/      - Backups automáticos
   ├── config/       - Configuración
   ├── docs/         - Documentación
   └── tests/        - Tests

✅ Base de datos operativa
✅ {self.db_path}

🚀 Próximos pasos:

1. Activar entorno virtual:
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\\Scripts\\activate    # Windows

2. Instalar dependencias:
   pip install -r requirements.txt

3. Abrir en VSCode:
   code .

4. Verificar sistema:
   python3 python/verificar_sistema.py data/gestion_rrhh.db

5. Consultar BD:
   sqlite3 data/gestion_rrhh.db
   > SELECT * FROM vista_salud_sistema;

📚 Documentación:
   - docs/GUIA_INSTALACION_FINAL.md
   - docs/README_PRINCIPAL.md
   - docs/CONFIGURACION_VSCODE_PASO_A_PASO.md
""")
    
    def run(self, crear_datos=True):
        """Ejecuta la inicialización completa"""
        self.print_header("INICIALIZADOR DEL PROYECTO RRHH v2.0")
        
        print(f"Directorio del proyecto: {self.root}")
        print(f"Base de datos: {self.db_path}")
        
        # Confirmar
        if sys.stdin.isatty():  # Si es interactivo
            respuesta = input("\n¿Continuar con la inicialización? (s/N): ")
            if respuesta.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
                print("Inicialización cancelada.")
                return False
        
        # Pasos
        success = True
        success &= self.crear_estructura()
        success &= self.crear_base_datos()
        
        if crear_datos:
            success &= self.generar_dias(90)
            success &= self.crear_datos_ejemplo()
        
        success &= self.verificar_sistema()
        success &= self.crear_archivos_config()
        
        if success:
            self.mostrar_resumen()
            return True
        else:
            self.print_error("La inicialización tuvo algunos errores.")
            return False


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Inicializa el proyecto RRHH v2.0'
    )
    parser.add_argument(
        '--dir',
        help='Directorio del proyecto (default: directorio actual)',
        default=None
    )
    parser.add_argument(
        '--no-datos',
        action='store_true',
        help='No crear datos de ejemplo'
    )
    
    args = parser.parse_args()
    
    # Inicializar
    initializer = ProyectoInitializer(args.dir)
    success = initializer.run(crear_datos=not args.no_datos)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
