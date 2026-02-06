#!/usr/bin/env python3
"""
DASHBOARD RRHH v5.0 - Sistema Híbrido SQLite/Supabase
======================================================

MEJORAS v5.0:
- Soporte híbrido: Supabase (actual) + SQLite (histórico)
- Indicador de fuente de datos (🌐 Supabase / 💾 SQLite)
- Fallback automático a SQLite si Supabase no disponible
- Todas las features de v4.0 mantenidas
- Selector de modo de conexión

Autor: Pablo - Data Analyst
Fecha: Diciembre 2025
"""

import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import sqlite3
from pathlib import Path
import dash_bootstrap_components as dbc
import psutil
import time
from datetime import datetime
import os

# ============================================================================
# IMPORTAR UNIFIED DB MANAGER
# ============================================================================

# Intentar importar el manager unificado
try:
    from src.database.manager import UnifiedDBManager, DBMode
    UNIFIED_AVAILABLE = True
except ImportError:
    # Fallback para desarrollo local si no se ejecuta como módulo
    try:
        from src.database.manager import UnifiedDBManager, DBMode
        UNIFIED_AVAILABLE = True
    except ImportError:
        UNIFIED_AVAILABLE = False
        print("⚠️  src.database.manager no disponible, usando SQLite directo")

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Paths
BASE_PATH = Path(__file__).parent.parent
DATA_PATH = BASE_PATH / 'data'
DB_PATH = DATA_PATH / 'gestion_rrhh.db'

if not DB_PATH.exists():
    DB_PATH = Path('data/gestion_rrhh.db')

# Instancia global del manager (se inicializa después)
db_manager = None
current_db_mode = 'sqlite'  # 'supabase', 'sqlite', 'hybrid'

# PALETA FLOURISH
FLOURISH_COLORS = {
    'purple': '#7C4DFF',
    'blue': '#2196F3',
    'teal': '#00BCD4',
    'green': '#4CAF50',
    'orange': '#FF9800',
    'pink': '#E91E63',
    'red': '#F44336',
    'yellow': '#FFC107',
    'purple_light': '#B388FF',
    'blue_light': '#64B5F6',
    'teal_light': '#4DD0E1',
    'green_light': '#81C784',
    'gray_dark': '#263238',
    'gray': '#546E7A',
    'gray_light': '#B0BEC5',
    'gray_lighter': '#ECEFF1',
    'bg_primary': '#FFFFFF',
    'bg_secondary': '#FAFAFA',
    'bg_card': '#FFFFFF',
    'text_primary': '#263238',
    'text_secondary': '#546E7A',
    'text_muted': '#90A4AE'
}

COLOR_SCALE_FLOURISH = [
    '#7C4DFF', '#2196F3', '#00BCD4', '#4CAF50',
    '#FFC107', '#FF9800', '#E91E63', '#F44336'
]

# ============================================================================
# INICIALIZACIÓN DEL DB MANAGER
# ============================================================================

def init_db_manager(mode='auto'):
    """
    Inicializa el manager de base de datos
    
    Args:
        mode: 'auto', 'supabase', 'sqlite', 'offline'
    
    Returns:
        Tupla (manager, modo_activo)
    """
    global db_manager, current_db_mode
    
    if UNIFIED_AVAILABLE:
        try:
            db_mode_map = {
                'auto': DBMode.AUTO,
                'supabase': DBMode.SUPABASE,
                'sqlite': DBMode.SQLITE,
                'offline': DBMode.OFFLINE
            }
            
            db_manager = UnifiedDBManager(
                current_year=datetime.now().year,
                sqlite_base_path=str(DATA_PATH),
                auto_connect_supabase=(mode != 'offline')
            )
            
            # Determinar modo activo
            if db_manager.supabase_connected:
                current_db_mode = 'hybrid' if mode == 'auto' else 'supabase'
            else:
                current_db_mode = 'sqlite'
            
            print(f"✅ DB Manager inicializado - Modo: {current_db_mode}")
            return db_manager, current_db_mode
            
        except Exception as e:
            print(f"⚠️  Error inicializando UnifiedDBManager: {e}")
            current_db_mode = 'sqlite'
            return None, 'sqlite'
    else:
        current_db_mode = 'sqlite'
        return None, 'sqlite'


# ============================================================================
# CLASE PARA MONITOREO DE RECURSOS
# ============================================================================

