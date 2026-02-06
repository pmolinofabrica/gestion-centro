#!/usr/bin/env python3
"""
DASHBOARD RRHH - Sistema de Gestión de Recursos Humanos v4.0
==============================================================

MEJORAS v4.0:
- Tablas en layout horizontal (side-by-side)
- Filtros con dropdowns en lugar de texto libre
- Selector de filas por página
- Carga dinámica por año (sin límite artificial de 500)
- Filtros adicionales: Residente + Mes (tabla derecha)
- Monitor de recursos y performance

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

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

DB_PATH = Path(__file__).parent.parent / 'data' / 'gestion_rrhh.db'
if not DB_PATH.exists():
    DB_PATH = 'data/gestion_rrhh.db'

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
# CLASE PARA MONITOREO DE RECURSOS
# ============================================================================

class ResourceMonitor:
    """Monitorea uso de recursos del sistema"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.start_time = time.time()
        self.query_times = []
    
    def get_memory_usage(self):
        """Obtiene uso de memoria en MB"""
        return self.process.memory_info().rss / 1024 / 1024
    
    def get_cpu_usage(self):
        """Obtiene uso de CPU en %"""
        return self.process.cpu_percent(interval=0.1)
    
    def get_uptime(self):
        """Obtiene tiempo de ejecución"""
        elapsed = time.time() - self.start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def record_query_time(self, query_time):
        """Registra tiempo de query"""
        self.query_times.append(query_time)
        # Mantener solo últimas 100 queries
        if len(self.query_times) > 100:
            self.query_times.pop(0)
    
    def get_avg_query_time(self):
        """Obtiene tiempo promedio de queries"""
        if not self.query_times:
            return 0
        return sum(self.query_times) / len(self.query_times)
    
    def get_stats(self):
        """Obtiene todas las estadísticas"""
        return {
            'memory_mb': self.get_memory_usage(),
            'cpu_percent': self.get_cpu_usage(),
            'uptime': self.get_uptime(),
            'avg_query_ms': self.get_avg_query_time() * 1000,
            'total_queries': len(self.query_times)
        }

# Instancia global del monitor
resource_monitor = ResourceMonitor()

# ============================================================================
# DEFINICIÓN DE TABLAS CON QUERIES DINÁMICAS POR AÑO
# ============================================================================

# Función para construir queries dinámicas con filtro de año
def build_query_with_year_filter(base_query, year=None):
    """
    Construye query con filtro de año opcional
    Si year=None, trae todos los datos (útil para historial completo)
    """
    if year is None:
        return base_query
    
    # Agregar WHERE/AND según si ya tiene WHERE
    if 'WHERE' in base_query.upper():
        return base_query.replace('ORDER BY', f"AND strftime('%Y', fecha_convocatoria) = '{year}' ORDER BY")
    else:
        # Insertar WHERE antes del ORDER BY o LIMIT
        if 'ORDER BY' in base_query.upper():
            return base_query.replace('ORDER BY', f"WHERE strftime('%Y', fecha_convocatoria) = '{year}' ORDER BY")
        elif 'LIMIT' in base_query.upper():
            return base_query.replace('LIMIT', f"WHERE strftime('%Y', fecha_convocatoria) = '{year}' LIMIT")
        else:
            return base_query + f" WHERE strftime('%Y', fecha_convocatoria) = '{year}'"

