#!/usr/bin/env python3
"""
=============================================================================
UNIFIED DATABASE MANAGER v1.0
=============================================================================

Capa de abstracción para arquitectura híbrida:
- Supabase (PostgreSQL) para datos del año en curso
- SQLite local para datos históricos

El usuario no necesita saber qué BD se está usando - el manager decide
automáticamente según la fecha de los datos.

ARQUITECTURA:
    ┌─────────────────────────────────────────────────┐
    │            unified_db_manager.py                 │
    │         (Decide qué BD usar según fecha)         │
    └──────────────┬─────────────────┬────────────────┘
                   │                 │
           ┌───────┴───────┐ ┌───────┴───────┐
           │   Supabase    │ │   SQLite      │
           │  (año actual) │ │ (histórico)   │
           │  PostgreSQL   │ │   local       │
           └───────────────┘ └───────────────┘

REQUISITOS:
    pip install psycopg2-binary python-dotenv

CONFIGURACIÓN:
    Archivo .env con:
        SUPABASE_DB_HOST=aws-1-sa-east-1.pooler.supabase.com
        SUPABASE_DB_PORT=6543
        SUPABASE_DB_NAME=postgres
        SUPABASE_DB_USER=postgres.zgzqeusbpobrwanvktyz
        SUPABASE_DB_PASSWORD=<tu-password-16-chars>

USO BÁSICO:
    from unified_db_manager import UnifiedDBManager
    
    db = UnifiedDBManager()
    
    # Insertar (automáticamente va a BD correcta según fecha)
    db.insert_convocatoria({
        'fecha_convocatoria': '2025-12-15',
        'id_agente': 1,
        ...
    })
    
    # Query (busca en BD correcta)
    convs = db.query_convocatorias(fecha_desde='2025-01-01')

Autor: Pablo - Data Analyst
Fecha: Diciembre 2025
Proyecto: El Molino Fábrica Cultural - Sistema RRHH
=============================================================================
"""

import sqlite3
import os
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Optional, Union, List, Dict, Any, Tuple
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

# Intentar importar dependencias opcionales
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, execute_batch
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Variables de entorno del sistema

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS Y DATACLASSES
# =============================================================================

class DBMode(Enum):
    """Modo de selección de base de datos"""
    AUTO = "auto"           # Decide automáticamente según fecha
    SUPABASE = "supabase"   # Forzar Supabase (online)
    SQLITE = "sqlite"       # Forzar SQLite (local)
    OFFLINE = "offline"     # Solo SQLite (sin intentar conectar a Supabase)


@dataclass
class ConnectionInfo:
    """Información sobre una conexión"""
    db_type: str            # 'supabase' o 'sqlite'
    status: str             # 'connected', 'disconnected', 'error'
    host: Optional[str]
    database: str
    last_check: datetime
    error_message: Optional[str] = None


@dataclass
class QueryResult:
    """Resultado de una query"""
    data: List[Dict[str, Any]]
    row_count: int
    source_db: str          # 'supabase' o 'sqlite'
    execution_time_ms: float


# =============================================================================
# UNIFIED DATABASE MANAGER
# =============================================================================