class ResourceMonitor:
    """Monitorea uso de recursos del sistema"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.start_time = time.time()
        self.query_times = []
        self.query_sources = {'supabase': 0, 'sqlite': 0}
    
    def get_memory_usage(self):
        return self.process.memory_info().rss / 1024 / 1024
    
    def get_cpu_usage(self):
        return self.process.cpu_percent(interval=0.1)
    
    def get_uptime(self):
        elapsed = time.time() - self.start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def record_query_time(self, query_time, source='sqlite'):
        self.query_times.append(query_time)
        self.query_sources[source] = self.query_sources.get(source, 0) + 1
        if len(self.query_times) > 100:
            self.query_times.pop(0)
    
    def get_avg_query_time(self):
        if not self.query_times:
            return 0
        return sum(self.query_times) / len(self.query_times)
    
    def get_stats(self):
        return {
            'memory_mb': self.get_memory_usage(),
            'cpu_percent': self.get_cpu_usage(),
            'uptime': self.get_uptime(),
            'avg_query_ms': self.get_avg_query_time() * 1000,
            'total_queries': len(self.query_times),
            'query_sources': self.query_sources
        }

resource_monitor = ResourceMonitor()

# ============================================================================
# QUERIES COMPATIBLES SQLITE/POSTGRESQL
# ============================================================================

def get_year_filter_sql(year, year_field, db_type='sqlite'):
    """
    Genera filtro de año compatible con SQLite y PostgreSQL
    """
    if not year or year == 'all':
        return ''
    
    if year_field == 'anio':
        return f"s.anio = {year}"
    
    if db_type == 'sqlite':
        return f"strftime('%Y', {year_field}) = '{year}'"
    else:  # PostgreSQL
        return f"TO_CHAR({year_field}, 'YYYY') = '{year}'"


def get_month_filter_sql(mes, year_field, db_type='sqlite'):
    """
    Genera filtro de mes compatible con SQLite y PostgreSQL
    """
    if not mes or mes == 'all':
        return ''
    
    mes_num = mes.split(' - ')[0] if ' - ' in str(mes) else str(mes).zfill(2)
    
    if year_field == 'anio':
        return f"s.mes = {int(mes_num)}"
    
    if db_type == 'sqlite':
        return f"strftime('%m', {year_field}) = '{mes_num}'"
    else:  # PostgreSQL
        return f"TO_CHAR({year_field}, 'MM') = '{mes_num}'"


TABLE_QUERIES = {
    'convocatoria': {
        'name': '📋 Convocatorias',
        'year_field': 'c.fecha_convocatoria',
        'query_sqlite': """
            SELECT 
                c.id_convocatoria,
                c.fecha_convocatoria,
                dp.nombre || ' ' || dp.apellido as agente,
                t.tipo_turno,
                t.hora_inicio as hora_inicio,
                t.hora_fin as hora_fin,
                t.cant_horas as horas,
                c.estado,
                p.cant_residentes_plan as residentes,
                p.cant_visit as visitantes,
                c.motivo_cambio
            FROM convocatoria c
            JOIN datos_personales dp ON c.id_agente = dp.id_agente
            JOIN turnos t ON c.id_turno = t.id_turno
            JOIN planificacion p ON c.id_plani = p.id_plani
            {where_clause}
            ORDER BY c.fecha_convocatoria DESC, dp.apellido
        """,
        'query_postgres': """
            SELECT 
                c.id_convocatoria,
                c.fecha_convocatoria::text as fecha_convocatoria,
                dp.nombre || ' ' || dp.apellido as agente,
                t.tipo_turno,
                t.hora_inicio::text as hora_inicio,
                t.hora_fin::text as hora_fin,
                t.cant_horas as horas,
                c.estado,
                p.cant_residentes_plan as residentes,
                p.cant_visit as visitantes,
                c.motivo_cambio
            FROM convocatoria c
            JOIN datos_personales dp ON c.id_agente = dp.id_agente
            JOIN turnos t ON c.id_turno = t.id_turno
            JOIN planificacion p ON c.id_plani = p.id_plani
            {where_clause}
            ORDER BY c.fecha_convocatoria DESC, dp.apellido
        """
    },
    'datos_personales': {
        'name': '👤 Datos Personales',
        'year_field': None,
        'query_sqlite': """
            SELECT 
                id_agente, nombre, apellido, dni, fecha_nacimiento,
                email, telefono, domicilio,
                CASE WHEN activo = 1 THEN 'Activo' ELSE 'Inactivo' END as estado,
                fecha_alta, fecha_baja
            FROM datos_personales
            ORDER BY apellido, nombre
        """,
        'query_postgres': """
            SELECT 
                id_agente, nombre, apellido, dni, 
                fecha_nacimiento::text as fecha_nacimiento,
                email, telefono, domicilio,
                CASE WHEN activo THEN 'Activo' ELSE 'Inactivo' END as estado,
                fecha_alta::text as fecha_alta, 
                fecha_baja::text as fecha_baja
            FROM datos_personales
            ORDER BY apellido, nombre
        """
    },
    'saldos': {
        'name': '⏱️ Saldos de Horas',
        'year_field': 'anio',
        'query_sqlite': """
            SELECT 
                dp.nombre || ' ' || dp.apellido as agente,
                s.mes, s.anio, s.horas_mes, s.horas_anuales,
                CASE 
                    WHEN s.horas_mes < 60 THEN 'BAJO ⚠️'
                    WHEN s.horas_mes >= 90 THEN 'ALTO 📈'
                    ELSE 'NORMAL ✓'
                END as nivel,
                s.fecha_actualizacion
            FROM saldos s
            JOIN datos_personales dp ON s.id_agente = dp.id_agente
            WHERE dp.activo = 1
            {additional_filters}
            ORDER BY s.anio DESC, s.mes DESC, dp.apellido
        """,
        'query_postgres': """
            SELECT 
                dp.nombre || ' ' || dp.apellido as agente,
                s.mes, s.anio, s.horas_mes, s.horas_anuales,
                CASE 
                    WHEN s.horas_mes < 60 THEN 'BAJO ⚠️'
                    WHEN s.horas_mes >= 90 THEN 'ALTO 📈'
                    ELSE 'NORMAL ✓'
                END as nivel,
                s.fecha_actualizacion::text as fecha_actualizacion
            FROM saldos s
            JOIN datos_personales dp ON s.id_agente = dp.id_agente
            WHERE dp.activo = true
            {additional_filters}
            ORDER BY s.anio DESC, s.mes DESC, dp.apellido
        """
    },
    'inasistencias': {
        'name': '🚫 Inasistencias',
        'year_field': 'i.fecha_inasistencia',
        'query_sqlite': """
            SELECT 
                i.id_inasistencia,
                dp.nombre || ' ' || dp.apellido as agente,
                i.fecha_inasistencia, i.motivo, i.estado,
                CASE WHEN i.requiere_certificado = 1 THEN 'Sí' ELSE 'No' END as requiere_certificado,
                i.observaciones
            FROM inasistencias i
            JOIN datos_personales dp ON i.id_agente = dp.id_agente
            {where_clause}
            ORDER BY i.fecha_inasistencia DESC
        """,
        'query_postgres': """
            SELECT 
                i.id_inasistencia,
                dp.nombre || ' ' || dp.apellido as agente,
                i.fecha_inasistencia::text as fecha_inasistencia, 
                i.motivo, i.estado,
                CASE WHEN i.requiere_certificado THEN 'Sí' ELSE 'No' END as requiere_certificado,
                i.observaciones
            FROM inasistencias i
            JOIN datos_personales dp ON i.id_agente = dp.id_agente
            {where_clause}
            ORDER BY i.fecha_inasistencia DESC
        """
    },
    'menu': {
        'name': '🖥️ Asignaciones',
        'year_field': 'm.fecha_asignacion',
        'query_sqlite': """
            SELECT 
                m.id_menu,
                dp.nombre || ' ' || dp.apellido as agente,
                d.nombre_dispositivo as dispositivo,
                d.piso_dispositivo as piso,
                m.fecha_asignacion,
                t.tipo_turno
            FROM menu m
            JOIN datos_personales dp ON m.id_agente = dp.id_agente
            JOIN dispositivos d ON m.id_dispositivo = d.id_dispositivo
            JOIN convocatoria c ON m.id_convocatoria = c.id_convocatoria
            JOIN turnos t ON c.id_turno = t.id_turno
            {where_clause}
            ORDER BY m.fecha_asignacion DESC, dp.apellido
        """,
        'query_postgres': """
            SELECT 
                m.id_menu,
                dp.nombre || ' ' || dp.apellido as agente,
                d.nombre_dispositivo as dispositivo,
                d.piso_dispositivo as piso,
                m.fecha_asignacion::text as fecha_asignacion,
                t.tipo_turno
            FROM menu m
            JOIN datos_personales dp ON m.id_agente = dp.id_agente
            JOIN dispositivos d ON m.id_dispositivo = d.id_dispositivo
            JOIN convocatoria c ON m.id_convocatoria = c.id_convocatoria
            JOIN turnos t ON c.id_turno = t.id_turno
            {where_clause}
            ORDER BY m.fecha_asignacion DESC, dp.apellido
        """
    },
    'dispositivos': {
        'name': '🏢 Dispositivos',
        'year_field': None,
        'query_sqlite': """
            SELECT 
                d.id_dispositivo, d.nombre_dispositivo, d.piso_dispositivo,
                CASE WHEN d.activo = 1 THEN '✓ Activo' ELSE '✗ Inactivo' END as estado,
                COUNT(DISTINCT m.id_agente) as agentes,
                COUNT(m.id_menu) as asignaciones,
                MAX(m.fecha_asignacion) as ultima_asignacion
            FROM dispositivos d
            LEFT JOIN menu m ON d.id_dispositivo = m.id_dispositivo
            GROUP BY d.id_dispositivo
            ORDER BY d.piso_dispositivo, d.nombre_dispositivo
        """,
        'query_postgres': """
            SELECT 
                d.id_dispositivo, d.nombre_dispositivo, d.piso_dispositivo,
                CASE WHEN d.activo THEN '✓ Activo' ELSE '✗ Inactivo' END as estado,
                COUNT(DISTINCT m.id_agente) as agentes,
                COUNT(m.id_menu) as asignaciones,
                MAX(m.fecha_asignacion)::text as ultima_asignacion
            FROM dispositivos d
            LEFT JOIN menu m ON d.id_dispositivo = m.id_dispositivo
            GROUP BY d.id_dispositivo
            ORDER BY d.piso_dispositivo, d.nombre_dispositivo
        """
    },
    'turnos': {
        'name': '🕐 Turnos',
        'year_field': None,
        'query_sqlite': """
            SELECT 
                t.tipo_turno, t.turno_notas as descripcion,
                t.hora_inicio, t.hora_fin, t.cant_horas,
                CASE WHEN t.activo = 1 THEN '✓' ELSE '✗' END as activo
            FROM turnos t
            ORDER BY t.tipo_turno
        """,
        'query_postgres': """
            SELECT 
                t.tipo_turno, t.turno_notas as descripcion,
                t.hora_inicio::text as hora_inicio, 
                t.hora_fin::text as hora_fin, 
                t.cant_horas,
                CASE WHEN t.activo THEN '✓' ELSE '✗' END as activo
            FROM turnos t
            ORDER BY t.tipo_turno
        """
    },
    'system_errors': {
        'name': '⚠️ Errores del Sistema',
        'year_field': 'timestamp',
        'query_sqlite': """
            SELECT 
                id_error, timestamp, error_type, component,
                substr(error_message, 1, 50) as mensaje,
                severity,
                CASE WHEN resolved = 1 THEN '✓' ELSE '✗' END as resuelto
            FROM system_errors
            {where_clause}
            ORDER BY resolved ASC, timestamp DESC
            LIMIT 100
        """,
        'query_postgres': """
            SELECT 
                id_error, timestamp::text as timestamp, error_type, component,
                LEFT(error_message, 50) as mensaje,
                severity,
                CASE WHEN resolved THEN '✓' ELSE '✗' END as resuelto
            FROM system_errors
            {where_clause}
            ORDER BY resolved ASC, timestamp DESC
            LIMIT 100
        """
    }
}


# ============================================================================
# FUNCIONES DE DATOS
# ============================================================================

def get_sqlite_connection():
    """Conexión directa a SQLite (fallback)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def execute_query(table_key, year=None, agente_filter=None, mes_filter=None):
    """
    Ejecuta query usando el manager apropiado
    
    Returns:
        Tupla (DataFrame, source_db)
    """
    global db_manager, current_db_mode
    start_time = time.time()
    
    table_config = TABLE_QUERIES.get(table_key)
    if not table_config:
        return pd.DataFrame(), 'error'
    
    year_field = table_config.get('year_field')
    
    # Determinar qué BD usar
    use_supabase = False
    if db_manager and current_db_mode in ('hybrid', 'supabase'):
        # CORRECCIÓN: Usar Supabase para 2025 en adelante (punto de corte de migración)
        # Si estamos en 2026, 2025 sigue estando en la nube, no en SQLite local.
        cutoff_year = 2025
        
        if year is None or year == 'all':
            use_supabase = db_manager.supabase_connected
        elif str(year).isdigit() and int(year) >= cutoff_year:
            use_supabase = db_manager.supabase_connected
    
    try:
        if use_supabase:
            # Query en PostgreSQL
            query = table_config.get('query_postgres', table_config.get('query_sqlite'))
            db_type = 'postgres'
        else:
            # Query en SQLite
            query = table_config.get('query_sqlite')
            db_type = 'sqlite'
        
        # Construir filtros
        filters = []
        
        if year and year != 'all' and year_field:
            filters.append(get_year_filter_sql(year, year_field, db_type))
        
        if mes_filter and mes_filter != 'all' and year_field:
            filters.append(get_month_filter_sql(mes_filter, year_field, db_type))
        
        if agente_filter and agente_filter != 'all':
            agente_safe = agente_filter.replace("'", "''")
            filters.append(f"(dp.nombre || ' ' || dp.apellido) = '{agente_safe}'")
        
        # Aplicar filtros a query
        if filters:
            filter_clause = ' AND '.join(filters)
            if '{where_clause}' in query:
                query = query.replace('{where_clause}', f"WHERE {filter_clause}")
            elif '{additional_filters}' in query:
                query = query.replace('{additional_filters}', f"AND {filter_clause}")
        else:
            query = query.replace('{where_clause}', '')
            query = query.replace('{additional_filters}', '')
        
        # Ejecutar
        if use_supabase:
            result = db_manager.query(query, mode=DBMode.SUPABASE)
            df = pd.DataFrame(result.data) if result.data else pd.DataFrame()
            source = 'supabase'
        else:
            conn = get_sqlite_connection()
            df = pd.read_sql_query(query, conn)
            conn.close()
            source = 'sqlite'
        
        # Registrar tiempo
        query_time = time.time() - start_time
        resource_monitor.record_query_time(query_time, source)
        
        return df, source
        
    except Exception as e:
        print(f"❌ Error en query {table_key} ({'Postgres' if use_supabase else 'SQLite'}): {e}")
        # Fallback a SQLite
        try:
            query = table_config.get('query_sqlite', '')
            query = query.replace('{where_clause}', '')
            query = query.replace('{additional_filters}', '')
            
            conn = get_sqlite_connection()
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            return df, 'sqlite (fallback)'
        except Exception as e2:
            print(f"Error en fallback: {e2}")
            return pd.DataFrame(), 'error'