TABLE_QUERIES = {
    'convocatoria': {
        'name': '📋 Convocatorias',
        'year_field': 'fecha_convocatoria',
        'query': """
            SELECT 
                c.id_convocatoria,
                c.fecha_convocatoria,
                dp.nombre || ' ' || dp.apellido as agente,
                t.tipo_turno,
                t.hora_inicio_default as hora_inicio,
                t.hora_fin_default as hora_fin,
                t.cant_horas_default as horas,
                c.estado,
                p.cant_residentes_plan as residentes,
                p.cant_visit as visitantes,
                c.motivo_cambio
            FROM convocatoria c
            JOIN datos_personales dp ON c.id_agente = dp.id_agente
            JOIN turnos t ON c.id_turno = t.id_turno
            JOIN planificacion p ON c.id_plani = p.id_plani
            {year_filter}
            ORDER BY c.fecha_convocatoria DESC, dp.apellido
        """
    },
    'datos_personales': {
        'name': '👤 Datos Personales',
        'year_field': None,  # No tiene filtro de año
        'query': """
            SELECT 
                id_agente,
                nombre,
                apellido,
                dni,
                fecha_nacimiento,
                email,
                telefono,
                domicilio,
                CASE WHEN activo = 1 THEN 'Activo' ELSE 'Inactivo' END as estado,
                fecha_alta,
                fecha_baja
            FROM datos_personales
            ORDER BY apellido, nombre
        """
    },
    'saldos': {
        'name': '⏱️ Saldos de Horas',
        'year_field': 'anio',
        'query': """
            SELECT 
                dp.nombre || ' ' || dp.apellido as agente,
                s.mes,
                s.anio,
                s.horas_mes,
                s.horas_anuales,
                CASE 
                    WHEN s.horas_mes < 60 THEN 'BAJO ⚠️'
                    WHEN s.horas_mes >= 90 THEN 'ALTO 📈'
                    ELSE 'NORMAL ✓'
                END as nivel,
                s.fecha_actualizacion
            FROM saldos s
            JOIN datos_personales dp ON s.id_agente = dp.id_agente
            WHERE dp.activo = 1
            {year_filter}
            ORDER BY s.anio DESC, s.mes DESC, dp.apellido
        """
    },
    'inasistencias': {
        'name': '🚫 Inasistencias',
        'year_field': 'fecha_inasistencia',
        'query': """
            SELECT 
                i.id_inasistencia,
                dp.nombre || ' ' || dp.apellido as agente,
                i.fecha_inasistencia,
                i.motivo,
                i.estado,
                CASE WHEN i.requiere_certificado = 1 THEN 'Sí' ELSE 'No' END as requiere_certificado,
                i.observaciones,
                i.usuario_actualizo_estado
            FROM inasistencias i
            JOIN datos_personales dp ON i.id_agente = dp.id_agente
            {year_filter}
            ORDER BY i.fecha_inasistencia DESC
        """
    },
    'certificados': {
        'name': '📄 Certificados',
        'year_field': 'fecha_inasistencia',
        'query': """
            SELECT 
                c.id_certificado,
                dp.nombre || ' ' || dp.apellido as agente,
                i.fecha_inasistencia,
                i.motivo as motivo_inasistencia,
                c.fecha_entrega_certificado,
                c.tipo_certificado,
                c.estado_certificado,
                c.observaciones,
                c.usuario_reviso
            FROM certificados c
            JOIN datos_personales dp ON c.id_agente = dp.id_agente
            JOIN inasistencias i ON c.id_inasistencia = i.id_inasistencia
            {year_filter}
            ORDER BY c.fecha_entrega_certificado DESC
        """
    },
    'menu': {
        'name': '🖥️ Asignaciones',
        'year_field': 'fecha_asignacion',
        'query': """
            SELECT 
                m.id_menu,
                dp.nombre || ' ' || dp.apellido as agente,
                d.nombre_dispositivo as dispositivo,
                d.piso_dispositivo as piso,
                m.fecha_asignacion,
                t.tipo_turno,
                CASE WHEN m.acompaña_grupo = 1 THEN 'Sí' ELSE 'No' END as acompaña_grupo
            FROM menu m
            JOIN datos_personales dp ON m.id_agente = dp.id_agente
            JOIN dispositivos d ON m.id_dispositivo = d.id_dispositivo
            JOIN convocatoria c ON m.id_convocatoria = c.id_convocatoria
            JOIN turnos t ON c.id_turno = t.id_turno
            {year_filter}
            ORDER BY m.fecha_asignacion DESC, dp.apellido
        """
    },
    'capacitaciones': {
        'name': '🎓 Capacitaciones',
        'year_field': 'fecha',
        'query': """
            SELECT 
                cap.id_cap,
                d.fecha as fecha_capacitacion,
                cap.tema,
                cap.grupo,
                coord.nombre || ' ' || coord.apellido as coordinador,
                COUNT(DISTINCT cp.id_agente) as participantes,
                SUM(CASE WHEN cp.asistio = 1 THEN 1 ELSE 0 END) as asistentes,
                SUM(CASE WHEN cp.aprobado = 1 THEN 1 ELSE 0 END) as aprobados
            FROM capacitaciones cap
            JOIN dias d ON cap.id_dia = d.id_dia
            JOIN datos_personales coord ON cap.coordinador_cap = coord.id_agente
            LEFT JOIN capacitaciones_participantes cp ON cap.id_cap = cp.id_cap
            {year_filter}
            GROUP BY cap.id_cap
            ORDER BY d.fecha DESC
        """
    },
    'dispositivos': {
        'name': '🏢 Dispositivos',
        'year_field': None,
        'query': """
            SELECT 
                d.id_dispositivo,
                d.nombre_dispositivo,
                d.piso_dispositivo,
                CASE WHEN d.activo = 1 THEN '✓ Activo' ELSE '✗ Inactivo' END as estado,
                COUNT(DISTINCT m.id_agente) as agentes,
                COUNT(m.id_menu) as asignaciones,
                MAX(m.fecha_asignacion) as ultima_asignacion
            FROM dispositivos d
            LEFT JOIN menu m ON d.id_dispositivo = m.id_dispositivo
            GROUP BY d.id_dispositivo
            ORDER BY d.piso_dispositivo, d.nombre_dispositivo
        """
    },
    'turnos': {
        'name': '🕐 Turnos',
        'year_field': None,
        'query': """
            SELECT 
                t.tipo_turno,
                t.descripcion,
                t.hora_inicio_default,
                t.hora_fin_default,
                t.cant_horas_default,
                CASE WHEN t.activo = 1 THEN '✓' ELSE '✗' END as activo
            FROM turnos t
            ORDER BY t.tipo_turno
        """
    }
}

