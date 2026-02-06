#!/usr/bin/env python3
"""
DASHBOARD RRHH - Sistema de Gestión de Recursos Humanos
========================================================

Visualizaciones interactivas con Plotly Dash:
1. Inasistencias (totales y por tipo)
2. Saldos por agente
3. Saldos por agente y turno
4. Asignaciones de dispositivos

Autor: Pablo - Data Analyst
Fecha: Diciembre 2025
"""

import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import sqlite3
from pathlib import Path

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Ruta a la base de datos (ajustar según tu estructura)
DB_PATH = Path(__file__).parent.parent / 'data' / 'gestion_rrhh.db'

# Si no existe, usar path relativo
if not DB_PATH.exists():
    DB_PATH = 'data/gestion_rrhh.db'

# Colores del tema
COLORS = {
    'primary': '#1f77b4',
    'secondary': '#ff7f0e',
    'success': '#2ca02c',
    'danger': '#d62728',
    'warning': '#ff9800',
    'info': '#17a2b8',
    'background': '#f8f9fa',
    'text': '#212529'
}

# ============================================================================
# FUNCIONES DE DATOS
# ============================================================================

def get_connection():
    """Conectar a la base de datos con row_factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_inasistencias_data():
    """Obtener datos de inasistencias"""
    conn = get_connection()
    
    # Total de inasistencias
    query_total = """
        SELECT COUNT(*) as total
        FROM inasistencias
    """
    total = pd.read_sql_query(query_total, conn)
    
    # Por tipo (motivo)
    query_por_tipo = """
        SELECT 
            motivo,
            COUNT(*) as cantidad,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM inasistencias), 2) as porcentaje
        FROM inasistencias
        GROUP BY motivo
        ORDER BY cantidad DESC
    """
    por_tipo = pd.read_sql_query(query_por_tipo, conn)
    
    # Por estado
    query_por_estado = """
        SELECT 
            estado,
            COUNT(*) as cantidad
        FROM inasistencias
        GROUP BY estado
        ORDER BY cantidad DESC
    """
    por_estado = pd.read_sql_query(query_por_estado, conn)
    
    # Por mes
    query_por_mes = """
        SELECT 
            strftime('%Y-%m', fecha_inasistencia) as mes,
            COUNT(*) as cantidad
        FROM inasistencias
        GROUP BY mes
        ORDER BY mes
    """
    por_mes = pd.read_sql_query(query_por_mes, conn)
    
    # Certificados vs sin certificados
    query_certificados = """
        SELECT 
            CASE 
                WHEN requiere_certificado = 1 THEN 'Requiere certificado'
                ELSE 'No requiere'
            END as categoria,
            COUNT(*) as cantidad
        FROM inasistencias
        GROUP BY requiere_certificado
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

def get_saldos_data():
    """Obtener datos de saldos por agente"""
    conn = get_connection()
    
    # Saldos actuales (último mes de cada agente)
    query_actuales = """
        SELECT 
            dp.nombre || ' ' || dp.apellido as agente,
            s.mes,
            s.anio,
            s.horas_mes,
            s.horas_anuales,
            CASE 
                WHEN s.horas_mes < 60 THEN 'BAJO'
                WHEN s.horas_mes >= 90 THEN 'ALTO'
                ELSE 'NORMAL'
            END as nivel
        FROM saldos s
        JOIN datos_personales dp ON s.id_agente = dp.id_agente
        WHERE dp.activo = 1
        ORDER BY s.anio DESC, s.mes DESC, agente
    """
    actuales = pd.read_sql_query(query_actuales, conn)
    
    # Saldos por agente (acumulado anual)
    query_anual = """
        SELECT 
            dp.nombre || ' ' || dp.apellido as agente,
            MAX(s.horas_anuales) as horas_totales,
            s.anio
        FROM saldos s
        JOIN datos_personales dp ON s.id_agente = dp.id_agente
        WHERE dp.activo = 1
        AND s.anio = (SELECT MAX(anio) FROM saldos)
        GROUP BY dp.id_agente, s.anio
        ORDER BY horas_totales DESC
    """
    anual = pd.read_sql_query(query_anual, conn)
    
    # Evolución mensual por agente
    query_evolucion = """
        SELECT 
            dp.nombre || ' ' || dp.apellido as agente,
            s.mes,
            s.anio,
            s.horas_mes
        FROM saldos s
        JOIN datos_personales dp ON s.id_agente = dp.id_agente
        WHERE dp.activo = 1
        ORDER BY dp.apellido, s.anio, s.mes
    """
    evolucion = pd.read_sql_query(query_evolucion, conn)
    
    conn.close()
    
    return {
        'actuales': actuales,
        'anual': anual,
        'evolucion': evolucion
    }