def get_available_years():
    """Obtener años disponibles"""
    try:
        df, _ = execute_query('convocatoria')
        if 'fecha_convocatoria' in df.columns:
            years = pd.to_datetime(df['fecha_convocatoria'], errors='coerce').dt.year.dropna().unique()
            return sorted([int(y) for y in years], reverse=True)
    except:
        pass
    return [datetime.now().year]


def get_agentes_list():
    """Obtener lista de agentes"""
    try:
        df, _ = execute_query('datos_personales')
        if 'agente' in df.columns:
            return df['agente'].dropna().tolist()
        elif 'nombre' in df.columns and 'apellido' in df.columns:
            return (df['nombre'] + ' ' + df['apellido']).dropna().tolist()
    except:
        pass
    return []


def get_meses_list():
    """Lista de meses"""
    return [
        '01 - Enero', '02 - Febrero', '03 - Marzo', '04 - Abril',
        '05 - Mayo', '06 - Junio', '07 - Julio', '08 - Agosto',
        '09 - Septiembre', '10 - Octubre', '11 - Noviembre', '12 - Diciembre'
    ]


def get_column_values(df, column_name, max_values=100):
    """Obtener valores únicos de columna para dropdown"""
    if column_name not in df.columns:
        return []
    
    unique_values = df[column_name].dropna().unique()
    if len(unique_values) > max_values:
        value_counts = df[column_name].value_counts().head(max_values)
        return value_counts.index.tolist()
    
    return sorted([str(v) for v in unique_values])


