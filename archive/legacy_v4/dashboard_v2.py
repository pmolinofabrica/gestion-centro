import streamlit as st
import pandas as pd
import sqlite3
import math

# ==============================================================================
# CONFIGURACIÓN DE LA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Dashboard RRHH - Gestión Avanzada",
    page_icon="📊",
    layout="wide"
)

DB_PATH = 'data/gestion_rrhh.db'

# ==============================================================================
# FUNCIONES DE ACCESO A DATOS
# ==============================================================================
@st.cache_data(ttl=60)
def cargar_datos(query):
    """Carga datos desde SQLite y los cachea por 60 segundos"""
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return pd.DataFrame()

def aplicar_filtros_estilo_sheets(df, key_prefix):
    """
    Implementa filtros tipo Google Sheets (ordenar y filtrar por valores)
    """
    with st.expander(f"🔍 Filtros y Ordenamiento ({key_prefix})", expanded=False):
        col1, col2 = st.columns([1, 3])
        
        # 1. Ordenar
        with col1:
            st.markdown("##### Ordenar")
            sort_col = st.selectbox("Columna", ["Ninguna"] + list(df.columns), key=f"{key_prefix}_sort_col")
            sort_asc = st.radio("Dirección", ["Ascendente (A-Z)", "Descendente (Z-A)"], key=f"{key_prefix}_sort_asc")
            
            if sort_col != "Ninguna":
                ascending = True if sort_asc == "Ascendente (A-Z)" else False
                df = df.sort_values(by=sort_col, ascending=ascending)

        # 2. Filtrar por valores (Checkbox style)
        with col2:
            st.markdown("##### Filtrar por Valores")
            filter_cols = st.multiselect(
                "Selecciona columnas para filtrar:", 
                df.columns,
                key=f"{key_prefix}_filter_cols"
            )
            
            for col in filter_cols:
                # Obtener valores únicos para las casillas de verificación
                unique_values = df[col].unique()
                selected_values = st.multiselect(
                    f"Valores para '{col}':",
                    options=unique_values,
                    default=unique_values, # Por defecto todos seleccionados
                    key=f"{key_prefix}_filter_val_{col}"
                )
                # Aplicar filtro
                if selected_values:
                    df = df[df[col].isin(selected_values)]
    
    return df

def mostrar_tabla_paginada(df, titulo, key_prefix):
    """
    Muestra una tabla con paginación y controles
    """
    st.subheader(titulo)
    
    # 1. Aplicar Filtros Avanzados (Requerimiento 3)
    df_filtrado = aplicar_filtros_estilo_sheets(df, key_prefix)
    
    # Controles de Paginación (Requerimiento 2)
    col_pag1, col_pag2, col_pag3, col_pag4 = st.columns([2, 2, 3, 2])
    
    with col_pag1:
        rows_per_page = st.selectbox(
            "Filas por página", 
            options=[20, 50, 100, 200], 
            index=0,
            key=f"{key_prefix}_rows"
        )
    
    total_rows = len(df_filtrado)
    total_pages = math.ceil(total_rows / rows_per_page)
    
    # Estado de la página actual en session_state
    page_key = f"{key_prefix}_current_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
        
    # Asegurar que la página es válida tras filtrar
    if st.session_state[page_key] > total_pages:
        st.session_state[page_key] = max(1, total_pages)

    with col_pag2:
        st.write("") # Espaciador vertical
        st.write(f"**Total:** {total_rows} registros")

    # Botones de navegación
    with col_pag3:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.button("◀", key=f"{key_prefix}_prev"):
                if st.session_state[page_key] > 1:
                    st.session_state[page_key] -= 1
                    st.rerun()
        with c2:
            st.markdown(f"<div style='text-align: center; padding-top: 5px;'>Pág. {st.session_state[page_key]} de {total_pages}</div>", unsafe_allow_html=True)
        with c3:
            if st.button("▶", key=f"{key_prefix}_next"):
                if st.session_state[page_key] < total_pages:
                    st.session_state[page_key] += 1
                    st.rerun()

    # Calcular slice de datos
    start_idx = (st.session_state[page_key] - 1) * rows_per_page
    end_idx = start_idx + rows_per_page
    
    # Mostrar Tabla
    st.dataframe(
        df_filtrado.iloc[start_idx:end_idx],
        use_container_width=True,
        hide_index=True
    )

# ==============================================================================
# INTERFAZ PRINCIPAL
# ==============================================================================

st.title("🏢 Centro Cultural - Gestión de RRHH")

# --- BARRA LATERAL (Requerimiento 1) ---
st.sidebar.header("Explorador de Tablas")

# Opción para agregar segunda tabla
mostrar_segunda_tabla = st.sidebar.checkbox(
    "Agregar Tabla Comparativa", 
    value=False,
    help="Activa esta casilla para ver dos tablas simultáneamente."
)

# --- CARGA DE DATOS ---
# Usamos la vista 'vista_convocatorias_activas' si existe, o un query manual
query_principal = """
    SELECT 
        c.id_convocatoria,
        c.fecha_convocatoria as Fecha,
        dp.apellido || ', ' || dp.nombre as Agente,
        t.tipo_turno as Turno,
        c.estado as Estado
    FROM convocatoria c
    JOIN datos_personales dp ON c.id_agente = dp.id_agente
    LEFT JOIN turnos t ON c.id_turno = t.id_turno
    ORDER BY c.fecha_convocatoria DESC
"""

df_principal = cargar_datos(query_principal)

# --- TABLA PRINCIPAL ---
mostrar_tabla_paginada(df_principal, "📋 Convocatorias (Principal)", "tabla1")

# --- TABLA SECUNDARIA (Condicional) ---
if mostrar_segunda_tabla:
    st.markdown("---")
    st.info("Modo Comparativo Activado")
    
    # Selector de qué ver en la segunda tabla
    opcion_tabla_2 = st.sidebar.selectbox(
        "Seleccionar datos para Tabla 2",
        ["Saldos de Horas", "Inasistencias", "Personal"]
    )
    
    queries = {
        "Saldos de Horas": "SELECT * FROM saldos",
        "Inasistencias": "SELECT * FROM inasistencias",
        "Personal": "SELECT id_agente, nombre, apellido, dni, email, activo FROM datos_personales"
    }
    
    df_secundario = cargar_datos(queries[opcion_tabla_2])
    mostrar_tabla_paginada(df_secundario, f"📊 {opcion_tabla_2} (Secundaria)", "tabla2")