def get_saldos_por_turno():
    """Obtener saldos por agente y tipo de turno"""
    conn = get_connection()
    
    query = """
        SELECT 
            dp.nombre || ' ' || dp.apellido as agente,
            t.tipo_turno,
            COUNT(DISTINCT c.id_convocatoria) as cantidad_turnos,
            SUM(COALESCE(p.cant_horas, t.cant_horas_default, 0)) as horas_totales
        FROM convocatoria c
        JOIN datos_personales dp ON c.id_agente = dp.id_agente
        JOIN planificacion p ON c.id_plani = p.id_plani
        JOIN turnos t ON p.id_turno = t.id_turno
        WHERE c.estado IN ('vigente', 'cumplida')
        AND dp.activo = 1
        GROUP BY dp.id_agente, t.tipo_turno
        ORDER BY dp.apellido, t.tipo_turno
    """
    
    data = pd.read_sql_query(query, conn)
    conn.close()
    
    return data

def get_dispositivos_data():
    """Obtener datos de asignaciones de dispositivos"""
    conn = get_connection()
    
    # Asignaciones por agente
    query_por_agente = """
        SELECT 
            dp.nombre || ' ' || dp.apellido as agente,
            COUNT(DISTINCT m.id_dispositivo) as dispositivos_diferentes,
            COUNT(*) as total_asignaciones
        FROM menu m
        JOIN datos_personales dp ON m.id_agente = dp.id_agente
        WHERE dp.activo = 1
        GROUP BY dp.id_agente
        ORDER BY total_asignaciones DESC
    """
    por_agente = pd.read_sql_query(query_por_agente, conn)
    
    # Matriz agente-dispositivo (heatmap)
    query_matriz = """
        SELECT 
            dp.nombre || ' ' || dp.apellido as agente,
            d.nombre_dispositivo,
            COUNT(*) as asignaciones
        FROM menu m
        JOIN datos_personales dp ON m.id_agente = dp.id_agente
        JOIN dispositivos d ON m.id_dispositivo = d.id_dispositivo
        WHERE dp.activo = 1
        GROUP BY dp.id_agente, d.id_dispositivo
        ORDER BY dp.apellido, d.nombre_dispositivo
    """
    matriz = pd.read_sql_query(query_matriz, conn)
    
    # Top dispositivos más asignados
    query_top_dispositivos = """
        SELECT 
            d.nombre_dispositivo,
            d.piso_dispositivo,
            COUNT(*) as veces_asignado,
            COUNT(DISTINCT m.id_agente) as agentes_distintos
        FROM menu m
        JOIN dispositivos d ON m.id_dispositivo = d.id_dispositivo
        GROUP BY d.id_dispositivo
        ORDER BY veces_asignado DESC
    """
    top_dispositivos = pd.read_sql_query(query_top_dispositivos, conn)
    
    # Distribución temporal de asignaciones
    query_temporal = """
        SELECT 
            strftime('%Y-%m', fecha_asignacion) as mes,
            COUNT(*) as asignaciones
        FROM menu
        GROUP BY mes
        ORDER BY mes
    """
    temporal = pd.read_sql_query(query_temporal, conn)
    
    conn.close()
    
    return {
        'por_agente': por_agente,
        'matriz': matriz,
        'top_dispositivos': top_dispositivos,
        'temporal': temporal
    }