# ============================================================================
# FUNCIONES DE DATOS
# ============================================================================

def get_connection():
    """Conectar a la base de datos"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_available_years():
    """Obtener años disponibles en la BD"""
    try:
        conn = get_connection()
        query = """
            SELECT DISTINCT strftime('%Y', fecha_convocatoria) as year
            FROM convocatoria
            WHERE fecha_convocatoria IS NOT NULL
            ORDER BY year DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        years = df['year'].tolist()
        return [int(y) for y in years if y]
    except:
        return [2025]  # Default

def get_agentes_list():
    """Obtener lista de agentes activos"""
    try:
        conn = get_connection()
        query = """
            SELECT DISTINCT nombre || ' ' || apellido as agente
            FROM datos_personales
            WHERE activo = 1
            ORDER BY apellido, nombre
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df['agente'].tolist()
    except:
        return []

def get_meses_list():
    """Obtener lista de meses con datos"""
    meses = [
        '01 - Enero', '02 - Febrero', '03 - Marzo', '04 - Abril',
        '05 - Mayo', '06 - Junio', '07 - Julio', '08 - Agosto',
        '09 - Septiembre', '10 - Octubre', '11 - Noviembre', '12 - Diciembre'
    ]
    return meses

def get_table_data(table_key, year=None, agente_filter=None, mes_filter=None):
    """
    Obtener datos de una tabla con filtros opcionales
    
    Args:
        table_key: Clave de la tabla
        year: Año a filtrar (None = todos)
        agente_filter: Filtro por agente (solo para tabla derecha)
        mes_filter: Filtro por mes (solo para tabla derecha)
    """
    start_time = time.time()
    
    try:
        conn = get_connection()
        table_config = TABLE_QUERIES[table_key]
        base_query = table_config['query']
        year_field = table_config.get('year_field')
        
        # Construir filtros dinámicos
        filters = []
        
        # Filtro de año
        if year and year_field:
            if year_field == 'anio':
                filters.append(f"s.anio = {year}")
            else:
                filters.append(f"strftime('%Y', {year_field}) = '{year}'")
        
        # Filtro de agente (solo si se proporciona)
        if agente_filter and 'agente' in base_query:
            # Escapar comillas simples
            agente_safe = agente_filter.replace("'", "''")
            filters.append(f"(dp.nombre || ' ' || dp.apellido) = '{agente_safe}'")
        
        # Filtro de mes (solo si se proporciona)
        if mes_filter and year_field and year_field != 'anio':
            mes_num = mes_filter.split(' - ')[0]  # Extraer '01' de '01 - Enero'
            filters.append(f"strftime('%m', {year_field}) = '{mes_num}'")
        elif mes_filter and year_field == 'anio':
            mes_num = mes_filter.split(' - ')[0]
            filters.append(f"s.mes = {int(mes_num)}")
        
        # Aplicar filtros
        if filters:
            filter_clause = ' AND '.join(filters)
            if 'WHERE' in base_query.upper():
                query = base_query.replace('{year_filter}', f"AND {filter_clause}")
            else:
                # Insertar WHERE antes de ORDER BY o GROUP BY
                if 'ORDER BY' in base_query.upper():
                    query = base_query.replace('{year_filter}', f"WHERE {filter_clause}")
                elif 'GROUP BY' in base_query.upper():
                    query = base_query.replace('{year_filter}', f"WHERE {filter_clause}")
                else:
                    query = base_query.replace('{year_filter}', f"WHERE {filter_clause}")
        else:
            query = base_query.replace('{year_filter}', '')
        
        # Ejecutar query
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Registrar tiempo de query
        query_time = time.time() - start_time
        resource_monitor.record_query_time(query_time)
        
        return df
        
    except Exception as e:
        print(f"Error obteniendo datos de {table_key}: {e}")
        return pd.DataFrame()

def get_column_values(df, column_name, max_values=100):
    """Obtener valores únicos de una columna para dropdown"""
    if column_name not in df.columns:
        return []
    
    unique_values = df[column_name].dropna().unique()
    # Limitar cantidad para no saturar dropdown
    if len(unique_values) > max_values:
        # Tomar los más frecuentes
        value_counts = df[column_name].value_counts().head(max_values)
        return value_counts.index.tolist()
    
    return sorted(unique_values.tolist())

# ============================================================================
# FUNCIONES DE VISUALIZACIÓN (mantenidas del código anterior)
# ============================================================================

def apply_flourish_template(fig):
    """Aplica template Flourish"""
    fig.update_layout(
        plot_bgcolor=FLOURISH_COLORS['bg_primary'],
        paper_bgcolor=FLOURISH_COLORS['bg_primary'],
        font=dict(
            family='"Inter", sans-serif',
            size=13,
            color=FLOURISH_COLORS['text_primary']
        ),
        title_font=dict(size=20, color=FLOURISH_COLORS['text_primary']),
        margin=dict(l=60, r=40, t=80, b=60),
        showlegend=True,
        hovermode='closest',
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=FLOURISH_COLORS['gray_lighter'],
            showline=False,
            zeroline=False
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=FLOURISH_COLORS['gray_lighter'],
            showline=False,
            zeroline=False
        )
    )
    return fig

# [AQUÍ IRÍAN TODAS LAS FUNCIONES DE GRÁFICOS DEL CÓDIGO ANTERIOR]
# Por brevedad las omito, pero deben estar presentes

def get_inasistencias_data():
    """Obtener datos de inasistencias"""
    conn = get_connection()
    
    query_total = "SELECT COUNT(*) as total FROM inasistencias"
    total = pd.read_sql_query(query_total, conn)
    
    query_por_tipo = """
        SELECT motivo, COUNT(*) as cantidad
        FROM inasistencias GROUP BY motivo ORDER BY cantidad DESC
    """
    por_tipo = pd.read_sql_query(query_por_tipo, conn)
    
    query_por_estado = """
        SELECT estado, COUNT(*) as cantidad
        FROM inasistencias GROUP BY estado ORDER BY cantidad DESC
    """
    por_estado = pd.read_sql_query(query_por_estado, conn)
    
    query_por_mes = """
        SELECT strftime('%Y-%m', fecha_inasistencia) as mes, COUNT(*) as cantidad
        FROM inasistencias GROUP BY mes ORDER BY mes
    """
    por_mes = pd.read_sql_query(query_por_mes, conn)
    
    query_certificados = """
        SELECT 
            CASE WHEN requiere_certificado = 1 THEN 'Requiere' ELSE 'No requiere' END as categoria,
            COUNT(*) as cantidad
        FROM inasistencias GROUP BY requiere_certificado
    """
    certificados = pd.read_sql_query(query_certificados, conn)
    
    conn.close()
    return {
        'total': total,
        'por_tipo': por_tipo,
        'por_estado': por_estado,
        'por_mes': por_mes,
        'certificados': certificados
    }

def create_inasistencias_charts(data):
    """Crear gráficos simples de inasistencias"""
    total = data['total']['total'].iloc[0] if not data['total'].empty else 0
    
    fig_total = go.Figure(go.Indicator(
        mode="number",
        value=total,
        title={'text': "Total Inasistencias", 'font': {'size': 18}},
        number={'font': {'size': 56, 'color': FLOURISH_COLORS['purple']}}
    ))
    fig_total.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
    
    return {'total': fig_total}

# ============================================================================
# APLICACIÓN DASH
# ============================================================================

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Dashboard RRHH v4.0"

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
            }
            .main-header h1 { margin: 0; font-size: 24px; font-weight: 600; }
            .main-header p { margin: 5px 0 0 0; opacity: 0.9; font-size: 13px; }
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

# Layout principal
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("Dashboard RRHH v4.0"),
        html.P("Sistema Optimizado - Carga Dinámica por Año")
    ], className='main-header'),
    
    # Tabs
    dcc.Tabs(id='tabs', value='tablas', children=[
        dcc.Tab(label='📊 Inasistencias', value='inasistencias'),
        dcc.Tab(label='📋 Explorador de Tablas', value='tablas'),
    ]),
    
    # Contenido
    html.Div(id='tab-content'),
    
    # Monitor de recursos (flotante)
    html.Div(id='resource-monitor', className='resource-monitor'),
    
    # Interval para actualizar monitor
    dcc.Interval(id='interval-monitor', interval=2000, n_intervals=0)
])

# Callback para actualizar monitor de recursos
@app.callback(
    Output('resource-monitor', 'children'),
    Input('interval-monitor', 'n_intervals')
)
def update_resource_monitor(n):
    stats = resource_monitor.get_stats()
    
    # Determinar color según uso
    memory_color = FLOURISH_COLORS['green'] if stats['memory_mb'] < 200 else FLOURISH_COLORS['orange'] if stats['memory_mb'] < 500 else FLOURISH_COLORS['red']
    cpu_color = FLOURISH_COLORS['green'] if stats['cpu_percent'] < 30 else FLOURISH_COLORS['orange'] if stats['cpu_percent'] < 70 else FLOURISH_COLORS['red']
    query_color = FLOURISH_COLORS['green'] if stats['avg_query_ms'] < 100 else FLOURISH_COLORS['orange'] if stats['avg_query_ms'] < 500 else FLOURISH_COLORS['red']
    
    return html.Div([
        html.Div("📊 Monitor de Recursos", style={'fontWeight': '600', 'marginBottom': '8px', 'color': FLOURISH_COLORS['purple']}),
        html.Div([
            html.Span("Memoria:", className='resource-label'),
            html.Span(f"{stats['memory_mb']:.1f} MB", className='resource-value', style={'color': memory_color})
        ], className='resource-item'),
        html.Div([
            html.Span("CPU:", className='resource-label'),
            html.Span(f"{stats['cpu_percent']:.1f}%", className='resource-value', style={'color': cpu_color})
        ], className='resource-item'),
        html.Div([
            html.Span("Query Prom:", className='resource-label'),
            html.Span(f"{stats['avg_query_ms']:.0f} ms", className='resource-value', style={'color': query_color})
        ], className='resource-item'),
        html.Div([
            html.Span("Queries:", className='resource-label'),
            html.Span(f"{stats['total_queries']}", className='resource-value')
        ], className='resource-item'),
        html.Div([
            html.Span("Uptime:", className='resource-label'),
            html.Span(stats['uptime'], className='resource-value')
        ], className='resource-item'),
    ])

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
            return html.Div([
                html.H2("Inasistencias"),
                dcc.Graph(figure=charts['total'])
            ])
        except Exception as e:
            return html.Div(f"Error: {e}")
    
    elif tab == 'tablas':
        table_options = [{'label': v['name'], 'value': k} for k, v in TABLE_QUERIES.items()]
        years = get_available_years()
        year_options = [{'label': 'Todos los años', 'value': 'all'}] + [{'label': str(y), 'value': y} for y in years]
        current_year = years[0] if years else 2025
        
        agentes = get_agentes_list()
        agente_options = [{'label': 'Todos', 'value': 'all'}] + [{'label': a, 'value': a} for a in agentes]
        
        meses = get_meses_list()
        mes_options = [{'label': 'Todos', 'value': 'all'}] + [{'label': m, 'value': m} for m in meses]
        
        return html.Div([
            html.H2("Explorador de Tablas", style={'marginBottom': '20px'}),
            
            # Layout horizontal con dos columnas
            html.Div([
                # COLUMNA IZQUIERDA (Tabla 1)
                html.Div([
                    html.Div([
                        # Controles en fila
                        html.Div([
                            html.Div([
                                html.Label("📊 Tabla:", className='control-label'),
                                dcc.Dropdown(
                                    id='table-dropdown-1',
                                    options=table_options,
                                    value='convocatoria',
                                    clearable=False,
                                    style={'width': '250px'}
                                )
                            ], className='control-item'),
                            
                            html.Div([
                                html.Label("📅 Año:", className='control-label'),
                                dcc.Dropdown(
                                    id='year-dropdown-1',
                                    options=year_options,
                                    value=current_year,
                                    clearable=False,
                                    style={'width': '150px'}
                                )
                            ], className='control-item'),
                            
                            html.Div([
                                html.Label("📄 Filas:", className='control-label'),
                                dcc.Dropdown(
                                    id='rows-dropdown-1',
                                    options=[
                                        {'label': '10', 'value': 10},
                                        {'label': '20', 'value': 20},
                                        {'label': '50', 'value': 50},
                                        {'label': '100', 'value': 100},
                                        {'label': '200', 'value': 200}
                                    ],
                                    value=20,
                                    clearable=False,
                                    style={'width': '100px'}
                                )
                            ], className='control-item')
                        ], className='controls-row'),
                        
                        html.Div(id='table-info-1', style={'fontSize': '12px', 'color': FLOURISH_COLORS['text_secondary'], 'marginBottom': '10px'}),
                        html.Div(id='table-container-1')
                    ], className='table-container')
                ], style={'width': '49%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                
                # COLUMNA DERECHA (Tabla 2 con filtros adicionales)
                html.Div([
                    html.Div([
                        # Controles en fila
                        html.Div([
                            html.Div([
                                html.Label("📊 Tabla:", className='control-label'),
                                dcc.Dropdown(
                                    id='table-dropdown-2',
                                    options=table_options,
                                    value='saldos',
                                    clearable=False,
                                    style={'width': '250px'}
                                )
                            ], className='control-item'),
                            
                            html.Div([
                                html.Label("📅 Año:", className='control-label'),
                                dcc.Dropdown(
                                    id='year-dropdown-2',
                                    options=year_options,
                                    value=current_year,
                                    clearable=False,
                                    style={'width': '150px'}
                                )
                            ], className='control-item'),
                            
                            html.Div([
                                html.Label("📄 Filas:", className='control-label'),
                                dcc.Dropdown(
                                    id='rows-dropdown-2',
                                    options=[
                                        {'label': '10', 'value': 10},
                                        {'label': '20', 'value': 20},
                                        {'label': '50', 'value': 50},
                                        {'label': '100', 'value': 100},
                                        {'label': '200', 'value': 200}
                                    ],
                                    value=20,
                                    clearable=False,
                                    style={'width': '100px'}
                                )
                            ], className='control-item')
                        ], className='controls-row'),
                        
                        # FILTROS ADICIONALES (segunda fila)
                        html.Div([
                            html.Div([
                                html.Label("👤 Residente:", className='control-label'),
                                dcc.Dropdown(
                                    id='agente-dropdown-2',
                                    options=agente_options,
                                    value='all',
                                    clearable=False,
                                    style={'width': '250px'}
                                )
                            ], className='control-item'),
                            
                            html.Div([
                                html.Label("📆 Mes:", className='control-label'),
                                dcc.Dropdown(
                                    id='mes-dropdown-2',
                                    options=mes_options,
                                    value='all',
                                    clearable=False,
                                    style={'width': '180px'}
                                )
                            ], className='control-item')
                        ], className='controls-row'),
                        
                        html.Div(id='table-info-2', style={'fontSize': '12px', 'color': FLOURISH_COLORS['text_secondary'], 'marginBottom': '10px'}),
                        html.Div(id='table-container-2')
                    ], className='table-container')
                ], style={'width': '49%', 'display': 'inline-block', 'verticalAlign': 'top', 'float': 'right'})
            ])
        ])

# Callback para TABLA 1 (izquierda)
@app.callback(
    [Output('table-container-1', 'children'),
     Output('table-info-1', 'children')],
    [Input('table-dropdown-1', 'value'),
     Input('year-dropdown-1', 'value'),
     Input('rows-dropdown-1', 'value')]
)
def update_table_1(table_key, year, rows_per_page):
    if not table_key:
        return html.Div("Selecciona una tabla"), ""
    
    try:
        # Determinar año a usar
        year_filter = None if year == 'all' else year
        
        # Obtener datos
        df = get_table_data(table_key, year=year_filter)
        
        if df.empty:
            return html.Div("⚠️ No hay datos", style={'padding': '20px', 'color': FLOURISH_COLORS['yellow']}), ""
        
        # Info
        info = f"📊 {len(df)} registros • {len(df.columns)} columnas"
        if year_filter:
            info += f" • Año: {year_filter}"
        
        # Crear tabla con filtros dropdown
        columns = []
        for col in df.columns:
            # Obtener valores únicos para dropdown
            unique_vals = get_column_values(df, col)
            
            columns.append({
                'name': col,
                'id': col,
                'presentation': 'dropdown' if len(unique_vals) > 0 and len(unique_vals) <= 50 else 'input'
            })
        
        table = dash_table.DataTable(
            data=df.to_dict('records'),
            columns=columns,
            style_table={'overflowX': 'auto', 'overflowY': 'auto', 'maxHeight': '600px'},
            style_cell={
                'textAlign': 'left',
                'padding': '10px',
                'fontFamily': '"Inter", sans-serif',
                'fontSize': '12px',
                'border': '1px solid #ECEFF1'
            },
            style_header={
                'backgroundColor': FLOURISH_COLORS['purple'],
                'color': 'white',
                'fontWeight': '600',
                'position': 'sticky',
                'top': 0,
                'zIndex': 1
            },
            style_data={
                'backgroundColor': 'white',
                'color': FLOURISH_COLORS['text_primary']
            },
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': FLOURISH_COLORS['bg_secondary']}
            ],
            page_size=rows_per_page,
            page_action='native',
            sort_action='native',
            filter_action='native',
            export_format='xlsx',
            fixed_rows={'headers': True}
        )
        
        return table, info
        
    except Exception as e:
        return html.Div(f"❌ Error: {str(e)}", style={'color': FLOURISH_COLORS['red'], 'padding': '20px'}), ""

# Callback para TABLA 2 (derecha con filtros adicionales)
@app.callback(
    [Output('table-container-2', 'children'),
     Output('table-info-2', 'children')],
    [Input('table-dropdown-2', 'value'),
     Input('year-dropdown-2', 'value'),
     Input('rows-dropdown-2', 'value'),
     Input('agente-dropdown-2', 'value'),
     Input('mes-dropdown-2', 'value')]
)
def update_table_2(table_key, year, rows_per_page, agente, mes):
    if not table_key:
        return html.Div("Selecciona una tabla"), ""
    
    try:
        # Determinar filtros
        year_filter = None if year == 'all' else year
        agente_filter = None if agente == 'all' else agente
        mes_filter = None if mes == 'all' else mes
        
        # Obtener datos con todos los filtros
        df = get_table_data(table_key, year=year_filter, agente_filter=agente_filter, mes_filter=mes_filter)
        
        if df.empty:
            return html.Div("⚠️ No hay datos con estos filtros", style={'padding': '20px', 'color': FLOURISH_COLORS['yellow']}), ""
        
        # Info con filtros aplicados
        info_parts = [f"📊 {len(df)} registros • {len(df.columns)} columnas"]
        if year_filter:
            info_parts.append(f"Año: {year_filter}")
        if agente_filter:
            info_parts.append(f"Agente: {agente_filter}")
        if mes_filter:
            info_parts.append(f"Mes: {mes_filter.split(' - ')[1]}")
        info = " • ".join(info_parts)
        
        # Crear tabla
        columns = []
        for col in df.columns:
            unique_vals = get_column_values(df, col)
            columns.append({
                'name': col,
                'id': col,
                'presentation': 'dropdown' if len(unique_vals) > 0 and len(unique_vals) <= 50 else 'input'
            })
        
        table = dash_table.DataTable(
            data=df.to_dict('records'),
            columns=columns,
            style_table={'overflowX': 'auto', 'overflowY': 'auto', 'maxHeight': '600px'},
            style_cell={
                'textAlign': 'left',
                'padding': '10px',
                'fontFamily': '"Inter", sans-serif',
                'fontSize': '12px',
                'border': '1px solid #ECEFF1'
            },
            style_header={
                'backgroundColor': FLOURISH_COLORS['blue'],
                'color': 'white',
                'fontWeight': '600',
                'position': 'sticky',
                'top': 0,
                'zIndex': 1
            },
            style_data={
                'backgroundColor': 'white',
                'color': FLOURISH_COLORS['text_primary']
            },
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': FLOURISH_COLORS['bg_secondary']}
            ],
            page_size=rows_per_page,
            page_action='native',
            sort_action='native',
            filter_action='native',
            export_format='xlsx',
            fixed_rows={'headers': True}
        )
        
        return table, info
        
    except Exception as e:
        return html.Div(f"❌ Error: {str(e)}", style={'color': FLOURISH_COLORS['red'], 'padding': '20px'}), ""

# ============================================================================
# EJECUTAR
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("  DASHBOARD RRHH v4.0 - Optimizado")
    print("="*70)
    print(f"\n📁 Base de datos: {DB_PATH}")
    
    if Path(DB_PATH).exists():
        print("✅ BD encontrada")
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM convocatoria")
            conv = cursor.fetchone()[0]
            
            years = get_available_years()
            
            print(f"   • Convocatorias: {conv}")
            print(f"   • Años disponibles: {', '.join(map(str, years))}")
            print(f"   • Tablas explorables: {len(TABLE_QUERIES)}")
            
            conn.close()
        except Exception as e:
            print(f"⚠️  Error: {e}")
    
    print("\n🚀 Características v4.0:")
    print("   ✅ Tablas lado a lado (horizontal)")
    print("   ✅ Filtros dropdown inteligentes")
    print("   ✅ Selector de filas por página")
    print("   ✅ Carga dinámica por año")
    print("   ✅ Filtros: Residente + Mes (tabla derecha)")
    print("   ✅ Monitor de recursos en tiempo real")
    print("\n📊 Abre: http://127.0.0.1:8050/")
    print("   Monitor en esquina inferior derecha")
    print("\nPresiona Ctrl+C para detener\n")
    
    app.run(debug=True, host='127.0.0.1', port=8050)