def get_connection_status():
    """Obtiene estado de conexiones"""
    global db_manager, current_db_mode
    
    status = {
        'mode': current_db_mode,
        'sqlite': True,  # SQLite siempre disponible
        'supabase': False,
        'icon': '💾'
    }
    
    if db_manager:
        status['supabase'] = db_manager.supabase_connected
        if status['supabase']:
            status['icon'] = '🌐' if current_db_mode == 'supabase' else '🔄'
    
    return status


# ============================================================================
# FUNCIONES DE FILTRADO
# ============================================================================

def filter_dataframe(df, filter_col, filter_vals, sort_col, sort_asc):
    """Aplica filtros y ordenamiento al DataFrame"""
    if filter_col and filter_vals and filter_col in df.columns:
        df = df[df[filter_col].isin(filter_vals)]
    
    if sort_col and sort_col in df.columns:
        ascending = True if sort_asc == 'asc' else False
        df = df.sort_values(by=sort_col, ascending=ascending)
        
    return df


# ============================================================================
# FUNCIONES DE INASISTENCIAS
# ============================================================================

def get_inasistencias_data():
    """Obtener datos de inasistencias para gráficos"""
    try:
        df, source = execute_query('inasistencias')
        
        result = {
            'total': len(df),
            'por_tipo': df['motivo'].value_counts().reset_index() if 'motivo' in df.columns else pd.DataFrame(),
            'por_estado': df['estado'].value_counts().reset_index() if 'estado' in df.columns else pd.DataFrame(),
            'source': source
        }
        
        if 'motivo' in result['por_tipo'].columns:
            result['por_tipo'].columns = ['motivo', 'cantidad']
        if 'estado' in result['por_estado'].columns:
            result['por_estado'].columns = ['estado', 'cantidad']
        
        return result
    except Exception as e:
        print(f"Error en inasistencias: {e}")
        return {'total': 0, 'por_tipo': pd.DataFrame(), 'por_estado': pd.DataFrame(), 'source': 'error'}