class UnifiedDBManager:
    """
    Gestor unificado de base de datos
    
    Gestiona acceso transparente a:
    - Supabase (PostgreSQL) para datos del año en curso
    - SQLite local para datos históricos
    
    Attributes:
        current_year: Año considerado "actual" (datos en Supabase)
        sqlite_base_path: Directorio base para archivos SQLite
        supabase_connected: True si la conexión a Supabase está activa
    """
    
    def __init__(self, 
                 current_year: int = None,
                 sqlite_base_path: str = 'data',
                 sqlite_db_name: str = 'gestion_rrhh.db',
                 auto_connect_supabase: bool = True):
        """
        Inicializa el manager
        
        Args:
            current_year: Año para datos online (default: año actual)
            sqlite_base_path: Ruta base para SQLite
            sqlite_db_name: Nombre del archivo SQLite
            auto_connect_supabase: Intentar conectar a Supabase al iniciar
        """
        self.current_year = current_year or datetime.now().year
        self.sqlite_base_path = Path(sqlite_base_path)
        self.sqlite_db_name = sqlite_db_name
        
        # Estado de conexiones
        self._supabase_conn: Optional[Any] = None
        self._sqlite_connections: Dict[int, sqlite3.Connection] = {}
        self.supabase_connected = False
        
        # Configuración Supabase desde variables de entorno
        self._supabase_config = {
            'host': os.getenv('SUPABASE_DB_HOST'),
            'port': os.getenv('SUPABASE_DB_PORT', '6543'),
            'database': os.getenv('SUPABASE_DB_NAME', 'postgres'),
            'user': os.getenv('SUPABASE_DB_USER'),
            'password': os.getenv('SUPABASE_DB_PASSWORD')
        }
        
        # Inicializar conexiones
        if auto_connect_supabase:
            self._init_supabase()
        
        logger.info(f"UnifiedDBManager inicializado (año actual: {self.current_year})")
        logger.info(f"Supabase: {'✅ Conectado' if self.supabase_connected else '❌ Offline'}")
    
    # =========================================================================
    # INICIALIZACIÓN DE CONEXIONES
    # =========================================================================
    
    def _init_supabase(self) -> bool:
        """Inicializa conexión a Supabase"""
        if not PSYCOPG2_AVAILABLE:
            logger.warning("psycopg2 no disponible - modo offline")
            return False
        
        # Verificar configuración
        if not all([self._supabase_config['host'], 
                    self._supabase_config['user'],
                    self._supabase_config['password']]):
            logger.warning("Configuración Supabase incompleta en .env")
            return False
        
        try:
            # Usar kwargs es más seguro para contraseñas con caracteres especiales
            self._supabase_conn = psycopg2.connect(
                host=self._supabase_config['host'],
                port=self._supabase_config['port'],
                dbname=self._supabase_config['database'],
                user=self._supabase_config['user'],
                password=self._supabase_config['password'],
                sslmode='require',
                connect_timeout=15
            )
            self._supabase_conn.autocommit = False
            self.supabase_connected = True
            
            logger.info(f"✅ Conectado a Supabase: {self._supabase_config['host']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error conectando a Supabase: {e}")
            self.supabase_connected = False
            return False
    
    def _get_sqlite_connection(self, year: int = None) -> sqlite3.Connection:
        """
        Obtiene conexión SQLite para un año específico
        
        Args:
            year: Año (None = usar año actual)
        
        Returns:
            Conexión SQLite con row_factory configurada
        """
        year = year or self.current_year
        
        # Usar caché de conexiones
        if year not in self._sqlite_connections:
            # Construir path según año
            if year == self.current_year:
                db_path = self.sqlite_base_path / self.sqlite_db_name
            else:
                db_path = self.sqlite_base_path / f"gestion_rrhh_{year}.db"
            
            if not db_path.exists():
                # Si no existe el archivo histórico, usar el principal
                db_path = self.sqlite_base_path / self.sqlite_db_name
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            
            self._sqlite_connections[year] = conn
            logger.debug(f"Conexión SQLite creada: {db_path}")
        
        return self._sqlite_connections[year]
    
    # =========================================================================
    # SELECCIÓN AUTOMÁTICA DE BD
    # =========================================================================
    
    def _extract_year(self, fecha: Union[str, date, datetime, None]) -> int:
        """Extrae año de una fecha en cualquier formato"""
        if fecha is None:
            return self.current_year
        
        if isinstance(fecha, str):
            try:
                fecha = datetime.strptime(fecha[:10], '%Y-%m-%d')
            except ValueError:
                return self.current_year
        
        if isinstance(fecha, (date, datetime)):
            return fecha.year
        
        return self.current_year
    
    def _should_use_supabase(self, fecha: Union[str, date, datetime, None] = None,
                              mode: DBMode = DBMode.AUTO) -> bool:
        """
        Determina si debe usarse Supabase o SQLite
        
        Args:
            fecha: Fecha de los datos (None = actual)
            mode: Modo de operación
        
        Returns:
            True si debe usar Supabase, False para SQLite
        """
        # Modos explícitos
        if mode == DBMode.SUPABASE:
            if not self.supabase_connected:
                raise ConnectionError("Supabase no está disponible")
            return True
        
        if mode in (DBMode.SQLITE, DBMode.OFFLINE):
            return False
        
        # Modo AUTO: decidir según fecha
        year = self._extract_year(fecha)
        
        # Usar Supabase solo si:
        # 1. Es el año actual O posterior
        # 2. Supabase está conectado
        if year >= self.current_year and self.supabase_connected:
            return True
        
        return False
    
    # =========================================================================
    # CONTEXT MANAGERS
    # =========================================================================
    
    @contextmanager
    def get_connection(self, fecha: Union[str, date, datetime, None] = None,
                       mode: DBMode = DBMode.AUTO):
        """
        Context manager para obtener conexión apropiada
        
        Args:
            fecha: Fecha para determinar BD
            mode: Modo de selección
        
        Yields:
            Tupla (conexión, tipo_bd)
        
        Uso:
            with db.get_connection('2025-12-15') as (conn, db_type):
                cursor = conn.cursor()
                ...
        """
        use_supabase = self._should_use_supabase(fecha, mode)
        
        if use_supabase:
            conn = self._supabase_conn
            db_type = 'supabase'
        else:
            year = self._extract_year(fecha)
            conn = self._get_sqlite_connection(year)
            db_type = 'sqlite'
        
        try:
            yield conn, db_type
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
    
    @contextmanager
    def transaction(self, fecha: Union[str, date, datetime, None] = None,
                    mode: DBMode = DBMode.AUTO):
        """
        Context manager para transacciones
        
        Uso:
            with db.transaction('2025-12-15') as (conn, db_type):
                db.execute(conn, "INSERT INTO ...")
                db.execute(conn, "UPDATE ...")
                # Auto-commit al final, rollback en error
        """
        with self.get_connection(fecha, mode) as (conn, db_type):
            yield conn, db_type
    
    # =========================================================================
    # EJECUCIÓN DE QUERIES
    # =========================================================================
    
    def execute(self, sql: str, params: tuple = None,
                fecha: Union[str, date, datetime, None] = None,
                mode: DBMode = DBMode.AUTO) -> int:
        """
        Ejecuta SQL en la BD apropiada
        
        Args:
            sql: Query SQL
            params: Parámetros (tuple)
            fecha: Fecha para determinar BD
            mode: Modo de selección
        
        Returns:
            Número de filas afectadas
        """
        with self.get_connection(fecha, mode) as (conn, db_type):
            cursor = conn.cursor()
            
            # Ajustar placeholders según BD
            if db_type == 'supabase':
                sql = self._convert_placeholders_to_pg(sql)
            
            cursor.execute(sql, params or ())
            return cursor.rowcount
    
    def query(self, sql: str, params: tuple = None,
              fecha: Union[str, date, datetime, None] = None,
              mode: DBMode = DBMode.AUTO) -> QueryResult:
        """
        Ejecuta SELECT y retorna resultados
        
        Args:
            sql: Query SELECT
            params: Parámetros
            fecha: Fecha para determinar BD
            mode: Modo de selección
        
        Returns:
            QueryResult con datos, conteo y fuente
        """
        import time
        start = time.time()
        
        with self.get_connection(fecha, mode) as (conn, db_type):
            if db_type == 'supabase':
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                sql = self._convert_placeholders_to_pg(sql)
            else:
                cursor = conn.cursor()
            
            cursor.execute(sql, params or ())
            rows = cursor.fetchall()
            
            # Convertir a lista de dicts
            if db_type == 'sqlite':
                data = [dict(row) for row in rows]
            else:
                data = [dict(row) for row in rows]
            
            elapsed = (time.time() - start) * 1000
            
            return QueryResult(
                data=data,
                row_count=len(data),
                source_db=db_type,
                execution_time_ms=elapsed
            )
    
    def query_one(self, sql: str, params: tuple = None,
                  fecha: Union[str, date, datetime, None] = None,
                  mode: DBMode = DBMode.AUTO) -> Optional[Dict[str, Any]]:
        """Ejecuta query y retorna primera fila o None"""
        result = self.query(sql, params, fecha, mode)
        return result.data[0] if result.data else None
    
    def _convert_placeholders_to_pg(self, sql: str) -> str:
        """Convierte ? a %s para PostgreSQL"""
        return sql.replace('?', '%s')
    
    # =========================================================================
    # OPERACIONES DE CONVOCATORIAS
    # =========================================================================
    
    def insert_convocatoria(self, data: Dict[str, Any]) -> int:
        """
        Inserta convocatoria en BD apropiada según fecha
        
        Args:
            data: Dict con campos de convocatoria
                  Debe incluir 'fecha_convocatoria'
        
        Returns:
            ID de la convocatoria insertada
        """
        fecha = data.get('fecha_convocatoria')
        
        sql = """
            INSERT INTO convocatoria 
            (id_plani, id_agente, id_turno, fecha_convocatoria, estado)
            VALUES (?, ?, ?, ?, ?)
        """
        
        params = (
            data['id_plani'],
            data['id_agente'],
            data['id_turno'],
            fecha,
            data.get('estado', 'vigente')
        )
        
        with self.get_connection(fecha) as (conn, db_type):
            cursor = conn.cursor()
            
            if db_type == 'supabase':
                sql = self._convert_placeholders_to_pg(sql)
                sql += " RETURNING id_convocatoria"
                cursor.execute(sql, params)
                result = cursor.fetchone()
                return result[0] if result else None
            else:
                cursor.execute(sql, params)
                return cursor.lastrowid
    
    def query_convocatorias(self, 
                            fecha_desde: str = None,
                            fecha_hasta: str = None,
                            id_agente: int = None,
                            estado: str = None,
                            limit: int = 1000) -> QueryResult:
        """
        Query flexible de convocatorias
        
        Args:
            fecha_desde: Fecha inicio (inclusive)
            fecha_hasta: Fecha fin (inclusive)
            id_agente: Filtrar por agente
            estado: Filtrar por estado
            limit: Máximo de resultados
        
        Returns:
            QueryResult con convocatorias
        """
        conditions = []
        params = []
        
        if fecha_desde:
            conditions.append("fecha_convocatoria >= ?")
            params.append(fecha_desde)
        
        if fecha_hasta:
            conditions.append("fecha_convocatoria <= ?")
            params.append(fecha_hasta)
        
        if id_agente:
            conditions.append("id_agente = ?")
            params.append(id_agente)
        
        if estado:
            conditions.append("estado = ?")
            params.append(estado)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
            SELECT c.*, 
                   dp.nombre || ' ' || dp.apellido as agente_nombre,
                   t.tipo_turno
            FROM convocatoria c
            JOIN datos_personales dp ON c.id_agente = dp.id_agente
            JOIN turnos t ON c.id_turno = t.id_turno
            WHERE {where_clause}
            ORDER BY c.fecha_convocatoria DESC
            LIMIT ?
        """
        params.append(limit)
        
        # Usar la fecha más reciente del filtro para determinar BD
        fecha_ref = fecha_hasta or fecha_desde
        return self.query(sql, tuple(params), fecha_ref)
    
    def update_convocatoria_estado(self, id_convocatoria: int, 
                                    nuevo_estado: str,
                                    motivo: str = None) -> bool:
        """Actualiza estado de una convocatoria"""
        sql = """
            UPDATE convocatoria 
            SET estado = ?, 
                motivo_cambio = ?,
                fecha_modificacion = CURRENT_TIMESTAMP
            WHERE id_convocatoria = ?
        """
        
        # Primero obtener la fecha para saber en qué BD está
        result = self.query_one(
            "SELECT fecha_convocatoria FROM convocatoria WHERE id_convocatoria = ?",
            (id_convocatoria,),
            mode=DBMode.AUTO
        )
        
        if not result:
            return False
        
        fecha = result['fecha_convocatoria']
        rows = self.execute(sql, (nuevo_estado, motivo, id_convocatoria), fecha)
        return rows > 0
    
    # =========================================================================
    # OPERACIONES DE SALDOS
    # =========================================================================
    
    def get_saldos_agente(self, id_agente: int, 
                          year: int = None) -> List[Dict[str, Any]]:
        """
        Obtiene saldos de horas de un agente
        
        Args:
            id_agente: ID del agente
            year: Año a consultar (None = actual)
        
        Returns:
            Lista de saldos por mes
        """
        year = year or self.current_year
        
        sql = """
            SELECT s.*, dp.nombre || ' ' || dp.apellido as agente
            FROM saldos s
            JOIN datos_personales dp ON s.id_agente = dp.id_agente
            WHERE s.id_agente = ? AND s.anio = ?
            ORDER BY s.mes
        """
        
        result = self.query(sql, (id_agente, year), f"{year}-01-01")
        return result.data
    
    def get_saldos_mes(self, mes: int, year: int = None) -> QueryResult:
        """Obtiene saldos de todos los agentes para un mes"""
        year = year or self.current_year
        
        sql = """
            SELECT s.*, dp.nombre || ' ' || dp.apellido as agente,
                   CASE 
                       WHEN s.horas_mes < 60 THEN 'BAJO'
                       WHEN s.horas_mes >= 90 THEN 'ALTO'
                       ELSE 'NORMAL'
                   END as nivel
            FROM saldos s
            JOIN datos_personales dp ON s.id_agente = dp.id_agente
            WHERE s.mes = ? AND s.anio = ?
            ORDER BY dp.apellido
        """
        
        return self.query(sql, (mes, year), f"{year}-{mes:02d}-01")
    
    # =========================================================================
    # OPERACIONES DE INASISTENCIAS
    # =========================================================================
    
    def insert_inasistencia(self, data: Dict[str, Any]) -> int:
        """Inserta una inasistencia"""
        fecha = data.get('fecha_inasistencia')
        
        sql = """
            INSERT INTO inasistencias 
            (id_agente, fecha_inasistencia, motivo, observaciones)
            VALUES (?, ?, ?, ?)
        """
        
        params = (
            data['id_agente'],
            fecha,
            data.get('motivo', 'imprevisto'),
            data.get('observaciones', '')
        )
        
        with self.get_connection(fecha) as (conn, db_type):
            cursor = conn.cursor()
            
            if db_type == 'supabase':
                sql = self._convert_placeholders_to_pg(sql)
                sql += " RETURNING id_inasistencia"
                cursor.execute(sql, params)
                result = cursor.fetchone()
                return result[0] if result else None
            else:
                cursor.execute(sql, params)
                return cursor.lastrowid
    
    def query_inasistencias(self, 
                            fecha_desde: str = None,
                            fecha_hasta: str = None,
                            id_agente: int = None) -> QueryResult:
        """Query de inasistencias con filtros"""
        conditions = []
        params = []
        
        if fecha_desde:
            conditions.append("fecha_inasistencia >= ?")
            params.append(fecha_desde)
        
        if fecha_hasta:
            conditions.append("fecha_inasistencia <= ?")
            params.append(fecha_hasta)
        
        if id_agente:
            conditions.append("id_agente = ?")
            params.append(id_agente)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
            SELECT i.*, dp.nombre || ' ' || dp.apellido as agente
            FROM inasistencias i
            JOIN datos_personales dp ON i.id_agente = dp.id_agente
            WHERE {where_clause}
            ORDER BY i.fecha_inasistencia DESC
        """
        
        fecha_ref = fecha_hasta or fecha_desde
        return self.query(sql, tuple(params), fecha_ref)
    
    # =========================================================================
    # OPERACIONES DE MENÚ (ASIGNACIONES)
    # =========================================================================
    
    def insert_menu(self, data: Dict[str, Any]) -> int:
        """Inserta asignación de dispositivo"""
        fecha = data.get('fecha_asignacion')
        
        sql = """
            INSERT INTO menu 
            (id_convocatoria, id_dispositivo, id_agente, fecha_asignacion, orden)
            VALUES (?, ?, ?, ?, ?)
        """
        
        params = (
            data['id_convocatoria'],
            data['id_dispositivo'],
            data['id_agente'],
            fecha,
            data.get('orden', 1)
        )
        
        with self.get_connection(fecha) as (conn, db_type):
            cursor = conn.cursor()
            
            if db_type == 'supabase':
                sql = self._convert_placeholders_to_pg(sql)
                sql += " RETURNING id_menu"
                cursor.execute(sql, params)
                result = cursor.fetchone()
                return result[0] if result else None
            else:
                cursor.execute(sql, params)
                return cursor.lastrowid
    
    # =========================================================================
    # CONSULTAS DE TABLAS MAESTRAS (siempre en la BD actual)
    # =========================================================================
    
    def get_agentes_activos(self) -> List[Dict[str, Any]]:
        """Obtiene lista de agentes activos"""
        sql = """
            SELECT id_agente, nombre, apellido, dni, email, 
                   nombre || ' ' || apellido as nombre_completo
            FROM datos_personales
            WHERE activo = 1
            ORDER BY apellido, nombre
        """
        result = self.query(sql)
        return result.data
    
    def get_dispositivos_activos(self) -> List[Dict[str, Any]]:
        """Obtiene lista de dispositivos activos"""
        sql = """
            SELECT id_dispositivo, nombre_dispositivo, piso_dispositivo
            FROM dispositivos
            WHERE activo = 1
            ORDER BY piso_dispositivo, nombre_dispositivo
        """
        result = self.query(sql)
        return result.data
    
    def get_turnos(self) -> List[Dict[str, Any]]:
        """Obtiene lista de turnos"""
        sql = """
            SELECT id_turno, tipo_turno, descripcion,
                   hora_inicio_default, hora_fin_default, cant_horas_default
            FROM turnos
            WHERE activo = 1
            ORDER BY tipo_turno
        """
        result = self.query(sql)
        return result.data
    
    # =========================================================================
    # VISTAS ANALÍTICAS
    # =========================================================================
    
    def get_salud_sistema(self) -> Dict[str, Any]:
        """Obtiene estado de salud del sistema"""
        sql = "SELECT * FROM vista_salud_sistema"
        result = self.query_one(sql)
        return result or {}
    
    def get_convocatorias_activas(self, fecha: str = None) -> QueryResult:
        """Obtiene convocatorias vigentes"""
        fecha = fecha or datetime.now().strftime('%Y-%m-%d')
        sql = """
            SELECT * FROM vista_convocatorias_activas
            WHERE fecha_convocatoria >= ?
            ORDER BY fecha_convocatoria, hora_inicio
        """
        return self.query(sql, (fecha,), fecha)
    
    # =========================================================================
    # INFORMACIÓN Y DIAGNÓSTICO
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """
        Retorna estado actual de las conexiones
        
        Returns:
            Dict con información de estado
        """
        status = {
            'current_year': self.current_year,
            'supabase': {
                'connected': self.supabase_connected,
                'host': self._supabase_config.get('host'),
                'database': self._supabase_config.get('database')
            },
            'sqlite': {
                'base_path': str(self.sqlite_base_path),
                'db_name': self.sqlite_db_name,
                'active_connections': len(self._sqlite_connections)
            },
            'mode': 'hybrid' if self.supabase_connected else 'offline'
        }
        
        # Verificar conexiones
        if self.supabase_connected:
            try:
                cursor = self._supabase_conn.cursor()
                cursor.execute("SELECT 1")
                status['supabase']['ping'] = 'OK'
            except Exception as e:
                status['supabase']['ping'] = f'ERROR: {e}'
        
        return status
    
    def get_table_counts(self, mode: DBMode = DBMode.AUTO) -> Dict[str, int]:
        """
        Obtiene conteo de registros por tabla
        
        Returns:
            Dict tabla -> conteo
        """
        tables = [
            'datos_personales', 'dispositivos', 'turnos', 'dias',
            'planificacion', 'convocatoria', 'menu', 'saldos',
            'inasistencias', 'certificados'
        ]
        
        counts = {}
        for table in tables:
            try:
                result = self.query_one(f"SELECT COUNT(*) as n FROM {table}", mode=mode)
                counts[table] = result['n'] if result else 0
            except Exception as e:
                counts[table] = f"ERROR: {e}"
        
        return counts
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Prueba las conexiones
        
        Returns:
            Tupla (éxito, mensaje)
        """
        messages = []
        success = True
        
        # Test Supabase
        if self.supabase_connected:
            try:
                cursor = self._supabase_conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM configuracion")
                count = cursor.fetchone()[0]
                messages.append(f"✅ Supabase: OK ({count} configs)")
            except Exception as e:
                messages.append(f"❌ Supabase: {e}")
                success = False
        else:
            messages.append("⚠️ Supabase: No conectado")
        
        # Test SQLite
        try:
            conn = self._get_sqlite_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM configuracion")
            count = cursor.fetchone()[0]
            messages.append(f"✅ SQLite: OK ({count} configs)")
        except Exception as e:
            messages.append(f"❌ SQLite: {e}")
            success = False
        
        return success, "\n".join(messages)
    
    # =========================================================================
    # LIMPIEZA
    # =========================================================================
    
    def close(self):
        """Cierra todas las conexiones abiertas"""
        # Cerrar SQLite
        for conn in self._sqlite_connections.values():
            try:
                conn.close()
            except:
                pass
        self._sqlite_connections.clear()
        
        # Cerrar Supabase
        if self._supabase_conn:
            try:
                self._supabase_conn.close()
            except:
                pass
            self._supabase_conn = None
            self.supabase_connected = False
        
        logger.info("Todas las conexiones cerradas")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# =============================================================================
# FUNCIÓN DE FÁBRICA
# =============================================================================

def create_db_manager(**kwargs) -> UnifiedDBManager:
    """
    Factory function para crear manager
    
    Uso:
        db = create_db_manager()
        db = create_db_manager(current_year=2025, sqlite_base_path='data')
    """
    return UnifiedDBManager(**kwargs)


# =============================================================================
# CLI Y PRUEBAS
# =============================================================================

def main():
    """Función principal - prueba del sistema"""
    print("=" * 70)
    print("  UNIFIED DATABASE MANAGER - Test")
    print("=" * 70)
    
    # Crear manager
    db = UnifiedDBManager()
    
    # Mostrar estado
    print("\n📊 Estado del sistema:")
    status = db.get_status()
    print(f"   Año actual: {status['current_year']}")
    print(f"   Modo: {status['mode']}")
    print(f"   Supabase: {'✅ ' + status['supabase']['host'] if status['supabase']['connected'] else '❌ Offline'}")
    print(f"   SQLite: {status['sqlite']['base_path']}/{status['sqlite']['db_name']}")
    
    # Test de conexión
    print("\n🔌 Test de conexiones:")
    success, message = db.test_connection()
    print(message)
    
    # Conteos
    print("\n📈 Conteo de registros:")
    counts = db.get_table_counts()
    for table, count in counts.items():
        print(f"   {table}: {count}")
    
    # Ejemplo de query
    print("\n🔍 Ejemplo de query (convocatorias recientes):")
    try:
        result = db.query_convocatorias(
            fecha_desde=f'{db.current_year}-01-01',
            limit=5
        )
        print(f"   Fuente: {result.source_db}")
        print(f"   Tiempo: {result.execution_time_ms:.2f}ms")
        print(f"   Registros: {result.row_count}")
        
        for row in result.data[:3]:
            print(f"   - {row.get('fecha_convocatoria')}: {row.get('agente_nombre', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Cerrar
    db.close()
    
    print("\n" + "=" * 70)
    print("  ✅ Test completado")
    print("=" * 70)


if __name__ == '__main__':
    main()