# ============================================================================
# FUNCIONES DE VISUALIZACIÓN
# ============================================================================

def create_inasistencias_charts(data):
    """Crear gráficos de inasistencias"""
    
    # Gráfico 1: Total (KPI card)
    total = data['total']['total'].iloc[0] if not data['total'].empty else 0
    
    fig_total = go.Figure(go.Indicator(
        mode="number",
        value=total,
        title={'text': "Total Inasistencias"},
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    fig_total.update_layout(height=200)
    
    # Gráfico 2: Por tipo (pie chart)
    if not data['por_tipo'].empty:
        fig_tipo = px.pie(
            data['por_tipo'],
            values='cantidad',
            names='motivo',
            title='Inasistencias por Motivo',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_tipo.update_traces(textposition='inside', textinfo='percent+label')
    else:
        fig_tipo = go.Figure()
        fig_tipo.add_annotation(text="No hay datos", x=0.5, y=0.5, showarrow=False)
    
    # Gráfico 3: Por estado (bar chart)
    if not data['por_estado'].empty:
        fig_estado = px.bar(
            data['por_estado'],
            x='estado',
            y='cantidad',
            title='Inasistencias por Estado',
            color='estado',
            text='cantidad',
            color_discrete_map={
                'pendiente': COLORS['warning'],
                'justificada': COLORS['success'],
                'injustificada': COLORS['danger']
            }
        )
        fig_estado.update_traces(textposition='outside')
        fig_estado.update_layout(showlegend=False)
    else:
        fig_estado = go.Figure()
    
    # Gráfico 4: Evolución temporal
    if not data['por_mes'].empty:
        fig_temporal = px.line(
            data['por_mes'],
            x='mes',
            y='cantidad',
            title='Evolución Mensual de Inasistencias',
            markers=True
        )
        fig_temporal.update_traces(line_color=COLORS['danger'])
    else:
        fig_temporal = go.Figure()
    
    # Gráfico 5: Certificados vs sin certificados
    if not data['certificados'].empty:
        fig_cert = px.bar(
            data['certificados'],
            x='categoria',
            y='cantidad',
            title='Requerimiento de Certificados',
            color='categoria',
            text='cantidad'
        )
        fig_cert.update_traces(textposition='outside')
    else:
        fig_cert = go.Figure()
    
    return {
        'total': fig_total,
        'tipo': fig_tipo,
        'estado': fig_estado,
        'temporal': fig_temporal,
        'certificados': fig_cert
    }

def create_saldos_charts(data):
    """Crear gráficos de saldos"""
    
    # Gráfico 1: Ranking de horas anuales
    if not data['anual'].empty:
        fig_ranking = px.bar(
            data['anual'].head(15),  # Top 15
            x='horas_totales',
            y='agente',
            orientation='h',
            title='Ranking de Horas Anuales (Top 15)',
            text='horas_totales',
            color='horas_totales',
            color_continuous_scale='Blues'
        )
        fig_ranking.update_traces(textposition='outside')
        fig_ranking.update_layout(yaxis={'categoryorder': 'total ascending'})
    else:
        fig_ranking = go.Figure()
    
    # Gráfico 2: Distribución de niveles
    if not data['actuales'].empty:
        nivel_counts = data['actuales']['nivel'].value_counts().reset_index()
        nivel_counts.columns = ['nivel', 'cantidad']
        
        fig_niveles = px.pie(
            nivel_counts,
            values='cantidad',
            names='nivel',
            title='Distribución de Niveles de Horas',
            color='nivel',
            color_discrete_map={
                'BAJO': COLORS['danger'],
                'NORMAL': COLORS['success'],
                'ALTO': COLORS['warning']
            }
        )
    else:
        fig_niveles = go.Figure()
    
    # Gráfico 3: Evolución mensual (líneas múltiples)
    if not data['evolucion'].empty:
        # Tomar solo los últimos 6 meses y top 10 agentes
        recent_data = data['evolucion'].sort_values(['anio', 'mes']).tail(60)
        top_agentes = data['anual'].head(10)['agente'].tolist()
        recent_data = recent_data[recent_data['agente'].isin(top_agentes)]
        
        if not recent_data.empty:
            recent_data['periodo'] = recent_data['anio'].astype(str) + '-' + recent_data['mes'].astype(str).str.zfill(2)
            
            fig_evolucion = px.line(
                recent_data,
                x='periodo',
                y='horas_mes',
                color='agente',
                title='Evolución Mensual de Horas (Top 10 Agentes)',
                markers=True
            )
        else:
            fig_evolucion = go.Figure()
    else:
        fig_evolucion = go.Figure()
    
    # Gráfico 4: Box plot de distribución
    if not data['actuales'].empty:
        fig_box = px.box(
            data['actuales'],
            y='horas_mes',
            title='Distribución de Horas Mensuales',
            color_discrete_sequence=[COLORS['primary']]
        )
        fig_box.add_hline(y=60, line_dash="dash", line_color="red", 
                         annotation_text="Mínimo (60h)")
        fig_box.add_hline(y=90, line_dash="dash", line_color="orange", 
                         annotation_text="Alto (90h)")
    else:
        fig_box = go.Figure()
    
    return {
        'ranking': fig_ranking,
        'niveles': fig_niveles,
        'evolucion': fig_evolucion,
        'box': fig_box
    }

def create_saldos_turno_chart(data):
    """Crear gráfico de saldos por agente y turno"""
    
    if data.empty:
        fig = go.Figure()
        fig.add_annotation(text="No hay datos disponibles", x=0.5, y=0.5, showarrow=False)
        return fig
    
    # Crear gráfico de barras agrupadas
    fig = px.bar(
        data,
        x='agente',
        y='horas_totales',
        color='tipo_turno',
        title='Horas por Agente y Tipo de Turno',
        text='horas_totales',
        barmode='group',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    
    fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
    fig.update_layout(
        xaxis_tickangle=-45,
        height=600,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def create_dispositivos_charts(data):
    """Crear gráficos de dispositivos"""
    
    # Gráfico 1: Asignaciones por agente (bar chart horizontal)
    if not data['por_agente'].empty:
        fig_por_agente = px.bar(
            data['por_agente'].head(20),
            x='total_asignaciones',
            y='agente',
            orientation='h',
            title='Total de Asignaciones por Agente (Top 20)',
            text='total_asignaciones',
            color='dispositivos_diferentes',
            color_continuous_scale='Viridis'
        )
        fig_por_agente.update_traces(textposition='outside')
        fig_por_agente.update_layout(yaxis={'categoryorder': 'total ascending'})
    else:
        fig_por_agente = go.Figure()
    
    # Gráfico 2: Heatmap agente-dispositivo
    if not data['matriz'].empty:
        # Crear pivot table para el heatmap
        pivot = data['matriz'].pivot_table(
            index='agente',
            columns='nombre_dispositivo',
            values='asignaciones',
            fill_value=0
        )
        
        fig_heatmap = px.imshow(
            pivot,
            title='Matriz de Asignaciones: Agente × Dispositivo',
            labels=dict(x="Dispositivo", y="Agente", color="Asignaciones"),
            aspect='auto',
            color_continuous_scale='Blues'
        )
        fig_heatmap.update_xaxes(side="bottom", tickangle=-45)
    else:
        fig_heatmap = go.Figure()
    
    # Gráfico 3: Top dispositivos
    if not data['top_dispositivos'].empty:
        fig_top = px.bar(
            data['top_dispositivos'],
            x='nombre_dispositivo',
            y='veces_asignado',
            title='Dispositivos Más Asignados',
            text='veces_asignado',
            color='piso_dispositivo',
            hover_data=['agentes_distintos']
        )
        fig_top.update_traces(textposition='outside')
        fig_top.update_xaxes(tickangle=-45)
    else:
        fig_top = go.Figure()
    
    # Gráfico 4: Evolución temporal
    if not data['temporal'].empty:
        fig_temporal = px.line(
            data['temporal'],
            x='mes',
            y='asignaciones',
            title='Evolución de Asignaciones en el Tiempo',
            markers=True
        )
        fig_temporal.update_traces(line_color=COLORS['info'])
    else:
        fig_temporal = go.Figure()
    
    # Gráfico 5: Distribución de dispositivos por agente
    if not data['por_agente'].empty:
        fig_dist = px.histogram(
            data['por_agente'],
            x='dispositivos_diferentes',
            title='Distribución: Cantidad de Dispositivos Diferentes por Agente',
            nbins=10,
            text_auto=True,
            color_discrete_sequence=[COLORS['secondary']]
        )
        fig_dist.update_traces(textposition='outside')
    else:
        fig_dist = go.Figure()
    
    return {
        'por_agente': fig_por_agente,
        'heatmap': fig_heatmap,
        'top': fig_top,
        'temporal': fig_temporal,
        'distribucion': fig_dist
    }

# ============================================================================
# APLICACIÓN DASH
# ============================================================================

# Inicializar app
app = dash.Dash(__name__)
app.title = "Dashboard RRHH - Centro Cultural"

# Layout principal
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("🏛️ Dashboard RRHH - Centro Cultural", 
                style={'textAlign': 'center', 'color': COLORS['text'], 'marginBottom': '10px'}),
        html.P("Sistema de Gestión de Recursos Humanos - Visualizaciones Interactivas",
               style={'textAlign': 'center', 'color': '#6c757d', 'marginBottom': '30px'})
    ], style={'backgroundColor': COLORS['background'], 'padding': '20px'}),
    
    # Tabs
    dcc.Tabs(id='tabs', value='inasistencias', children=[
        dcc.Tab(label='📊 Inasistencias', value='inasistencias'),
        dcc.Tab(label='⏱️ Saldos por Agente', value='saldos'),
        dcc.Tab(label='🔄 Saldos por Turno', value='saldos_turno'),
        dcc.Tab(label='🖥️ Dispositivos', value='dispositivos'),
    ]),
    
    # Contenido
    html.Div(id='tab-content', style={'padding': '20px'}),
    
    # Footer
    html.Div([
        html.Hr(),
        html.P("Sistema RRHH v3.0 DAMA | Pablo - Data Analyst | Diciembre 2025",
               style={'textAlign': 'center', 'color': '#6c757d', 'fontSize': '12px'})
    ], style={'marginTop': '50px'})
])

# Callback para actualizar contenido según tab seleccionado
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
                html.H2("📊 Análisis de Inasistencias", style={'marginBottom': '20px'}),
                
                # KPI Total
                html.Div([
                    dcc.Graph(figure=charts['total'])
                ], style={'marginBottom': '20px'}),
                
                # Fila 1: Por tipo y estado
                html.Div([
                    html.Div([
                        dcc.Graph(figure=charts['tipo'])
                    ], style={'width': '48%', 'display': 'inline-block'}),
                    
                    html.Div([
                        dcc.Graph(figure=charts['estado'])
                    ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
                ]),
                
                # Fila 2: Temporal y certificados
                html.Div([
                    html.Div([
                        dcc.Graph(figure=charts['temporal'])
                    ], style={'width': '48%', 'display': 'inline-block'}),
                    
                    html.Div([
                        dcc.Graph(figure=charts['certificados'])
                    ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
                ])
            ])
        except Exception as e:
            return html.Div([
                html.H2("⚠️ Error", style={'color': COLORS['danger']}),
                html.P(f"No se pudieron cargar los datos de inasistencias: {str(e)}"),
                html.P("Verifica que la base de datos exista y contenga datos.")
            ])
    
    elif tab == 'saldos':
        try:
            data = get_saldos_data()
            charts = create_saldos_charts(data)
            
            return html.Div([
                html.H2("⏱️ Análisis de Saldos por Agente", style={'marginBottom': '20px'}),
                
                # Fila 1: Ranking y niveles
                html.Div([
                    html.Div([
                        dcc.Graph(figure=charts['ranking'])
                    ], style={'width': '65%', 'display': 'inline-block'}),
                    
                    html.Div([
                        dcc.Graph(figure=charts['niveles'])
                    ], style={'width': '33%', 'display': 'inline-block', 'float': 'right'})
                ]),
                
                # Fila 2: Evolución y box plot
                html.Div([
                    html.Div([
                        dcc.Graph(figure=charts['evolucion'])
                    ], style={'width': '65%', 'display': 'inline-block'}),
                    
                    html.Div([
                        dcc.Graph(figure=charts['box'])
                    ], style={'width': '33%', 'display': 'inline-block', 'float': 'right'})
                ])
            ])
        except Exception as e:
            return html.Div([
                html.H2("⚠️ Error", style={'color': COLORS['danger']}),
                html.P(f"No se pudieron cargar los datos de saldos: {str(e)}"),
                html.P("Verifica que la base de datos exista y contenga datos.")
            ])
    
    elif tab == 'saldos_turno':
        try:
            data = get_saldos_por_turno()
            chart = create_saldos_turno_chart(data)
            
            return html.Div([
                html.H2("🔄 Saldos por Agente y Tipo de Turno", style={'marginBottom': '20px'}),
                dcc.Graph(figure=chart)
            ])
        except Exception as e:
            return html.Div([
                html.H2("⚠️ Error", style={'color': COLORS['danger']}),
                html.P(f"No se pudieron cargar los datos: {str(e)}"),
                html.P("Verifica que la base de datos exista y contenga datos.")
            ])
    
    elif tab == 'dispositivos':
        try:
            data = get_dispositivos_data()
            charts = create_dispositivos_charts(data)
            
            return html.Div([
                html.H2("🖥️ Análisis de Asignaciones de Dispositivos", style={'marginBottom': '20px'}),
                
                # Fila 1: Por agente y heatmap
                html.Div([
                    html.Div([
                        dcc.Graph(figure=charts['por_agente'])
                    ], style={'width': '48%', 'display': 'inline-block'}),
                    
                    html.Div([
                        dcc.Graph(figure=charts['heatmap'])
                    ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
                ]),
                
                # Fila 2: Top dispositivos y temporal
                html.Div([
                    html.Div([
                        dcc.Graph(figure=charts['top'])
                    ], style={'width': '48%', 'display': 'inline-block'}),
                    
                    html.Div([
                        dcc.Graph(figure=charts['temporal'])
                    ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
                ]),
                
                # Fila 3: Distribución
                html.Div([
                    dcc.Graph(figure=charts['distribucion'])
                ])
            ])
        except Exception as e:
            return html.Div([
                html.H2("⚠️ Error", style={'color': COLORS['danger']}),
                html.P(f"No se pudieron cargar los datos de dispositivos: {str(e)}"),
                html.P("Verifica que la base de datos exista y contenga datos.")
            ])

# ============================================================================
# EJECUTAR APLICACIÓN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("  DASHBOARD RRHH - Centro Cultural")
    print("="*70)
    print(f"\n📁 Base de datos: {DB_PATH}")
    
    # Verificar que existe la BD
    if Path(DB_PATH).exists():
        print("✅ Base de datos encontrada")
        
        # Mostrar estadísticas rápidas
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM inasistencias")
            inasistencias = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM saldos")
            saldos = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM menu")
            asignaciones = cursor.fetchone()[0]
            
            print(f"   • Inasistencias: {inasistencias}")
            print(f"   • Registros de saldos: {saldos}")
            print(f"   • Asignaciones dispositivos: {asignaciones}")
            
            conn.close()
        except Exception as e:
            print(f"⚠️  Error al leer datos: {e}")
    else:
        print("⚠️  Base de datos NO encontrada")
        print(f"   Esperada en: {DB_PATH}")
        print("\n   Crea la base de datos primero con:")
        print("   sqlite3 data/gestion_rrhh.db < sql/schema_v3_DAMA_compliant.sql")
    
    print("\n🚀 Iniciando servidor...")
    print("📊 Abre tu navegador en: http://127.0.0.1:8050/")
    print("\n   Presiona Ctrl+C para detener el servidor\n")
    
    app.run(debug=True, host='127.0.0.1', port=8050)