def create_inasistencias_charts(data):
    """Crear gráficos de inasistencias"""
    charts = {}
    
    # Total
    fig_total = go.Figure(go.Indicator(
        mode="number",
        value=data['total'],
        title={'text': "Total Inasistencias", 'font': {'size': 18}},
        number={'font': {'size': 56, 'color': FLOURISH_COLORS['purple']}}
    ))
    fig_total.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
    charts['total'] = fig_total
    
    # Por tipo
    if not data['por_tipo'].empty:
        fig_tipo = px.pie(
            data['por_tipo'], 
            values='cantidad', 
            names='motivo',
            title='Por Motivo',
            color_discrete_sequence=COLOR_SCALE_FLOURISH
        )
        fig_tipo.update_layout(height=300)
        charts['por_tipo'] = fig_tipo
    
    # Por estado
    if not data['por_estado'].empty:
        fig_estado = px.bar(
            data['por_estado'],
            x='estado',
            y='cantidad',
            title='Por Estado',
            color='estado',
            color_discrete_sequence=COLOR_SCALE_FLOURISH
        )
        fig_estado.update_layout(height=300)
        charts['por_estado'] = fig_estado
    
    return charts


# ============================================================================
# APLICACIÓN DASH
# ============================================================================

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Dashboard RRHH v5.0 - Híbrido"

