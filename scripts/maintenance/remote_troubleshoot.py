#!/usr/bin/env python3
"""
REMOTE TROUBLESHOOTER v2 - Diagnóstico Remoto para Sistema RRHH
================================================================

Versión corregida con mejor manejo de errores y debugging.

Autor: Pablo - Data Analyst
Fecha: Diciembre 2025
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import traceback

# Intentar importar psycopg2
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("⚠️  psycopg2 no instalado. Instalar con: pip install psycopg2-binary")

# Colores para terminal
class Color:
    VERDE = '\033[92m'
    ROJO = '\033[91m'
    AMARILLO = '\033[93m'
    AZUL = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    FIN = '\033[0m'
    BOLD = '\033[1m'


@dataclass
class DiagnosticResult:
    """Resultado de un diagnóstico"""
    name: str
    status: str  # 'ok', 'warning', 'error'
    message: str
    details: Optional[Dict] = None
    action_required: bool = False
    suggested_action: Optional[str] = None


class RemoteTroubleshooter:
    """
    Herramienta de diagnóstico remoto para el sistema RRHH
    """
    
    def __init__(self, env_path: str = None, debug: bool = False):
        """
        Inicializa el troubleshooter
        
        Args:
            env_path: Ruta al archivo .env (opcional)
            debug: Activar modo debug para ver errores completos
        """
        self.conn = None
        self.connected = False
        self.env_path = env_path
        self.config = {}
        self.debug = debug
        
        # Cargar configuración
        self._load_config()
    
    def _load_config(self):
        """Carga configuración de Supabase desde .env"""
        try:
            from dotenv import load_dotenv
            if self.env_path:
                load_dotenv(self.env_path)
            else:
                load_dotenv()
        except ImportError:
            pass
        
        self.config = {
            'host': os.getenv('SUPABASE_DB_HOST', 'aws-0-sa-east-1.pooler.supabase.com'),
            'port': os.getenv('SUPABASE_DB_PORT', '6543'),
            'database': os.getenv('SUPABASE_DB_NAME', 'postgres'),
            'user': os.getenv('SUPABASE_DB_USER', ''),
            'password': os.getenv('SUPABASE_DB_PASSWORD', ''),
        }
    
    def _log_error(self, context: str, error: Exception):
        """Log de errores con contexto"""
        print(f"{Color.ROJO}❌ Error en {context}: {error}{Color.FIN}")
        if self.debug:
            traceback.print_exc()
    
    def connect(self) -> bool:
        """Establece conexión con Supabase"""
        if not PSYCOPG2_AVAILABLE:
            print(f"{Color.ROJO}❌ psycopg2 no disponible{Color.FIN}")
            return False
        
        if not self.config['user'] or not self.config['password']:
            print(f"{Color.ROJO}❌ Credenciales de Supabase no configuradas{Color.FIN}")
            print("   Configura las variables de entorno:")
            print("   - SUPABASE_DB_HOST")
            print("   - SUPABASE_DB_USER") 
            print("   - SUPABASE_DB_PASSWORD")
            return False
        
        try:
            print(f"{Color.CYAN}🔌 Conectando a Supabase...{Color.FIN}")
            self.conn = psycopg2.connect(
                host=self.config['host'],
                port=self.config['port'],
                dbname=self.config['database'],
                user=self.config['user'],
                password=self.config['password'],
                sslmode='require',
                connect_timeout=15
            )
            self.conn.autocommit = False
            self.connected = True
            
            print(f"{Color.VERDE}✅ Conexión establecida{Color.FIN}")
            return True
            
        except Exception as e:
            self._log_error("connect", e)
            self.connected = False
            return False
    
    def disconnect(self):
        """Cierra la conexión"""
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            self.connected = False
            print(f"{Color.CYAN}🔌 Conexión cerrada{Color.FIN}")
    
    def _execute(self, sql: str, params: tuple = None) -> List[Dict]:
        """Ejecuta query y retorna resultados como lista de dicts"""
        if not self.connected:
            raise ConnectionError("No hay conexión a Supabase")
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, params)
                if cursor.description:
                    return [dict(row) for row in cursor.fetchall()]
                return []
        except Exception as e:
            self._log_error("_execute", e)
            # Intentar rollback para limpiar estado
            try:
                self.conn.rollback()
            except:
                pass
            raise
    
    def _execute_safe(self, sql: str, params: tuple = None, default=None) -> Any:
        """Ejecuta query de forma segura, retornando default en caso de error"""
        try:
            return self._execute(sql, params)
        except Exception as e:
            if self.debug:
                self._log_error("_execute_safe", e)
            return default if default is not None else []
    
    def _execute_write(self, sql: str, params: tuple = None) -> int:
        """Ejecuta query de escritura"""
        if not self.connected:
            raise ConnectionError("No hay conexión a Supabase")
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, params)
                affected = cursor.rowcount
                self.conn.commit()
                return affected
        except Exception as e:
            self._log_error("_execute_write", e)
            try:
                self.conn.rollback()
            except:
                pass
            raise
    
    # ========================================================================
    # DIAGNÓSTICOS DEL SISTEMA
    # ========================================================================
    
    def get_system_status(self) -> Dict:
        """Obtiene estado general del sistema"""
        if not self.connected:
            return {'error': 'No conectado', 'health': 'error'}
        
        status = {
            'timestamp': datetime.now().isoformat(),
            'connection': 'ok',
            'tables': {},
            'recent_activity': {},
            'health': 'unknown'
        }
        
        # Contar registros en tablas principales
        tables = [
            'datos_personales', 'dispositivos', 'turnos', 'dias',
            'convocatoria', 'planificacion', 'menu', 'saldos',
            'inasistencias', 'certificados', 'system_errors'
        ]
        
        for table in tables:
            result = self._execute_safe(f"SELECT COUNT(*) as count FROM {table}")
            status['tables'][table] = result[0]['count'] if result else 'error'
        
        # Actividad reciente
        result = self._execute_safe("""
            SELECT COUNT(*) as count 
            FROM convocatoria 
            WHERE fecha_convocatoria >= CURRENT_DATE - INTERVAL '7 days'
        """)
        status['recent_activity']['convocatorias_7d'] = result[0]['count'] if result else 0
        
        result = self._execute_safe("""
            SELECT COUNT(*) as count 
            FROM inasistencias 
            WHERE fecha_inasistencia >= CURRENT_DATE - INTERVAL '7 days'
        """)
        status['recent_activity']['inasistencias_7d'] = result[0]['count'] if result else 0
        
        # Errores no resueltos
        result = self._execute_safe("""
            SELECT COUNT(*) as count 
            FROM system_errors 
            WHERE resolved = false
        """)
        errores = result[0]['count'] if result else 0
        status['recent_activity']['errores_pendientes'] = errores
        
        # Determinar salud
        if errores > 10:
            status['health'] = 'critical'
        elif errores > 0:
            status['health'] = 'warning'
        else:
            status['health'] = 'healthy'
        
        return status
    
    def diagnose_common_issues(self) -> List[DiagnosticResult]:
        """Ejecuta diagnóstico de problemas comunes"""
        if not self.connected:
            return [DiagnosticResult(
                name='Conexión',
                status='error',
                message='No hay conexión a Supabase',
                action_required=True
            )]
        
        results = []
        
        # 1. Convocatorias duplicadas
        try:
            duplicates = self._execute_safe("""
                SELECT id_agente, fecha_convocatoria, COUNT(*) as count
                FROM convocatoria
                WHERE estado = 'vigente'
                GROUP BY id_agente, fecha_convocatoria
                HAVING COUNT(*) > 1
            """, default=[])
            
            if duplicates:
                results.append(DiagnosticResult(
                    name='Convocatorias Duplicadas',
                    status='error',
                    message=f'{len(duplicates)} agente(s) con convocatorias duplicadas',
                    action_required=True,
                    suggested_action='fix_duplicate_convocatorias()'
                ))
            else:
                results.append(DiagnosticResult(
                    name='Convocatorias Duplicadas',
                    status='ok',
                    message='No hay convocatorias duplicadas'
                ))
        except Exception as e:
            results.append(DiagnosticResult(
                name='Convocatorias Duplicadas',
                status='error',
                message=f'Error en diagnóstico: {e}'
            ))
        
        # 2. Inasistencias pendientes
        try:
            pending = self._execute_safe("""
                SELECT COUNT(*) as count
                FROM inasistencias
                WHERE estado = 'pendiente'
                AND requiere_certificado = true
                AND fecha_inasistencia < CURRENT_DATE - INTERVAL '7 days'
            """, default=[])
            
            count = pending[0]['count'] if pending else 0
            if count > 0:
                results.append(DiagnosticResult(
                    name='Inasistencias Pendientes',
                    status='warning',
                    message=f'{count} inasistencia(s) pendiente(s) >7 días',
                    action_required=True
                ))
            else:
                results.append(DiagnosticResult(
                    name='Inasistencias Pendientes',
                    status='ok',
                    message='No hay inasistencias pendientes antiguas'
                ))
        except Exception as e:
            results.append(DiagnosticResult(
                name='Inasistencias Pendientes',
                status='error',
                message=f'Error: {e}'
            ))
        
        # 3. Errores del sistema
        try:
            errors = self._execute_safe("""
                SELECT COUNT(*) as count,
                       COALESCE(SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END), 0) as critical,
                       COALESCE(SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END), 0) as high
                FROM system_errors
                WHERE resolved = false
            """, default=[])
            
            if errors and errors[0]['count'] > 0:
                critical = errors[0]['critical']
                high = errors[0]['high']
                
                status = 'error' if critical > 0 else 'warning'
                results.append(DiagnosticResult(
                    name='Errores del Sistema',
                    status=status,
                    message=f"{errors[0]['count']} error(es) sin resolver ({critical} críticos)",
                    action_required=critical > 0
                ))
            else:
                results.append(DiagnosticResult(
                    name='Errores del Sistema',
                    status='ok',
                    message='No hay errores pendientes'
                ))
        except Exception as e:
            results.append(DiagnosticResult(
                name='Errores del Sistema',
                status='error',
                message=f'Error: {e}'
            ))
        
        return results
    
    # ========================================================================
    # VISTAS RÁPIDAS
    # ========================================================================
    
    def show_recent_convocatorias(self, days: int = 7, limit: int = 20) -> List[Dict]:
        """Muestra convocatorias recientes"""
        if not self.connected:
            return []
        
        return self._execute_safe(f"""
            SELECT c.id_convocatoria, 
                   c.fecha_convocatoria::text as fecha,
                   dp.nombre || ' ' || dp.apellido as agente,
                   t.tipo_turno, 
                   c.estado
            FROM convocatoria c
            JOIN datos_personales dp ON c.id_agente = dp.id_agente
            JOIN turnos t ON c.id_turno = t.id_turno
            WHERE c.fecha_convocatoria >= CURRENT_DATE - INTERVAL '{days} days'
            ORDER BY c.fecha_convocatoria DESC, dp.apellido
            LIMIT {limit}
        """, default=[])
    
    def show_saldos_mes(self, mes: int = None, anio: int = None) -> List[Dict]:
        """Muestra saldos del mes"""
        if not self.connected:
            return []
        
        if mes is None:
            mes = datetime.now().month
        if anio is None:
            anio = datetime.now().year
        
        return self._execute_safe("""
            SELECT dp.nombre || ' ' || dp.apellido as agente,
                   s.horas_mes, 
                   s.horas_anuales, 
                   s.fecha_actualizacion::text as actualizado,
                   CASE 
                       WHEN s.horas_mes < 60 THEN 'BAJO'
                       WHEN s.horas_mes >= 90 THEN 'ALTO'
                       ELSE 'NORMAL'
                   END as nivel
            FROM saldos s
            JOIN datos_personales dp ON s.id_agente = dp.id_agente
            WHERE s.mes = %s AND s.anio = %s
            ORDER BY s.horas_mes DESC
        """, (mes, anio), default=[])
    
    def show_inasistencias_pendientes(self) -> List[Dict]:
        """Muestra inasistencias pendientes"""
        if not self.connected:
            return []
        
        return self._execute_safe("""
            SELECT i.id_inasistencia,
                   dp.nombre || ' ' || dp.apellido as agente,
                   i.fecha_inasistencia::text as fecha, 
                   i.motivo, 
                   i.estado,
                   (CURRENT_DATE - i.fecha_inasistencia) as dias
            FROM inasistencias i
            JOIN datos_personales dp ON i.id_agente = dp.id_agente
            WHERE i.estado = 'pendiente'
            ORDER BY i.fecha_inasistencia
        """, default=[])
    
    def show_errores_sistema(self, limit: int = 20) -> List[Dict]:
        """Muestra errores del sistema"""
        if not self.connected:
            return []
        
        return self._execute_safe(f"""
            SELECT id_error, 
                   timestamp::text as fecha,
                   error_type, 
                   component,
                   LEFT(error_message, 50) as mensaje, 
                   severity, 
                   resolved
            FROM system_errors
            ORDER BY resolved ASC, timestamp DESC
            LIMIT {limit}
        """, default=[])
    
    # ========================================================================
    # ACCIONES CORRECTIVAS
    # ========================================================================
    
    def fix_duplicate_convocatorias(self, dry_run: bool = True) -> Dict:
        """Corrige convocatorias duplicadas"""
        if not self.connected:
            return {'error': 'No conectado'}
        
        try:
            # Encontrar duplicados
            duplicates = self._execute("""
                SELECT id_agente, fecha_convocatoria, COUNT(*) as count
                FROM convocatoria
                WHERE estado = 'vigente'
                GROUP BY id_agente, fecha_convocatoria
                HAVING COUNT(*) > 1
            """)
            
            if not duplicates:
                return {'status': 'ok', 'message': 'No hay duplicados', 'affected': 0}
            
            result = {
                'duplicates_found': len(duplicates),
                'status': 'dry_run' if dry_run else 'pending'
            }
            
            if not dry_run:
                # Cancelar duplicados (mantener el más nuevo)
                affected = self._execute_write("""
                    UPDATE convocatoria c1
                    SET estado = 'cancelada',
                        motivo_cambio = 'Duplicada - cancelada automáticamente'
                    WHERE estado = 'vigente'
                    AND EXISTS (
                        SELECT 1 FROM convocatoria c2
                        WHERE c2.id_agente = c1.id_agente
                        AND c2.fecha_convocatoria = c1.fecha_convocatoria
                        AND c2.estado = 'vigente'
                        AND c2.id_convocatoria > c1.id_convocatoria
                    )
                """)
                result['status'] = 'ok'
                result['affected'] = affected
                result['message'] = f'{affected} convocatorias canceladas'
            else:
                result['message'] = 'Ejecutar con dry_run=False para aplicar'
            
            return result
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def recalculate_saldos(self, id_agente: int = None, mes: int = None, anio: int = None) -> Dict:
        """Recalcula saldos de horas"""
        if not self.connected:
            return {'error': 'No conectado'}
        
        if mes is None:
            mes = datetime.now().month
        if anio is None:
            anio = datetime.now().year
        
        try:
            # Query base
            agent_filter = f"AND c.id_agente = {id_agente}" if id_agente else ""
            
            affected = self._execute_write(f"""
                INSERT INTO saldos (id_agente, mes, anio, horas_mes, horas_anuales, fecha_actualizacion)
                SELECT 
                    c.id_agente,
                    {mes} as mes,
                    {anio} as anio,
                    COALESCE(SUM(CASE 
                        WHEN EXTRACT(MONTH FROM c.fecha_convocatoria) = {mes} 
                        THEN COALESCE(t.cant_horas_default, 0) ELSE 0 
                    END), 0) as horas_mes,
                    COALESCE(SUM(COALESCE(t.cant_horas_default, 0)), 0) as horas_anuales,
                    CURRENT_TIMESTAMP
                FROM convocatoria c
                JOIN turnos t ON c.id_turno = t.id_turno
                WHERE c.estado IN ('vigente', 'cumplida')
                AND EXTRACT(YEAR FROM c.fecha_convocatoria) = {anio}
                {agent_filter}
                GROUP BY c.id_agente
                ON CONFLICT (id_agente, mes, anio)
                DO UPDATE SET
                    horas_mes = EXCLUDED.horas_mes,
                    horas_anuales = EXCLUDED.horas_anuales,
                    fecha_actualizacion = CURRENT_TIMESTAMP
            """)
            
            return {
                'status': 'ok',
                'message': f'Saldos recalculados para {mes}/{anio}',
                'affected': affected
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def mark_error_resolved(self, id_error: int, notes: str = None) -> Dict:
        """Marca error como resuelto"""
        if not self.connected:
            return {'error': 'No conectado'}
        
        try:
            affected = self._execute_write("""
                UPDATE system_errors
                SET resolved = true,
                    resolution_date = CURRENT_TIMESTAMP,
                    resolution_notes = %s
                WHERE id_error = %s
            """, (notes or 'Resuelto via troubleshoot', id_error))
            
            return {
                'status': 'ok' if affected > 0 else 'warning',
                'message': f'Error {id_error} resuelto' if affected else 'Error no encontrado'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    # ========================================================================
    # CONSOLA SQL
    # ========================================================================
    
    def sql_console(self):
        """Consola SQL interactiva"""
        if not self.connected:
            print(f"{Color.ROJO}❌ No conectado{Color.FIN}")
            return
        
        print(f"\n{Color.CYAN}{'='*60}{Color.FIN}")
        print(f"{Color.BOLD}SQL Console - Supabase{Color.FIN}")
        print("Comandos: .exit, .tables, .count <tabla>")
        print(f"{Color.CYAN}{'='*60}{Color.FIN}\n")
        
        while True:
            try:
                sql = input(f"{Color.VERDE}SQL>{Color.FIN} ").strip()
                
                if not sql:
                    continue
                
                if sql.lower() in ('.exit', '.quit', 'exit'):
                    break
                
                if sql.lower() == '.tables':
                    result = self._execute_safe("""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = 'public' ORDER BY table_name
                    """)
                    for row in result:
                        print(f"  • {row['table_name']}")
                    continue
                
                if sql.lower().startswith('.count '):
                    table = sql.split()[1]
                    result = self._execute_safe(f"SELECT COUNT(*) as n FROM {table}")
                    print(f"  {table}: {result[0]['n'] if result else 'error'}")
                    continue
                
                # Ejecutar SQL normal
                is_select = sql.strip().upper().startswith('SELECT')
                
                if is_select:
                    result = self._execute_safe(sql)
                    if result:
                        # Mostrar resultados
                        keys = list(result[0].keys())
                        print("\n" + " | ".join(k[:15].ljust(15) for k in keys))
                        print("-" * (17 * len(keys)))
                        for row in result[:30]:
                            print(" | ".join(str(row.get(k, ''))[:15].ljust(15) for k in keys))
                        print(f"\n{len(result)} filas")
                    else:
                        print("Sin resultados")
                else:
                    confirm = input(f"{Color.AMARILLO}¿Ejecutar? (s/N): {Color.FIN}")
                    if confirm.lower() == 's':
                        try:
                            affected = self._execute_write(sql)
                            print(f"{Color.VERDE}✅ {affected} filas afectadas{Color.FIN}")
                        except Exception as e:
                            print(f"{Color.ROJO}Error: {e}{Color.FIN}")
                
            except KeyboardInterrupt:
                print("\n(.exit para salir)")
            except EOFError:
                break
    
    # ========================================================================
    # MENÚ INTERACTIVO
    # ========================================================================
    
    def interactive_menu(self):
        """Menú interactivo principal"""
        if not self.connected:
            if not self.connect():
                return
        
        while True:
            print(f"\n{Color.CYAN}{'='*60}{Color.FIN}")
            print(f"{Color.BOLD}🔧 Remote Troubleshooter v2 - Sistema RRHH{Color.FIN}")
            print(f"{Color.CYAN}{'='*60}{Color.FIN}")
            print()
            print("  1. 📊 Estado del Sistema")
            print("  2. 🔍 Diagnóstico Automático")
            print("  3. 📋 Ver Convocatorias Recientes")
            print("  4. 💰 Ver Saldos del Mes")
            print("  5. 🚫 Ver Inasistencias Pendientes")
            print("  6. ⚠️  Ver Errores del Sistema")
            print("  7. 🔧 Corregir Duplicados")
            print("  8. 📊 Recalcular Saldos")
            print("  9. 💻 Consola SQL")
            print("  0. 🚪 Salir")
            print()
            
            try:
                choice = input(f"{Color.VERDE}Opción: {Color.FIN}").strip()
                
                if choice == '1':
                    self._menu_system_status()
                elif choice == '2':
                    self._menu_diagnostics()
                elif choice == '3':
                    self._menu_convocatorias()
                elif choice == '4':
                    self._menu_saldos()
                elif choice == '5':
                    self._menu_inasistencias()
                elif choice == '6':
                    self._menu_errors()
                elif choice == '7':
                    self._menu_fix_duplicates()
                elif choice == '8':
                    self._menu_recalculate()
                elif choice == '9':
                    self.sql_console()
                elif choice == '0':
                    print("¡Hasta luego!")
                    break
                else:
                    print(f"{Color.AMARILLO}Opción no válida{Color.FIN}")
                    
            except Exception as e:
                print(f"{Color.ROJO}Error: {e}{Color.FIN}")
                if self.debug:
                    traceback.print_exc()
            
            # Pausa para ver resultado
            input(f"\n{Color.CYAN}Presiona Enter para continuar...{Color.FIN}")
    
    def _menu_system_status(self):
        """Opción 1: Estado del sistema"""
        print(f"\n{Color.CYAN}📊 ESTADO DEL SISTEMA{Color.FIN}")
        print("-" * 40)
        
        status = self.get_system_status()
        
        # Salud
        health = status.get('health', 'unknown')
        health_colors = {'healthy': Color.VERDE, 'warning': Color.AMARILLO, 'critical': Color.ROJO}
        print(f"\nSalud: {health_colors.get(health, Color.FIN)}{health.upper()}{Color.FIN}")
        
        # Tablas
        print(f"\n{Color.BOLD}Registros por tabla:{Color.FIN}")
        for table, count in status.get('tables', {}).items():
            print(f"  • {table}: {count}")
        
        # Actividad
        print(f"\n{Color.BOLD}Actividad (7 días):{Color.FIN}")
        for key, val in status.get('recent_activity', {}).items():
            print(f"  • {key}: {val}")
    
    def _menu_diagnostics(self):
        """Opción 2: Diagnósticos"""
        print(f"\n{Color.CYAN}🔍 DIAGNÓSTICO AUTOMÁTICO{Color.FIN}")
        print("-" * 40)
        
        results = self.diagnose_common_issues()
        
        for r in results:
            icons = {'ok': '✅', 'warning': '⚠️', 'error': '❌'}
            colors = {'ok': Color.VERDE, 'warning': Color.AMARILLO, 'error': Color.ROJO}
            
            print(f"\n{icons.get(r.status, '❓')} {Color.BOLD}{r.name}{Color.FIN}")
            print(f"   {colors.get(r.status, Color.FIN)}{r.message}{Color.FIN}")
            
            if r.suggested_action:
                print(f"   {Color.AMARILLO}→ {r.suggested_action}{Color.FIN}")
    
    def _menu_convocatorias(self):
        """Opción 3: Convocatorias"""
        print(f"\n{Color.CYAN}📋 CONVOCATORIAS RECIENTES{Color.FIN}")
        
        days = input("Días atrás (7): ").strip() or '7'
        result = self.show_recent_convocatorias(days=int(days))
        
        print("-" * 70)
        if result:
            print(f"{'Fecha':<12} {'Agente':<25} {'Turno':<15} {'Estado':<10}")
            print("-" * 70)
            for row in result:
                estado_color = Color.VERDE if row['estado'] == 'vigente' else Color.AMARILLO
                print(f"{str(row.get('fecha', ''))[:10]:<12} {str(row.get('agente', ''))[:24]:<25} {str(row.get('tipo_turno', ''))[:14]:<15} {estado_color}{row.get('estado', '')}{Color.FIN}")
        else:
            print("  Sin resultados")
    
    def _menu_saldos(self):
        """Opción 4: Saldos"""
        print(f"\n{Color.CYAN}💰 SALDOS DEL MES{Color.FIN}")
        
        mes = input(f"Mes ({datetime.now().month}): ").strip()
        mes = int(mes) if mes else datetime.now().month
        
        result = self.show_saldos_mes(mes=mes)
        
        print("-" * 60)
        if result:
            print(f"{'Agente':<30} {'Horas':<10} {'Nivel':<10}")
            print("-" * 60)
            for row in result:
                nivel_colors = {'BAJO': Color.ROJO, 'NORMAL': Color.VERDE, 'ALTO': Color.CYAN}
                nivel = row.get('nivel', 'NORMAL')
                print(f"{str(row.get('agente', ''))[:29]:<30} {str(row.get('horas_mes', 0)):<10} {nivel_colors.get(nivel, Color.FIN)}{nivel}{Color.FIN}")
        else:
            print("  Sin resultados")
    
    def _menu_inasistencias(self):
        """Opción 5: Inasistencias"""
        print(f"\n{Color.CYAN}🚫 INASISTENCIAS PENDIENTES{Color.FIN}")
        print("-" * 60)
        
        result = self.show_inasistencias_pendientes()
        
        if result:
            print(f"{'Fecha':<12} {'Agente':<25} {'Motivo':<15} {'Días':<6}")
            print("-" * 60)
            for row in result:
                dias = row.get('dias', 0)
                color = Color.ROJO if dias > 7 else Color.AMARILLO if dias > 3 else Color.FIN
                print(f"{str(row.get('fecha', ''))[:10]:<12} {str(row.get('agente', ''))[:24]:<25} {str(row.get('motivo', ''))[:14]:<15} {color}{dias}{Color.FIN}")
        else:
            print(f"  {Color.VERDE}✅ No hay inasistencias pendientes{Color.FIN}")
    
    def _menu_errors(self):
        """Opción 6: Errores"""
        print(f"\n{Color.CYAN}⚠️ ERRORES DEL SISTEMA{Color.FIN}")
        print("-" * 70)
        
        result = self.show_errores_sistema()
        
        if result:
            print(f"{'ID':<6} {'Fecha':<12} {'Severidad':<10} {'Componente':<15} {'Resuelto':<8}")
            print("-" * 70)
            for row in result:
                sev_colors = {'critical': Color.ROJO, 'high': Color.AMARILLO}
                resolved = '✅' if row.get('resolved') else '❌'
                sev = row.get('severity', 'low')
                print(f"{row.get('id_error', ''):<6} {str(row.get('fecha', ''))[:10]:<12} {sev_colors.get(sev, Color.FIN)}{sev:<10}{Color.FIN} {str(row.get('component', ''))[:14]:<15} {resolved}")
        else:
            print(f"  {Color.VERDE}✅ No hay errores{Color.FIN}")
    
    def _menu_fix_duplicates(self):
        """Opción 7: Corregir duplicados"""
        print(f"\n{Color.CYAN}🔧 CORREGIR DUPLICADOS{Color.FIN}")
        
        # Dry run primero
        result = self.fix_duplicate_convocatorias(dry_run=True)
        
        if result.get('duplicates_found', 0) == 0:
            print(f"\n{Color.VERDE}✅ No hay duplicados{Color.FIN}")
            return
        
        print(f"\nDuplicados: {result['duplicates_found']}")
        
        confirm = input(f"\n{Color.AMARILLO}¿Corregir? (s/N): {Color.FIN}")
        if confirm.lower() == 's':
            result = self.fix_duplicate_convocatorias(dry_run=False)
            print(f"\n{Color.VERDE}✅ {result.get('message', 'Completado')}{Color.FIN}")
    
    def _menu_recalculate(self):
        """Opción 8: Recalcular saldos"""
        print(f"\n{Color.CYAN}📊 RECALCULAR SALDOS{Color.FIN}")
        
        mes = input(f"Mes ({datetime.now().month}): ").strip()
        mes = int(mes) if mes else datetime.now().month
        
        result = self.recalculate_saldos(mes=mes)
        
        if result.get('status') == 'ok':
            print(f"\n{Color.VERDE}✅ {result.get('message')}{Color.FIN}")
        else:
            print(f"\n{Color.ROJO}❌ {result.get('message')}{Color.FIN}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Remote Troubleshooter v2')
    parser.add_argument('--status', action='store_true', help='Estado del sistema')
    parser.add_argument('--diagnose', action='store_true', help='Diagnóstico')
    parser.add_argument('--sql', action='store_true', help='Consola SQL')
    parser.add_argument('--debug', action='store_true', help='Modo debug')
    parser.add_argument('--env', type=str, help='Ruta a .env')
    
    args = parser.parse_args()
    
    rt = RemoteTroubleshooter(env_path=args.env, debug=args.debug)
    
    try:
        if not rt.connect():
            sys.exit(1)
        
        if args.status:
            rt._menu_system_status()
        elif args.diagnose:
            rt._menu_diagnostics()
        elif args.sql:
            rt.sql_console()
        else:
            rt.interactive_menu()
    finally:
        rt.disconnect()


if __name__ == '__main__':
    main()
