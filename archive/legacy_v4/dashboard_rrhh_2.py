#!/usr/bin/env python3
"""
DASHBOARD RRHH - Sistema de Gestión de Recursos Humanos
========================================================

Visualizaciones interactivas con estética tipo Flourish
- Diseño limpio y moderno
- Paleta de colores profesional
- Tipografía elegante
- Espaciado generoso

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
import dash_bootstrap_components as dbc

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Ruta a la base de datos
DB_PATH = Path(__file__).parent.parent / 'data' / 'gestion_rrhh.db'
if not DB_PATH.exists():
    DB_PATH = 'data/gestion_rrhh.db'

# PALETA FLOURISH - Colores modernos y profesionales
FLOURISH_COLORS = {
    # Colores primarios
    'purple': '#7C4DFF',      # Púrpura vibrante
    'blue': '#2196F3',        # Azul brillante
    'teal': '#00BCD4',        # Cian
    'green': '#4CAF50',       # Verde
    'orange': '#FF9800',      # Naranja
    'pink': '#E91E63',        # Rosa
    'red': '#F44336',         # Rojo
    'yellow': '#FFC107',      # Amarillo
    
    # Colores secundarios
    'purple_light': '#B388FF',
    'blue_light': '#64B5F6',
    'teal_light': '#4DD0E1',
    'green_light': '#81C784',
    
    # Grises
    'gray_dark': '#263238',
    'gray': '#546E7A',
    'gray_light': '#B0BEC5',
    'gray_lighter': '#ECEFF1',
    
    # Background
    'bg_primary': '#FFFFFF',
    'bg_secondary': '#FAFAFA',
    'bg_card': '#FFFFFF',
    
    # Text
    'text_primary': '#263238',
    'text_secondary': '#546E7A',
    'text_muted': '#90A4AE'
}

# Paleta de colores secuencial (para gráficos)
COLOR_SCALE_FLOURISH = [
    '#7C4DFF',  # Púrpura
    '#2196F3',  # Azul
    '#00BCD4',  # Cian
    '#4CAF50',  # Verde
    '#FFC107',  # Amarillo
    '#FF9800',  # Naranja
    '#E91E63',  # Rosa
    '#F44336'   # Rojo
]

# ============================================================================
# FUNCIONES DE DATOS (sin cambios)
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
    
    query_total = "SELECT COUNT(*) as total FROM inasistencias"
    total = pd.read_sql_query(query_total, conn)
    
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
    
    query_por_estado = """
        SELECT 
            estado,
            COUNT(*) as cantidad
        FROM inasistencias
        GROUP BY estado
        ORDER BY cantidad DESC
    """
    por_estado = pd.read_sql_query(query_por_estado, conn)
    
    query_por_mes = """
        SELECT 
            strftime('%Y-%m', fecha_inasistencia) as mes,
            COUNT(*) as cantidad
        FROM inasistencias
        GROUP BY mes
        ORDER BY mes
    """
    por_mes = pd.read_sql_query(query_por_mes, conn)
    
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
# TEMPLATE FLOURISH PARA GRÁFICOS
# ============================================================================

def apply_flourish_template(fig):
    """Aplica el template estilo Flourish a un gráfico"""
    fig.update_layout(
        # Fondo
        plot_bgcolor=FLOURISH_COLORS['bg_primary'],
        paper_bgcolor=FLOURISH_COLORS['bg_primary'],
        
        # Fuente
        font=dict(
            family='"Inter", "Segoe UI", "Helvetica Neue", sans-serif',
            size=13,
            color=FLOURISH_COLORS['text_primary']
        ),
        
        # Título
        title_font=dict(
            size=20,
            color=FLOURISH_COLORS['text_primary'],
            family='"Inter", sans-serif'
        ),
        title_x=0.02,
        title_y=0.98,
        
        # Márgenes generosos
        margin=dict(l=60, r=40, t=80, b=60),
        
        # Sin borde
        showlegend=True,
        
        # Hover
        hovermode='closest',
        
        # Grid sutil
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
        ),
        
        # Leyenda
        legend=dict(
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor=FLOURISH_COLORS['gray_lighter'],
            borderwidth=1,
            font=dict(size=11)
        )
    )
    
    return fig

# ============================================================================
# FUNCIONES DE VISUALIZACIÓN ESTILO FLOURISH
# ============================================================================

def create_inasistencias_charts(data):
    """Crear gráficos de inasistencias estilo Flourish"""
    
    # Gráfico 1: KPI Total
    total = data['total']['total'].iloc[0] if not data['total'].empty else 0
    
    fig_total = go.Figure(go.Indicator(
        mode="number",
        value=total,
        title={'text': "Total Inasistencias", 
               'font': {'size': 18, 'color': FLOURISH_COLORS['text_secondary']}},
        number={'font': {'size': 56, 'color': FLOURISH_COLORS['purple'], 'family': '"Inter", sans-serif'}},
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    fig_total.update_layout(
        paper_bgcolor=FLOURISH_COLORS['bg_card'],
        height=200,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    # Gráfico 2: Por tipo (donut chart moderno)
    if not data['por_tipo'].empty:
        fig_tipo = go.Figure(data=[go.Pie(
            labels=data['por_tipo']['motivo'],
            values=data['por_tipo']['cantidad'],
            hole=0.5,
            marker=dict(colors=COLOR_SCALE_FLOURISH),
            textposition='outside',
            textinfo='label+percent',
            textfont=dict(size=12)
        )])
        
        fig_tipo.update_layout(
            title={
                'text': 'Distribución por Motivo',
                'x': 0.5,
                'xanchor': 'center'
            },
            showlegend=False,
            height=400
        )
        fig_tipo = apply_flourish_template(fig_tipo)
    else:
        fig_tipo = go.Figure()
    
    # Gráfico 3: Por estado (barras redondeadas)
    if not data['por_estado'].empty:
        color_map = {
            'pendiente': FLOURISH_COLORS['yellow'],
            'justificada': FLOURISH_COLORS['green'],
            'injustificada': FLOURISH_COLORS['red']
        }
        
        colors = [color_map.get(e, FLOURISH_COLORS['blue']) for e in data['por_estado']['estado']]
        
        fig_estado = go.Figure(data=[go.Bar(
            x=data['por_estado']['estado'],
            y=data['por_estado']['cantidad'],
            marker=dict(
                color=colors,
                line=dict(width=0)
            ),
            text=data['por_estado']['cantidad'],
            textposition='outside',
            textfont=dict(size=14, color=FLOURISH_COLORS['text_primary']),
            hovertemplate='<b>%{x}</b><br>Cantidad: %{y}<extra></extra>'
        )])
        
        fig_estado.update_layout(
            title='Por Estado',
            showlegend=False,
            height=400
        )
        fig_estado = apply_flourish_template(fig_estado)
        fig_estado.update_xaxes(title='')
        fig_estado.update_yaxes(title='Cantidad')
    else:
        fig_estado = go.Figure()
    
    # Gráfico 4: Evolución temporal (área suave)
    if not data['por_mes'].empty:
        fig_temporal = go.Figure()
        
        fig_temporal.add_trace(go.Scatter(
            x=data['por_mes']['mes'],
            y=data['por_mes']['cantidad'],
            mode='lines+markers',
            line=dict(
                color=FLOURISH_COLORS['purple'],
                width=3,
                shape='spline'
            ),
            marker=dict(
                size=8,
                color=FLOURISH_COLORS['purple'],
                line=dict(color='white', width=2)
            ),
            fill='tozeroy',
            fillcolor=f"rgba(124, 77, 255, 0.1)",
            hovertemplate='<b>%{x}</b><br>Inasistencias: %{y}<extra></extra>'
        ))
        
        fig_temporal.update_layout(
            title='Evolución Mensual',
            height=400
        )
        fig_temporal = apply_flourish_template(fig_temporal)
        fig_temporal.update_xaxes(title='')
        fig_temporal.update_yaxes(title='Cantidad')
    else:
        fig_temporal = go.Figure()
    
    # Gráfico 5: Certificados (barras horizontales)
    if not data['certificados'].empty:
        fig_cert = go.Figure(data=[go.Bar(
            y=data['certificados']['categoria'],
            x=data['certificados']['cantidad'],
            orientation='h',
            marker=dict(
                color=[FLOURISH_COLORS['teal'], FLOURISH_COLORS['gray_light']],
                line=dict(width=0)
            ),
            text=data['certificados']['cantidad'],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Cantidad: %{x}<extra></extra>'
        )])
        
        fig_cert.update_layout(
            title='Requerimiento de Certificados',
            showlegend=False,
            height=300
        )
        fig_cert = apply_flourish_template(fig_cert)
        fig_cert.update_xaxes(title='Cantidad')
        fig_cert.update_yaxes(title='')
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
    """Crear gráficos de saldos estilo Flourish"""
    
    # Gráfico 1: Ranking (barras horizontales degradadas)
    if not data['anual'].empty:
        top_data = data['anual'].head(15)
        
        # Crear gradiente de color
        colors = [f"rgba(124, 77, 255, {0.4 + (i/len(top_data))*0.6})" 
                 for i in range(len(top_data))]
        
        fig_ranking = go.Figure(data=[go.Bar(
            x=top_data['horas_totales'],
            y=top_data['agente'],
            orientation='h',
            marker=dict(
                color=colors,
                line=dict(width=0)
            ),
            text=top_data['horas_totales'].apply(lambda x: f"{x:.1f}h"),
            textposition='outside',
            textfont=dict(size=11),
            hovertemplate='<b>%{y}</b><br>Horas: %{x:.1f}h<extra></extra>'
        )])
        
        fig_ranking.update_layout(
            title='Ranking de Horas Anuales',
            showlegend=False,
            height=600
        )
        fig_ranking = apply_flourish_template(fig_ranking)
        fig_ranking.update_xaxes(title='Horas')
        fig_ranking.update_yaxes(title='', categoryorder='total ascending')
    else:
        fig_ranking = go.Figure()
    
    # Gráfico 2: Niveles (donut)
    if not data['actuales'].empty:
        nivel_counts = data['actuales']['nivel'].value_counts().reset_index()
        nivel_counts.columns = ['nivel', 'cantidad']
        
        color_map = {
            'BAJO': FLOURISH_COLORS['red'],
            'NORMAL': FLOURISH_COLORS['green'],
            'ALTO': FLOURISH_COLORS['yellow']
        }
        colors = [color_map.get(n, FLOURISH_COLORS['blue']) for n in nivel_counts['nivel']]
        
        fig_niveles = go.Figure(data=[go.Pie(
            labels=nivel_counts['nivel'],
            values=nivel_counts['cantidad'],
            hole=0.5,
            marker=dict(colors=colors),
            textposition='outside',
            textinfo='label+percent',
            textfont=dict(size=12)
        )])
        
        fig_niveles.update_layout(
            title={
                'text': 'Distribución de Niveles',
                'x': 0.5,
                'xanchor': 'center'
            },
            showlegend=False,
            height=400
        )
        fig_niveles = apply_flourish_template(fig_niveles)
    else:
        fig_niveles = go.Figure()
    
    # Gráfico 3: Evolución (líneas suaves múltiples)
    if not data['evolucion'].empty:
        recent_data = data['evolucion'].sort_values(['anio', 'mes']).tail(60)
        top_agentes = data['anual'].head(10)['agente'].tolist()
        recent_data = recent_data[recent_data['agente'].isin(top_agentes)]
        
        if not recent_data.empty:
            recent_data['periodo'] = recent_data['anio'].astype(str) + '-' + recent_data['mes'].astype(str).str.zfill(2)
            
            fig_evolucion = go.Figure()
            
            for i, agente in enumerate(top_agentes):
                agente_data = recent_data[recent_data['agente'] == agente]
                if not agente_data.empty:
                    fig_evolucion.add_trace(go.Scatter(
                        x=agente_data['periodo'],
                        y=agente_data['horas_mes'],
                        mode='lines+markers',
                        name=agente,
                        line=dict(
                            color=COLOR_SCALE_FLOURISH[i % len(COLOR_SCALE_FLOURISH)],
                            width=2,
                            shape='spline'
                        ),
                        marker=dict(size=6),
                        hovertemplate='<b>%{fullData.name}</b><br>%{x}<br>Horas: %{y:.1f}h<extra></extra>'
                    ))
            
            fig_evolucion.update_layout(
                title='Evolución Mensual (Top 10)',
                height=500,
                legend=dict(
                    orientation='h',
                    yanchor='bottom',
                    y=-0.3,
                    xanchor='center',
                    x=0.5
                )
            )
            fig_evolucion = apply_flourish_template(fig_evolucion)
            fig_evolucion.update_xaxes(title='')
            fig_evolucion.update_yaxes(title='Horas')
        else:
            fig_evolucion = go.Figure()
    else:
        fig_evolucion = go.Figure()
    
    # Gráfico 4: Box plot minimalista
    if not data['actuales'].empty:
        fig_box = go.Figure()
        
        fig_box.add_trace(go.Box(
            y=data['actuales']['horas_mes'],
            name='',
            marker=dict(color=FLOURISH_COLORS['blue']),
            line=dict(color=FLOURISH_COLORS['blue']),
            fillcolor=f"rgba(33, 150, 243, 0.3)",
            boxmean='sd',
            hovertemplate='Horas: %{y:.1f}<extra></extra>'
        ))
        
        # Líneas de referencia
        fig_box.add_hline(y=60, line_dash="dash", line_color=FLOURISH_COLORS['red'], 
                         line_width=2, opacity=0.6,
                         annotation_text="Mínimo (60h)", annotation_position="right")
        fig_box.add_hline(y=90, line_dash="dash", line_color=FLOURISH_COLORS['yellow'], 
                         line_width=2, opacity=0.6,
                         annotation_text="Alto (90h)", annotation_position="right")
        
        fig_box.update_layout(
            title='Distribución de Horas',
            showlegend=False,
            height=400
        )
        fig_box = apply_flourish_template(fig_box)
        fig_box.update_yaxes(title='Horas Mensuales')
        fig_box.update_xaxes(showticklabels=False)
    else:
        fig_box = go.Figure()
    
    return {
        'ranking': fig_ranking,
        'niveles': fig_niveles,
        'evolucion': fig_evolucion,
        'box': fig_box
    }

def create_saldos_turno_chart(data):
    """Crear gráfico de saldos por turno estilo Flourish"""
    
    if data.empty:
        fig = go.Figure()
        return fig
    
    fig = go.Figure()
    
    # Agrupar por tipo de turno
    tipos_turno = data['tipo_turno'].unique()
    
    for i, tipo in enumerate(tipos_turno):
        tipo_data = data[data['tipo_turno'] == tipo]
        
        fig.add_trace(go.Bar(
            name=tipo.replace('_', ' ').title(),
            x=tipo_data['agente'],
            y=tipo_data['horas_totales'],
            marker=dict(
                color=COLOR_SCALE_FLOURISH[i % len(COLOR_SCALE_FLOURISH)],
                line=dict(width=0)
            ),
            text=tipo_data['horas_totales'].apply(lambda x: f"{x:.0f}h"),
            textposition='outside',
            textfont=dict(size=10),
            hovertemplate='<b>%{x}</b><br>%{fullData.name}<br>Horas: %{y:.1f}h<extra></extra>'
        ))
    
    fig.update_layout(
        title='Horas por Agente y Tipo de Turno',
        barmode='group',
        height=600,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.25,
            xanchor='center',
            x=0.5
        )
    )
    fig = apply_flourish_template(fig)
    fig.update_xaxes(title='', tickangle=-45)
    fig.update_yaxes(title='Horas')
    
    return fig

def create_dispositivos_charts(data):
    """Crear gráficos de dispositivos estilo Flourish"""
    
    # Gráfico 1: Por agente (burbujas + barras)
    if not data['por_agente'].empty:
        top_data = data['por_agente'].head(20)
        
        fig_por_agente = go.Figure()
        
        # Barras base
        fig_por_agente.add_trace(go.Bar(
            x=top_data['total_asignaciones'],
            y=top_data['agente'],
            orientation='h',
            marker=dict(
                color=top_data['dispositivos_diferentes'],
                colorscale=[[0, FLOURISH_COLORS['blue_light']], [1, FLOURISH_COLORS['blue']]],
                line=dict(width=0),
                colorbar=dict(title="Dispositivos<br>Diferentes", len=0.5)
            ),
            text=top_data['total_asignaciones'],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Total: %{x}<br>Dispositivos: %{marker.color}<extra></extra>'
        ))
        
        fig_por_agente.update_layout(
            title='Asignaciones por Agente',
            showlegend=False,
            height=600
        )
        fig_por_agente = apply_flourish_template(fig_por_agente)
        fig_por_agente.update_xaxes(title='Total Asignaciones')
        fig_por_agente.update_yaxes(title='', categoryorder='total ascending')
    else:
        fig_por_agente = go.Figure()
    
    # Gráfico 2: Heatmap elegante
    if not data['matriz'].empty:
        pivot = data['matriz'].pivot_table(
            index='agente',
            columns='nombre_dispositivo',
            values='asignaciones',
            fill_value=0
        )
        
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale=[[0, 'white'], [0.5, FLOURISH_COLORS['blue_light']], [1, FLOURISH_COLORS['blue']]],
            text=pivot.values,
            texttemplate='%{text}',
            textfont=dict(size=10),
            hovertemplate='<b>%{y}</b><br>%{x}<br>Asignaciones: %{z}<extra></extra>',
            colorbar=dict(title="Asignaciones")
        ))
        
        fig_heatmap.update_layout(
            title='Matriz Agente × Dispositivo',
            height=600
        )
        fig_heatmap = apply_flourish_template(fig_heatmap)
        fig_heatmap.update_xaxes(title='', side='bottom', tickangle=-45)
        fig_heatmap.update_yaxes(title='')
    else:
        fig_heatmap = go.Figure()
    
    # Gráfico 3: Top dispositivos (barras)
    if not data['top_dispositivos'].empty:
        fig_top = go.Figure(data=[go.Bar(
            x=data['top_dispositivos']['nombre_dispositivo'],
            y=data['top_dispositivos']['veces_asignado'],
            marker=dict(
                color=data['top_dispositivos']['piso_dispositivo'],
                colorscale=[[0, FLOURISH_COLORS['teal_light']], [1, FLOURISH_COLORS['teal']]],
                line=dict(width=0),
                colorbar=dict(title="Piso")
            ),
            text=data['top_dispositivos']['veces_asignado'],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Asignaciones: %{y}<br>Agentes: %{customdata}<extra></extra>',
            customdata=data['top_dispositivos']['agentes_distintos']
        )])
        
        fig_top.update_layout(
            title='Dispositivos Más Asignados',
            showlegend=False,
            height=400
        )
        fig_top = apply_flourish_template(fig_top)
        fig_top.update_xaxes(title='', tickangle=-45)
        fig_top.update_yaxes(title='Asignaciones')
    else:
        fig_top = go.Figure()
    
    # Gráfico 4: Temporal (área)
    if not data['temporal'].empty:
        fig_temporal = go.Figure()
        
        fig_temporal.add_trace(go.Scatter(
            x=data['temporal']['mes'],
            y=data['temporal']['asignaciones'],
            mode='lines+markers',
            line=dict(
                color=FLOURISH_COLORS['teal'],
                width=3,
                shape='spline'
            ),
            marker=dict(
                size=8,
                color=FLOURISH_COLORS['teal'],
                line=dict(color='white', width=2)
            ),
            fill='tozeroy',
            fillcolor=f"rgba(0, 188, 212, 0.1)",
            hovertemplate='<b>%{x}</b><br>Asignaciones: %{y}<extra></extra>'
        ))
        
        fig_temporal.update_layout(
            title='Evolución de Asignaciones',
            height=400
        )
        fig_temporal = apply_flourish_template(fig_temporal)
        fig_temporal.update_xaxes(title='')
        fig_temporal.update_yaxes(title='Asignaciones')
    else:
        fig_temporal = go.Figure()
    
    # Gráfico 5: Distribución (histograma moderno)
    if not data['por_agente'].empty:
        fig_dist = go.Figure(data=[go.Histogram(
            x=data['por_agente']['dispositivos_diferentes'],
            nbinsx=10,
            marker=dict(
                color=FLOURISH_COLORS['orange'],
                line=dict(color='white', width=1)
            ),
            hovertemplate='Dispositivos: %{x}<br>Agentes: %{y}<extra></extra>'
        )])
        
        fig_dist.update_layout(
            title='Distribución: Dispositivos por Agente',
            showlegend=False,
            height=350,
            bargap=0.1
        )
        fig_dist = apply_flourish_template(fig_dist)
        fig_dist.update_xaxes(title='Cantidad de Dispositivos Diferentes')
        fig_dist.update_yaxes(title='Número de Agentes')
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
# APLICACIÓN DASH CON ESTILO FLOURISH
# ============================================================================

# Inicializar app con Bootstrap (para mejor layout)
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
app.title = "Dashboard RRHH - Centro Cultural"

# CSS personalizado estilo Flourish
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
            * {
                font-family: 'Inter', 'Segoe UI', sans-serif;
            }
            body {
                background: #FAFAFA;
                margin: 0;
                padding: 0;
            }
            .main-header {
                background: linear-gradient(135deg, #7C4DFF 0%, #2196F3 100%);
                color: white;
                padding: 30px 40px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .main-header h1 {
                margin: 0;
                font-size: 28px;
                font-weight: 600;
                letter-spacing: -0.5px;
            }
            .main-header p {
                margin: 5px 0 0 0;
                opacity: 0.9;
                font-size: 14px;
                font-weight: 400;
            }
            .dash-tab {
                font-size: 14px !important;
                font-weight: 500 !important;
                color: #546E7A !important;
                border: none !important;
                padding: 12px 24px !important;
                background: transparent !important;
                transition: all 0.2s ease !important;
            }
            .dash-tab--selected {
                color: #7C4DFF !important;
                border-bottom: 3px solid #7C4DFF !important;
                background: white !important;
            }
            .dash-tab:hover {
                color: #7C4DFF !important;
                background: rgba(124, 77, 255, 0.05) !important;
            }
            #tab-content {
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.08);
                margin: 20px 40px;
                padding: 30px;
            }
            .footer {
                text-align: center;
                padding: 20px;
                color: #90A4AE;
                font-size: 12px;
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
    # Header moderno
    html.Div([
        html.H1("Dashboard RRHH"),
        html.P("Sistema de Gestión de Recursos Humanos - El Molino Fábrica Cultural")
    ], className='main-header'),
    
    # Tabs elegantes
    dcc.Tabs(id='tabs', value='inasistencias', children=[
        dcc.Tab(label='📊 Inasistencias', value='inasistencias'),
        dcc.Tab(label='⏱️ Saldos por Agente', value='saldos'),
        dcc.Tab(label='🔄 Saldos por Turno', value='saldos_turno'),
        dcc.Tab(label='🖥️ Dispositivos', value='dispositivos'),
    ], style={'borderBottom': '1px solid #ECEFF1', 'background': 'white'}),
    
    # Contenido
    html.Div(id='tab-content'),
    
    # Footer minimalista
    html.Div([
        html.P("Sistema RRHH v3.0 DAMA • Pablo - Data Analyst • Diciembre 2025")
    ], className='footer')
])

# Callback para actualizar contenido
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
                html.H2("Análisis de Inasistencias", 
                       style={'marginBottom': '30px', 'color': FLOURISH_COLORS['text_primary']}),
                
                dcc.Graph(figure=charts['total'], config={'displayModeBar': False}),
                
                html.Div([
                    html.Div([dcc.Graph(figure=charts['tipo'])], 
                            style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                    html.Div([dcc.Graph(figure=charts['estado'])], 
                            style={'width': '48%', 'display': 'inline-block', 'float': 'right', 'verticalAlign': 'top'})
                ], style={'marginBottom': '20px'}),
                
                html.Div([
                    html.Div([dcc.Graph(figure=charts['temporal'])], 
                            style={'width': '65%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                    html.Div([dcc.Graph(figure=charts['certificados'])], 
                            style={'width': '33%', 'display': 'inline-block', 'float': 'right', 'verticalAlign': 'top'})
                ])
            ])
        except Exception as e:
            return html.Div([
                html.H2("⚠️ Error", style={'color': FLOURISH_COLORS['red']}),
                html.P(f"No se pudieron cargar los datos: {str(e)}")
            ])
    
    elif tab == 'saldos':
        try:
            data = get_saldos_data()
            charts = create_saldos_charts(data)
            
            return html.Div([
                html.H2("Análisis de Saldos por Agente",
                       style={'marginBottom': '30px', 'color': FLOURISH_COLORS['text_primary']}),
                
                html.Div([
                    html.Div([dcc.Graph(figure=charts['ranking'])], 
                            style={'width': '65%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                    html.Div([dcc.Graph(figure=charts['niveles'])], 
                            style={'width': '33%', 'display': 'inline-block', 'float': 'right', 'verticalAlign': 'top'})
                ], style={'marginBottom': '20px'}),
                
                html.Div([
                    html.Div([dcc.Graph(figure=charts['evolucion'])], 
                            style={'width': '65%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                    html.Div([dcc.Graph(figure=charts['box'])], 
                            style={'width': '33%', 'display': 'inline-block', 'float': 'right', 'verticalAlign': 'top'})
                ])
            ])
        except Exception as e:
            return html.Div([
                html.H2("⚠️ Error", style={'color': FLOURISH_COLORS['red']}),
                html.P(f"No se pudieron cargar los datos: {str(e)}")
            ])
    
    elif tab == 'saldos_turno':
        try:
            data = get_saldos_por_turno()
            chart = create_saldos_turno_chart(data)
            
            return html.Div([
                html.H2("Saldos por Agente y Tipo de Turno",
                       style={'marginBottom': '30px', 'color': FLOURISH_COLORS['text_primary']}),
                dcc.Graph(figure=chart)
            ])
        except Exception as e:
            return html.Div([
                html.H2("⚠️ Error", style={'color': FLOURISH_COLORS['red']}),
                html.P(f"No se pudieron cargar los datos: {str(e)}")
            ])
    
    elif tab == 'dispositivos':
        try:
            data = get_dispositivos_data()
            charts = create_dispositivos_charts(data)
            
            return html.Div([
                html.H2("Análisis de Asignaciones de Dispositivos",
                       style={'marginBottom': '30px', 'color': FLOURISH_COLORS['text_primary']}),
                
                html.Div([
                    html.Div([dcc.Graph(figure=charts['por_agente'])], 
                            style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                    html.Div([dcc.Graph(figure=charts['heatmap'])], 
                            style={'width': '48%', 'display': 'inline-block', 'float': 'right', 'verticalAlign': 'top'})
                ], style={'marginBottom': '20px'}),
                
                html.Div([
                    html.Div([dcc.Graph(figure=charts['top'])], 
                            style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                    html.Div([dcc.Graph(figure=charts['temporal'])], 
                            style={'width': '48%', 'display': 'inline-block', 'float': 'right', 'verticalAlign': 'top'})
                ], style={'marginBottom': '20px'}),
                
                dcc.Graph(figure=charts['distribucion'])
            ])
        except Exception as e:
            return html.Div([
                html.H2("⚠️ Error", style={'color': FLOURISH_COLORS['red']}),
                html.P(f"No se pudieron cargar los datos: {str(e)}")
            ])

# ============================================================================
# EJECUTAR APLICACIÓN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("  DASHBOARD RRHH - Centro Cultural (Estilo Flourish)")
    print("="*70)
    print(f"\n📁 Base de datos: {DB_PATH}")
    
    if Path(DB_PATH).exists():
        print("✅ Base de datos encontrada")
        
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
    
    print("\n🚀 Iniciando servidor...")
    print("📊 Abre tu navegador en: http://127.0.0.1:8050/")
    print("\n   Presiona Ctrl+C para detener el servidor\n")
    
    app.run(debug=True, host='127.0.0.1', port=8050)