# CSS personalizado
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { font-family: 'Inter', sans-serif; }
            body { background: #FAFAFA; margin: 0; padding: 0; }
            .main-header {
                background: linear-gradient(135deg, #7C4DFF 0%, #2196F3 100%);
                color: white;
                padding: 20px 40px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .main-header h1 { margin: 0; font-size: 24px; font-weight: 600; }
            .main-header p { margin: 5px 0 0 0; opacity: 0.9; font-size: 13px; }
            .connection-badge {
                background: rgba(255,255,255,0.2);
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 500;
            }
            .dash-tab {
                font-size: 13px !important;
                font-weight: 500 !important;
                padding: 10px 20px !important;
                border: none !important;
            }
            .dash-tab--selected {
                color: #7C4DFF !important;
                border-bottom: 3px solid #7C4DFF !important;
            }
            #tab-content {
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.08);
                margin: 20px;
                padding: 20px;
            }
            .table-container {
                border: 1px solid #ECEFF1;
                border-radius: 8px;
                padding: 15px;
                background: white;
            }
            .controls-row {
                display: flex;
                gap: 10px;
                margin-bottom: 15px;
                align-items: center;
                flex-wrap: wrap;
            }
            .control-item {
                display: flex;
                flex-direction: column;
                gap: 5px;
            }
            .control-label {
                font-size: 12px;
                font-weight: 500;
                color: #546E7A;
            }
            .source-badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 600;
            }
            .source-supabase {
                background: #E3F2FD;
                color: #1976D2;
            }
            .source-sqlite {
                background: #E8F5E9;
                color: #388E3C;
            }
            .resource-monitor {
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: white;
                border: 1px solid #ECEFF1;
                border-radius: 8px;
                padding: 10px 15px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.15);
                font-size: 11px;
                z-index: 1000;
                min-width: 200px;
            }
            .resource-item {
                display: flex;
                justify-content: space-between;
                padding: 3px 0;
            }
            .resource-label {
                color: #546E7A;
                font-weight: 500;
            }
            .resource-value {
                color: #263238;
                font-weight: 600;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Layout
app.layout = html.Div([
    # Header con indicador de conexión
    html.Div([
        html.Div([
            html.H1("Dashboard RRHH v5.0"),
            html.P("Sistema Híbrido - SQLite + Supabase")
        ]),
        html.Div([
            dbc.Switch(
                id='monitor-toggle',
                label="Monitor",
                value=False,
                style={'color': 'white', 'marginRight': '20px', 'fontWeight': '500'}
            ),
            html.Div(id='connection-badge', className='connection-badge')
        ], style={'display': 'flex', 'alignItems': 'center'})
    ], className='main-header'),
    
    # Tabs
    dcc.Tabs(id='tabs', value='tablas', children=[
        dcc.Tab(label='📊 Inasistencias', value='inasistencias'),
        dcc.Tab(label='📋 Explorador de Tablas', value='tablas'),
        dcc.Tab(label='⚙️ Configuración', value='config'),
    ]),
    
    # Contenido
    html.Div(id='tab-content'),
    
    # Monitor de recursos
    html.Div(id='resource-monitor', className='resource-monitor'),
    
    # Interval para actualizar
    dcc.Interval(id='interval-monitor', interval=2000, n_intervals=0),
    dcc.Interval(id='interval-connection', interval=10000, n_intervals=0)
])


# Callback para badge de conexión
@app.callback(
    Output('connection-badge', 'children'),
    Input('interval-connection', 'n_intervals')
)
def update_connection_badge(n):
    status = get_connection_status()
    
    if status['supabase']:
        if status['mode'] == 'hybrid':
            return "🔄 Híbrido (Supabase + SQLite)"
        else:
            return "🌐 Supabase"
    else:
        return "💾 SQLite Local"


# Callback para monitor de recursos
@app.callback(
    [Output('resource-monitor', 'children'),
     Output('resource-monitor', 'style')],
    [Input('interval-monitor', 'n_intervals'),
     Input('monitor-toggle', 'value')]
)
def update_resource_monitor(n, show_monitor):
    if not show_monitor:
        return None, {'display': 'none'}
        
    stats = resource_monitor.get_stats()
    
    memory_color = FLOURISH_COLORS['green'] if stats['memory_mb'] < 200 else FLOURISH_COLORS['orange'] if stats['memory_mb'] < 500 else FLOURISH_COLORS['red']
    
    content = html.Div([
        html.Div("📊 Monitor", style={'fontWeight': '600', 'marginBottom': '8px', 'color': FLOURISH_COLORS['purple']}),
        html.Div([
            html.Span("Memoria:", className='resource-label'),
            html.Span(f"{stats['memory_mb']:.1f} MB", className='resource-value', style={'color': memory_color})
        ], className='resource-item'),
        html.Div([
            html.Span("Query Prom:", className='resource-label'),
            html.Span(f"{stats['avg_query_ms']:.0f} ms", className='resource-value')
        ], className='resource-item'),
        html.Div([
            html.Span("Supabase:", className='resource-label'),
            html.Span(str(stats['query_sources'].get('supabase', 0)), className='resource-value')
        ], className='resource-item'),
        html.Div([
            html.Span("SQLite:", className='resource-label'),
            html.Span(str(stats['query_sources'].get('sqlite', 0)), className='resource-value')
        ], className='resource-item'),
        html.Div([
            html.Span("Uptime:", className='resource-label'),
            html.Span(stats['uptime'], className='resource-value')
        ], className='resource-item'),
    ])
    
    return content, {}


# Callback principal de contenido
@app.callback(
    Output('tab-content', 'children'),
    Input('tabs', 'value')
)
def render_content(tab):
    if tab == 'inasistencias':
        try:
            data = get_inasistencias_data()
            charts = create_inasistencias_charts(data)
            
            source_class = 'source-supabase' if 'supabase' in data['source'] else 'source-sqlite'
            source_text = '🌐 Supabase' if 'supabase' in data['source'] else '💾 SQLite'
            
            return html.Div([
                html.Div([
                    html.H2("Inasistencias", style={'display': 'inline-block'}),
                    html.Span(source_text, className=f'source-badge {source_class}', style={'marginLeft': '15px'})
                ]),
                dcc.Graph(figure=charts.get('total', go.Figure())),
                html.Div([
                    html.Div([dcc.Graph(figure=charts.get('por_tipo', go.Figure()))], style={'width': '50%', 'display': 'inline-block'}),
                    html.Div([dcc.Graph(figure=charts.get('por_estado', go.Figure()))], style={'width': '50%', 'display': 'inline-block'})
                ]) if 'por_tipo' in charts else None
            ])
        except Exception as e:
            return html.Div(f"Error: {e}")
    
    elif tab == 'tablas':
        table_options = [{'label': v['name'], 'value': k} for k, v in TABLE_QUERIES.items()]
        years = get_available_years()
        year_options = [{'label': 'Todos', 'value': 'all'}] + [{'label': str(y), 'value': y} for y in years]
        current_year = years[0] if years else datetime.now().year
        
        agentes = get_agentes_list()
        agente_options = [{'label': 'Todos', 'value': 'all'}] + [{'label': a, 'value': a} for a in agentes[:100]]
        
        meses = get_meses_list()
        mes_options = [{'label': 'Todos', 'value': 'all'}] + [{'label': m, 'value': m} for m in meses]
        
        return html.Div([
            html.H2("Explorador de Tablas", style={'marginBottom': '20px'}),
            
            # Control de doble tabla
            dbc.Checkbox(
                id='toggle-table-2',
                label="Agregar Tabla Comparativa",
                value=False,
                style={'marginBottom': '20px', 'fontWeight': '500'}
            ),
            
            # Layout horizontal
            html.Div([
                # Tabla izquierda
                html.Div([
                    html.Div([
                        html.Div([
                            html.Div([
                                html.Label("📊 Tabla:", className='control-label'),
                                dcc.Dropdown(id='table-dropdown-1', options=table_options, value='convocatoria', clearable=False, style={'width': '200px'})
                            ], className='control-item'),
                            html.Div([
                                html.Label("📅 Año:", className='control-label'),
                                dcc.Dropdown(id='year-dropdown-1', options=year_options, value=current_year, clearable=False, style={'width': '120px'})
                            ], className='control-item'),
                            html.Div([
                                html.Label("📄 Paginación:", className='control-label'),
                                dcc.Dropdown(id='rows-dropdown-1', options=[{'label': str(n), 'value': n} for n in [10, 20, 50, 100]], value=20, clearable=False, style={'width': '80px'})
                            ], className='control-item')
                        ], className='controls-row'),
                        
                        # Filtros Avanzados Tabla 1
                        html.Div([
                            html.Label("🔍 Filtros Avanzados:", className='control-label', style={'fontWeight': 'bold'}),
                            html.Div([
                                dcc.Dropdown(id='filter-col-1', placeholder="Filtrar por columna...", style={'width': '200px'}),
                                dcc.Dropdown(id='filter-val-1', placeholder="Seleccionar valores...", multi=True, style={'width': '300px'}),
                                dcc.Dropdown(id='sort-col-1', placeholder="Ordenar por...", style={'width': '200px'}),
                                dbc.RadioItems(
                                    id='sort-asc-1',
                                    options=[{'label': 'Asc', 'value': 'asc'}, {'label': 'Desc', 'value': 'desc'}],
                                    value='asc',
                                    inline=True,
                                    style={'fontSize': '12px', 'marginTop': '5px'}
                                ),
                            ], className='controls-row')
                        ], style={'backgroundColor': '#F5F5F5', 'padding': '10px', 'borderRadius': '5px', 'marginBottom': '10px'}),

                        html.Div(id='table-info-1', style={'fontSize': '12px', 'color': FLOURISH_COLORS['text_secondary'], 'marginBottom': '10px'}),
                        html.Div(id='table-container-1')
                    ], className='table-container'),
                ], id='container-1', style={'width': '100%', 'display': 'inline-block', 'verticalAlign': 'top', 'transition': 'width 0.3s'}),
                
                # Tabla derecha (con filtros adicionales)
                html.Div(id='container-2', children=[
                    html.Div([
                        html.Div([
                            html.Div([
                                html.Label("📊 Tabla:", className='control-label'),
                                dcc.Dropdown(id='table-dropdown-2', options=table_options, value='saldos', clearable=False, style={'width': '200px'})
                            ], className='control-item'),
                            html.Div([
                                html.Label("📅 Año:", className='control-label'),
                                dcc.Dropdown(id='year-dropdown-2', options=year_options, value=current_year, clearable=False, style={'width': '120px'})
                            ], className='control-item'),
                            html.Div([
                                html.Label("📄 Paginación:", className='control-label'),
                                dcc.Dropdown(id='rows-dropdown-2', options=[{'label': str(n), 'value': n} for n in [10, 20, 50, 100]], value=20, clearable=False, style={'width': '80px'})
                            ], className='control-item')
                        ], className='controls-row'),
                        
                        # Filtros Avanzados Tabla 2
                        html.Div([
                            html.Label("🔍 Filtros Avanzados:", className='control-label', style={'fontWeight': 'bold'}),
                            html.Div([
                                dcc.Dropdown(id='filter-col-2', placeholder="Filtrar por columna...", style={'width': '200px'}),
                                dcc.Dropdown(id='filter-val-2', placeholder="Seleccionar valores...", multi=True, style={'width': '300px'}),
                                dcc.Dropdown(id='sort-col-2', placeholder="Ordenar por...", style={'width': '200px'}),
                                dbc.RadioItems(
                                    id='sort-asc-2',
                                    options=[{'label': 'Asc', 'value': 'asc'}, {'label': 'Desc', 'value': 'desc'}],
                                    value='asc',
                                    inline=True,
                                    style={'fontSize': '12px', 'marginTop': '5px'}
                                ),
                            ], className='controls-row')
                        ], style={'backgroundColor': '#F5F5F5', 'padding': '10px', 'borderRadius': '5px', 'marginBottom': '10px'}),

                        html.Div(id='table-info-2', style={'fontSize': '12px', 'color': FLOURISH_COLORS['text_secondary'], 'marginBottom': '10px'}),
                        html.Div(id='table-container-2')
                    ], className='table-container')
                ], style={'width': '49%', 'display': 'none', 'verticalAlign': 'top', 'float': 'right', 'transition': 'width 0.3s'})
            ])
        ])
    
    elif tab == 'config':
        status = get_connection_status()
        
        return html.Div([
            html.H2("Configuración de Conexión"),
            html.Div([
                html.H4("Estado Actual"),
                html.P(f"Modo: {status['mode'].upper()}"),
                html.P(f"SQLite: {'✅ Disponible' if status['sqlite'] else '❌'}"),
                html.P(f"Supabase: {'✅ Conectado' if status['supabase'] else '❌ No conectado'}"),
                html.Hr(),
                html.H4("Información"),
                html.P("• Datos del año actual: Supabase (PostgreSQL)"),
                html.P("• Datos históricos: SQLite local"),
                html.P("• Si Supabase no está disponible, usa SQLite automáticamente"),
            ], style={'padding': '20px', 'background': '#f5f5f5', 'borderRadius': '8px'})
        ])


# Callback para mostrar/ocultar segunda tabla
@app.callback(
    [Output('container-1', 'style'), Output('container-2', 'style')],
    Input('toggle-table-2', 'value')
)
def toggle_tables(show_second):
    if show_second:
        return {'width': '49%', 'display': 'inline-block', 'verticalAlign': 'top', 'transition': 'width 0.3s'}, \
               {'width': '49%', 'display': 'inline-block', 'verticalAlign': 'top', 'float': 'right', 'transition': 'width 0.3s'}
    else:
        return {'width': '100%', 'display': 'inline-block', 'verticalAlign': 'top', 'transition': 'width 0.3s'}, \
               {'display': 'none'}


# Callbacks para tablas
@app.callback(
    [Output('table-container-1', 'children'), Output('table-info-1', 'children'),
     Output('filter-col-1', 'options'), Output('filter-val-1', 'options'), Output('sort-col-1', 'options')],
    [Input('table-dropdown-1', 'value'), Input('year-dropdown-1', 'value'), Input('rows-dropdown-1', 'value'),
     Input('filter-col-1', 'value'), Input('filter-val-1', 'value'), 
     Input('sort-col-1', 'value'), Input('sort-asc-1', 'value')]
)
def update_table_1(table_key, year, rows, filter_col, filter_vals, sort_col, sort_asc):
    if not table_key:
        return html.Div("Selecciona una tabla"), "", [], [], []
    
    try:
        df, source = execute_query(table_key, year=year)
        
        if df.empty:
            return html.Div("⚠️ Sin datos", style={'padding': '20px'}), "", [], [], []
        
        # Opciones de columnas para filtros
        col_options = [{'label': c, 'value': c} for c in df.columns]
        
        # Opciones de valores para el filtro seleccionado
        val_options = []
        if filter_col and filter_col in df.columns:
            unique_vals = sorted([str(x) for x in df[filter_col].unique() if pd.notna(x)])
            val_options = [{'label': v, 'value': v} for v in unique_vals]
        
        # Aplicar filtros y ordenamiento
        df_filtered = filter_dataframe(df, filter_col, filter_vals, sort_col, sort_asc)
        
        source_icon = '🌐' if 'supabase' in source else '💾'
        info = f"{source_icon} {len(df_filtered)} registros (Total: {len(df)}) • {source}"
        
        table = dash_table.DataTable(
            data=df_filtered.to_dict('records'),
            columns=[{'name': c, 'id': c} for c in df_filtered.columns],
            style_table={'overflowX': 'auto', 'maxHeight': '500px'},
            style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '12px'},
            style_header={'backgroundColor': FLOURISH_COLORS['purple'], 'color': 'white', 'fontWeight': '600'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#fafafa'}],
            page_size=rows,
            page_action='native', # Paginación en frontend
            sort_action='native',
            filter_action='native',
            export_format='xlsx'
        )
        
        return table, info, col_options, val_options, col_options
    except Exception as e:
        return html.Div(f"❌ Error: {e}"), "", [], [], []


@app.callback(
    [Output('table-container-2', 'children'), Output('table-info-2', 'children'),
     Output('filter-col-2', 'options'), Output('filter-val-2', 'options'), Output('sort-col-2', 'options')],
    [Input('table-dropdown-2', 'value'), Input('year-dropdown-2', 'value'), Input('rows-dropdown-2', 'value'),
     Input('filter-col-2', 'value'), Input('filter-val-2', 'value'), 
     Input('sort-col-2', 'value'), Input('sort-asc-2', 'value')]
)
def update_table_2(table_key, year, rows, filter_col, filter_vals, sort_col, sort_asc):
    if not table_key:
        return html.Div("Selecciona una tabla"), "", [], [], []
    
    try:
        df, source = execute_query(table_key, year=year)
        
        if df.empty:
            return html.Div("⚠️ Sin datos", style={'padding': '20px'}), "", [], [], []
        
        # Opciones de columnas
        col_options = [{'label': c, 'value': c} for c in df.columns]
        
        # Opciones de valores
        val_options = []
        if filter_col and filter_col in df.columns:
            unique_vals = sorted([str(x) for x in df[filter_col].unique() if pd.notna(x)])
            val_options = [{'label': v, 'value': v} for v in unique_vals]
        
        # Aplicar filtros
        df_filtered = filter_dataframe(df, filter_col, filter_vals, sort_col, sort_asc)
        
        source_icon = '🌐' if 'supabase' in source else '💾'
        info = f"{source_icon} {len(df_filtered)} registros (Total: {len(df)}) • {source}"
        
        table = dash_table.DataTable(
            data=df_filtered.to_dict('records'),
            columns=[{'name': c, 'id': c} for c in df_filtered.columns],
            style_table={'overflowX': 'auto', 'maxHeight': '500px'},
            style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '12px'},
            style_header={'backgroundColor': FLOURISH_COLORS['blue'], 'color': 'white', 'fontWeight': '600'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#fafafa'}],
            page_size=rows,
            page_action='native',
            sort_action='native',
            filter_action='native',
            export_format='xlsx'
        )
        
        return table, info, col_options, val_options, col_options
    except Exception as e:
        return html.Div(f"❌ Error: {e}"), "", [], [], []


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("  DASHBOARD RRHH v5.0 - Sistema Híbrido")
    print("="*70)
    
    # Inicializar DB Manager
    init_db_manager(mode='auto')
    
    status = get_connection_status()
    print(f"\n📊 Modo: {status['mode'].upper()}")
    print(f"   💾 SQLite: {'✅' if status['sqlite'] else '❌'}")
    print(f"   🌐 Supabase: {'✅' if status['supabase'] else '❌'}")
    
    print(f"\n📍 SQLite: {DB_PATH}")
    print(f"\n🚀 Abriendo: http://127.0.0.1:8050/")
    print("\nPresiona Ctrl+C para detener\n")
    
    app.run(debug=True, host='127.0.0.1', port=8050)
