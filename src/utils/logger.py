"""
Error Logger - Sistema de Logging Automático
Registra y monitorea errores del sistema
Detecta patrones y genera alertas
"""

import traceback
import json
import functools
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from database_manager import DatabaseManager
import logging

logger = logging.getLogger(__name__)


class ErrorLogger:
    """
    Registra errores automáticamente en la base de datos
    Detecta patrones y genera alertas
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    # ========================================================================
    # REGISTRO DE ERRORES
    # ========================================================================
    
    def log_error(self,
                  error_type: str,
                  component: str,
                  error_message: str,
                  error_details: str = None,
                  severity: str = 'medium',
                  user_action: str = None,
                  id_agente: int = None,
                  id_convocatoria: int = None,
                  id_transaccion: int = None,
                  additional_context: Dict = None) -> int:
        """
        Registra un error en el sistema
        
        Args:
            error_type: Tipo de error ('trigger', 'constraint', 'validation', etc.)
            component: Componente donde ocurrió ('cambio_turno_manager', etc.)
            error_message: Mensaje corto del error
            error_details: Stack trace o detalles técnicos
            severity: 'low', 'medium', 'high', 'critical'
            user_action: Qué estaba haciendo el usuario
            id_agente: ID del agente involucrado (si aplica)
            id_convocatoria: ID de convocatoria involucrada (si aplica)
            id_transaccion: ID de transacción involucrada (si aplica)
            additional_context: Dict con contexto adicional (se guarda como JSON)
        
        Returns:
            ID del error registrado
        """
        try:
            context_json = json.dumps(additional_context) if additional_context else None
            
            with self.db.get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO system_errors
                    (error_type, component, error_message, error_details,
                     severity, user_action, id_agente, id_convocatoria,
                     id_transaccion, additional_context)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (error_type, component, error_message, error_details,
                     severity, user_action, id_agente, id_convocatoria,
                     id_transaccion, context_json)
                )
                
                id_error = cursor.lastrowid
                
                # Log a nivel Python también
                log_level = {
                    'critical': logging.CRITICAL,
                    'high': logging.ERROR,
                    'medium': logging.WARNING,
                    'low': logging.INFO
                }.get(severity, logging.WARNING)
                
                logger.log(log_level, 
                          f"[{component}] {error_message}")
                
                return id_error
                
        except Exception as e:
            # Si falla el logging, al menos registrar en Python
            logger.error(f"Error registrando error en BD: {e}")
            logger.error(f"Error original: {error_message}")
            return None
    
    def log_exception(self,
                      component: str,
                      exception: Exception,
                      severity: str = 'medium',
                      user_action: str = None,
                      **context) -> int:
        """
        Registra una excepción de Python automáticamente
        
        Args:
            component: Nombre del componente
            exception: La excepción capturada
            severity: Nivel de severidad
            user_action: Qué estaba haciendo el usuario
            **context: Contexto adicional (id_agente, id_convocatoria, etc.)
        """
        # Determinar tipo de error según la excepción
        error_type = self._classify_exception(exception)
        
        return self.log_error(
            error_type=error_type,
            component=component,
            error_message=str(exception),
            error_details=traceback.format_exc(),
            severity=severity,
            user_action=user_action,
            id_agente=context.get('id_agente'),
            id_convocatoria=context.get('id_convocatoria'),
            id_transaccion=context.get('id_transaccion'),
            additional_context=context
        )
    
    def _classify_exception(self, exception: Exception) -> str:
        """Clasifica automáticamente el tipo de error según la excepción"""
        import sqlite3
        
        if isinstance(exception, sqlite3.IntegrityError):
            return 'constraint'
        elif isinstance(exception, sqlite3.OperationalError):
            return 'database'
        elif isinstance(exception, ValueError):
            return 'validation'
        elif isinstance(exception, (ConnectionError, TimeoutError)):
            return 'network'
        else:
            return 'python_operation'
    
    # ========================================================================
    # DECORADOR PARA AUTO-LOGGING
    # ========================================================================
    
    def log_errors(self, component: str = None, severity: str = 'medium'):
        """
        Decorador que captura y registra errores automáticamente
        
        Uso:
            @error_logger.log_errors(component='cambio_turno', severity='high')
            def aprobar_cambio(id_trans):
                # código que puede fallar
                pass
        """
        def decorator(func: Callable) -> Callable:
            component_name = component or func.__name__
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Registrar error
                    self.log_exception(
                        component=component_name,
                        exception=e,
                        severity=severity,
                        user_action=f"Ejecutando {func.__name__}",
                        args=str(args),
                        kwargs=str(kwargs)
                    )
                    # Re-lanzar la excepción
                    raise
            
            return wrapper
        return decorator
    
    # ========================================================================
    # CONSULTAS Y ANÁLISIS
    # ========================================================================
    
    def get_dashboard(self) -> Dict:
        """
        Obtiene el dashboard de salud del sistema
        
        Returns:
            Dict con métricas de salud
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM vista_salud_sistema")
                row = cursor.fetchone()
                return dict(row) if row else {}
        except Exception as e:
            logger.error(f"Error obteniendo dashboard: {e}")
            return {}
    
    def get_recent_errors(self, days: int = 7) -> List[Dict]:
        """Obtiene errores recientes"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM vista_errores_recientes LIMIT 50"
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error obteniendo errores recientes: {e}")
            return []
    
    def get_patterns(self) -> List[Dict]:
        """Obtiene patrones de errores detectados"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM vista_patrones_errores"
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error obteniendo patrones: {e}")
            return []
    
    def get_errors_by_component(self) -> List[Dict]:
        """Análisis de errores por componente"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM vista_errores_por_componente"
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error obteniendo análisis por componente: {e}")
            return []
    
    def get_timeline(self, days: int = 30) -> List[Dict]:
        """Obtiene timeline de errores para gráficos"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM vista_errores_timeline"
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error obteniendo timeline: {e}")
            return []
    
    # ========================================================================
    # GESTIÓN DE ERRORES
    # ========================================================================
    
    def resolve_error(self, 
                      id_error: int, 
                      resolution_notes: str,
                      resolved_by: str) -> bool:
        """Marca un error como resuelto"""
        try:
            with self.db.get_connection() as conn:
                conn.execute(
                    """UPDATE system_errors
                    SET resolved = 1,
                        resolution_notes = ?,
                        resolved_by = ?
                    WHERE id_error = ?""",
                    (resolution_notes, resolved_by, id_error)
                )
                logger.info(f"Error {id_error} marcado como resuelto")
                return True
        except Exception as e:
            logger.error(f"Error marcando como resuelto: {e}")
            return False
    
    def resolve_pattern(self,
                        id_pattern: int,
                        resolution_description: str) -> bool:
        """Marca un patrón como resuelto"""
        try:
            with self.db.get_connection() as conn:
                conn.execute(
                    """UPDATE error_patterns
                    SET pattern_status = 'resolved',
                        resolution_description = ?
                    WHERE id_pattern = ?""",
                    (resolution_description, id_pattern)
                )
                logger.info(f"Patrón {id_pattern} marcado como resuelto")
                return True
        except Exception as e:
            logger.error(f"Error resolviendo patrón: {e}")
            return False
    
    # ========================================================================
    # ALERTAS
    # ========================================================================
    
    def check_alerts(self) -> List[Dict]:
        """
        Verifica si hay situaciones que requieren alertas inmediatas
        
        Returns:
            Lista de alertas que requieren acción
        """
        alerts = []
        dashboard = self.get_dashboard()
        
        if not dashboard:
            return alerts
        
        # Alerta crítica: errores críticos sin resolver
        if dashboard.get('criticos_pendientes', 0) > 0:
            alerts.append({
                'nivel': 'CRÍTICO',
                'tipo': 'errores_criticos',
                'mensaje': f"{dashboard['criticos_pendientes']} error(es) crítico(s) sin resolver",
                'accion': 'Revisar inmediatamente en vista_errores_recientes'
            })
        
        # Alerta alta: muchos errores en 24h
        if dashboard.get('errores_24h', 0) > 20:
            alerts.append({
                'nivel': 'ALTO',
                'tipo': 'volumen_errores',
                'mensaje': f"{dashboard['errores_24h']} errores en las últimas 24 horas",
                'accion': 'Investigar causa raíz'
            })
        
        # Alerta media: patrones activos
        if dashboard.get('patrones_activos', 0) > 0:
            alerts.append({
                'nivel': 'MEDIO',
                'tipo': 'patrones_detectados',
                'mensaje': f"{dashboard['patrones_activos']} patrón(es) de errores recurrentes",
                'accion': 'Revisar vista_patrones_errores'
            })
        
        # Alerta baja: componente problemático
        if dashboard.get('componente_problematico'):
            alerts.append({
                'nivel': 'BAJO',
                'tipo': 'componente_problematico',
                'mensaje': f"Componente con más errores: {dashboard['componente_problematico']}",
                'accion': 'Revisar implementación del componente'
            })
        
        return alerts
    
    def generate_alert_email(self) -> str:
        """
        Genera el contenido de un email de alerta
        
        Returns:
            HTML con el contenido del email
        """
        dashboard = self.get_dashboard()
        alerts = self.check_alerts()
        recent_errors = self.get_recent_errors(days=1)
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .critical {{ background-color: #ffebee; padding: 10px; }}
                .high {{ background-color: #fff3e0; padding: 10px; }}
                .healthy {{ background-color: #e8f5e9; padding: 10px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
            </style>
        </head>
        <body>
            <h2>Reporte de Salud del Sistema</h2>
            <p><strong>Fecha:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            
            <div class="{self._get_status_class(dashboard.get('estado_sistema', ''))}">
                <h3>Estado General: {dashboard.get('estado_sistema', 'DESCONOCIDO')}</h3>
            </div>
            
            <h3>Métricas Principales</h3>
            <ul>
                <li>Errores últimas 24h: {dashboard.get('errores_24h', 0)}</li>
                <li>Críticos pendientes: {dashboard.get('criticos_pendientes', 0)}</li>
                <li>Patrones activos: {dashboard.get('patrones_activos', 0)}</li>
                <li>Tasa de resolución: {dashboard.get('tasa_resolucion_porcentaje', 0)}%</li>
            </ul>
            
            <h3>Alertas Activas</h3>
            {'<p>No hay alertas activas</p>' if not alerts else self._format_alerts_html(alerts)}
            
            <h3>Últimos Errores (24h)</h3>
            {self._format_errors_table(recent_errors[:10])}
            
            <p><em>Este es un reporte automático del sistema de monitoreo.</em></p>
        </body>
        </html>
        """
        
        return html
    
    def _get_status_class(self, estado: str) -> str:
        """Determina la clase CSS según el estado"""
        if 'CRÍTICO' in estado:
            return 'critical'
        elif 'ATENCIÓN' in estado:
            return 'high'
        else:
            return 'healthy'
    
    def _format_alerts_html(self, alerts: List[Dict]) -> str:
        """Formatea las alertas como HTML"""
        html = "<ul>"
        for alert in alerts:
            html += f"""
            <li>
                <strong>[{alert['nivel']}]</strong> {alert['mensaje']}<br>
                <em>Acción: {alert['accion']}</em>
            </li>
            """
        html += "</ul>"
        return html
    
    def _format_errors_table(self, errors: List[Dict]) -> str:
        """Formatea los errores como tabla HTML"""
        if not errors:
            return "<p>No hay errores recientes</p>"
        
        html = """
        <table>
            <tr>
                <th>Timestamp</th>
                <th>Componente</th>
                <th>Mensaje</th>
                <th>Severidad</th>
            </tr>
        """
        
        for error in errors:
            html += f"""
            <tr>
                <td>{error.get('timestamp', '')}</td>
                <td>{error.get('component', '')}</td>
                <td>{error.get('error_message', '')[:100]}</td>
                <td>{error.get('severity', '')}</td>
            </tr>
            """
        
        html += "</table>"
        return html
    
    # ========================================================================
    # MANTENIMIENTO
    # ========================================================================
    
    def cleanup_old_errors(self, days: int = 90) -> int:
        """
        Limpia errores resueltos antiguos
        
        Args:
            days: Eliminar errores resueltos más antiguos que X días
        
        Returns:
            Cantidad de errores eliminados
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute(
                    """DELETE FROM system_errors
                    WHERE resolved = 1
                    AND resolution_date < datetime('now', ? || ' days')""",
                    (f'-{days}',)
                )
                deleted = cursor.rowcount
                logger.info(f"Limpieza: {deleted} errores antiguos eliminados")
                return deleted
        except Exception as e:
            logger.error(f"Error en limpieza: {e}")
            return 0
    
    def archive_old_patterns(self, days: int = 90) -> int:
        """Archiva patrones resueltos antiguos"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute(
                    """UPDATE error_patterns
                    SET pattern_status = 'ignored'
                    WHERE pattern_status = 'resolved'
                    AND last_occurrence < datetime('now', ? || ' days')""",
                    (f'-{days}',)
                )
                archived = cursor.rowcount
                logger.info(f"Archivado: {archived} patrones antiguos")
                return archived
        except Exception as e:
            logger.error(f"Error archivando patrones: {e}")
            return 0


# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def setup_error_logging(db: DatabaseManager) -> ErrorLogger:
    """
    Configura el sistema de logging de errores
    
    Returns:
        Instancia de ErrorLogger configurada
    """
    error_logger = ErrorLogger(db)
    
    # Configurar logging de Python para que también use ErrorLogger
    class DBHandler(logging.Handler):
        def emit(self, record):
            if record.levelno >= logging.ERROR:
                error_logger.log_error(
                    error_type='python_operation',
                    component=record.name,
                    error_message=record.getMessage(),
                    error_details=self.format(record),
                    severity='high' if record.levelno >= logging.CRITICAL else 'medium'
                )
    
    # Agregar handler a logger raíz
    db_handler = DBHandler()
    logging.getLogger().addHandler(db_handler)
    
    return error_logger


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

def ejemplo_uso_error_logger():
    """Ejemplo completo del sistema de logging"""
    from database_manager import DatabaseManager
    
    db = DatabaseManager('gestion_rrhh.db')
    error_logger = ErrorLogger(db)
    
    print("="*70)
    print("SISTEMA DE LOGGING - EJEMPLO DE USO")
    print("="*70)
    
    # 1. Uso básico: registrar error manualmente
    print("\n1. Registrando error manualmente...")
    id_error = error_logger.log_error(
        error_type='validation',
        component='cambio_turno',
        error_message='Agente no está capacitado en dispositivo',
        severity='medium',
        user_action='Intentando asignar dispositivo',
        id_agente=1,
        additional_context={'dispositivo_id': 5}
    )
    print(f"   ✓ Error registrado: ID={id_error}")
    
    # 2. Uso con decorador
    print("\n2. Usando decorador para auto-logging...")
    
    @error_logger.log_errors(component='test_function', severity='high')
    def funcion_que_falla():
        raise ValueError("Error de prueba")
    
    try:
        funcion_que_falla()
    except ValueError:
        print("   ✓ Error capturado y registrado automáticamente")
    
    # 3. Dashboard de salud
    print("\n3. Consultando dashboard de salud...")
    dashboard = error_logger.get_dashboard()
    print(f"   Estado del sistema: {dashboard.get('estado_sistema', 'N/A')}")
    print(f"   Errores últimas 24h: {dashboard.get('errores_24h', 0)}")
    print(f"   Críticos pendientes: {dashboard.get('criticos_pendientes', 0)}")
    
    # 4. Verificar alertas
    print("\n4. Verificando alertas...")
    alerts = error_logger.check_alerts()
    if alerts:
        print(f"   ⚠️  {len(alerts)} alerta(s) activa(s):")
        for alert in alerts:
            print(f"      [{alert['nivel']}] {alert['mensaje']}")
    else:
        print("   ✓ No hay alertas activas")
    
    # 5. Patrones detectados
    print("\n5. Patrones de errores detectados...")
    patterns = error_logger.get_patterns()
    if patterns:
        print(f"   Patrones encontrados: {len(patterns)}")
        for pattern in patterns[:3]:
            print(f"   - {pattern['component']}: {pattern['veces_ocurrido']} veces ({pattern['nivel_urgencia']})")
    else:
        print("   ✓ No se detectaron patrones")
    
    print("\n" + "="*70)
    print("✓ Ejemplo completado")
    print("="*70)


if __name__ == '__main__':
    ejemplo_uso_error_logger()