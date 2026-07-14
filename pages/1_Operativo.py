import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="goBIG Operativo v1.1", page_icon="⚙️", layout="wide")

# Barra lateral con Identidad Continua
with st.sidebar:
    st.image("goBIG_logo.jpg", width=200)
    st.markdown("---")
    st.caption("v1.1 - Consola de Control Operativo")
    st.info("🧱 **Actualización:** Treemap híbrido mostrando Costos y Horas de Esfuerzo simultáneamente.")

st.title("⚙️ Operativa y Rentabilidad de Proyectos")
st.markdown("Análisis de esfuerzo de los consultores cruzado con el costo por hora en tiempo real.")
st.markdown("---")

# --- 2. MAPEO Y CONSTANTES ---
MAPA_CONSULTORES = {
    "Jimmy Peña": "JIMMY PEÑA",
    "Alejandra Buriticá": "ALEJANDRA BURITICA",
    "Alejandra Cárdenas": "MARIA ALEJANDRA CARDENAS",
    "Sebastian Saenz": "SEBASTIAN SAENZ"
}

IDS = {
    'fin': "1ldntONNpWFgXPcF8VINDKzNAhG_vGMdzGEOESM3aLNU",
    'ops': "1Vl5rhQDi6YooJgjYAF76oOO0aN8rbPtu07giky36wSo"
}

# --- 3. FUNCIONES UTILITARIAS ---
def limpiar_moneda_colombia(serie):
    if serie is None: return pd.Series([])
    serie = serie.astype(str).str.replace(r'[$\s]', '', regex=True)
    serie = serie.str.replace('.', '', regex=False)
    serie = serie.str.replace(',', '.', regex=False)
    return pd.to_numeric(serie, errors='coerce').fillna(0)

# --- 4. MOTOR DE EXTRACCIÓN SEGURO Y CACHEADO ---
@st.cache_data(ttl=600)
def load_operational_data():
    errores = []
    data = {"ops": pd.DataFrame(), "costos": pd.DataFrame()}
    
    try:
        # Autenticación con Google Sheets
        json_str = st.secrets["credenciales_json"]
        key_dict = json.loads(json_str, strict=False)
        creds = Credentials.from_service_account_info(
            key_dict, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)
        
        # Abrir libros
        sh_fin = client.open_by_key(IDS['fin'])
        sh_ops = client.open_by_key(IDS['ops'])
        
        # A. Carga Diccionario de Recursos (Costo Hora)
        try:
            df_costos = pd.DataFrame(sh_fin.worksheet("04_Diccionario de recursos desde 2026").get_all_records())
            col_ch = next((c for c in df_costos.columns if "Costo Hora" in c), None)
            if col_ch:
                df_costos[col_ch] = limpiar_moneda_colombia(df_costos[col_ch])
                df_costos['COLABORADOR'] = df_costos['COLABORADOR'].astype(str).str.strip().str.upper()
                data['costos'] = df_costos
        except Exception as e:
            errores.append(f"Error cargando Diccionario de Recursos: {e}")
            
        # B. Carga Backlog de Consultores (Pestañas Individuales)
        all_tasks = []
        for pestana, nombre_normalizado in MAPA_CONSULTORES.items():
            try:
                raw = sh_ops.worksheet(pestana).get_all_values()
                if len(raw) > 5:
                    header = raw[4] # Fila 5 contiene las cabeceras reales
                    df = pd.DataFrame(raw[5:], columns=header)
                    df['Consultor_Pestana'] = pestana
                    df['Consultor_Cruce'] = nombre_normalizado
                    
                    # Limpieza de columnas de tiempo
                    for c in ['Tiempo estimado', 'Tiempo real']:
                        if c in df.columns:
                            df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                    
                    if 'Fecha de entrega' in df.columns:
                        df['Fecha de entrega'] = pd.to_datetime(df['Fecha de entrega'], dayfirst=True, errors='coerce')
                        
                    all_tasks.append(df)
            except Exception as e:
                pass # Tolerancia si un consultor no tiene pestaña activa
                
        if all_tasks:
            data['ops'] = pd.concat(all_tasks, ignore_index=True)
        else:
            errores.append("No se cargó ninguna tarea del Backlog.")
            
    except Exception as e:
        errores.append(f"Error de conexión con Sheets: {e}")
        
    return data, errores

# --- 5. EJECUCIÓN DEL MOTOR ---
if st.sidebar.button("🔄 Forzar Recarga Operativa"):
    st.cache_data.clear()

with st.spinner("Descargando Backlog y mapeando costos por hora..."):
    data, errores = load_operational_data()

if errores:
    with st.expander("⚠️ Alertas de Integridad de Datos", expanded=True):
        for err in errores:
            st.error(err)

# --- 6. PROCESAMIENTO Y CRUCE (DF_FILTRADO) ---
if not data['ops'].empty and not data['costos'].empty:
    # Hacemos el cruce (JOIN) entre Backlog y Costo Hora
    df_filtrado = pd.merge(data['ops'], data['costos'], left_on='Consultor_Cruce', right_on='COLABORADOR', how='left')
    
    col_costo = next((c for c in df_filtrado.columns if "Costo Hora" in c), None)
    if col_costo:
        df_filtrado['Costo_Devengado'] = df_filtrado['Tiempo real'] * df_filtrado[col_costo]
    else:
        df_filtrado['Costo_Devengado'] = 0.0
        
    # --- FILTROS DE INTERFAZ ---
    st.sidebar.markdown("### 🔍 Filtros de Consulta")
    consultor_sel = st.sidebar.selectbox("Filtrar Consultor:", ["Todos"] + list(MAPA_CONSULTORES.keys()))
    
    cliente_col = next((c for c in df_filtrado.columns if "cliente" in c.lower()), None)
    clientes_disponibles = sorted(list(df_filtrado[cliente_col].dropna().unique())) if cliente_col else []
    cliente_sel = st.sidebar.selectbox("Filtrar por Cliente:", ["Todos"] + clientes_disponibles)
    
    # Aplicación de filtros
    if consultor_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Consultor_Pestana'] == consultor_sel]
    if cliente_sel != "Todos" and cliente_col:
        df_filtrado = df_filtrado[df_filtrado[cliente_col] == cliente_sel]

    # --- KPIs PRINCIPALES ---
    k1, k2, k3 = st.columns(3)
    total_horas = df_filtrado['Tiempo real'].sum()
    total_costo = df_filtrado['Costo_Devengado'].sum()
    
    k1.metric("Esfuerzo Total Invertido", f"{total_horas:.1f} Hrs")
    k2.metric("Costo Nómina Devengado", f"${total_costo:,.0f} COP")
    k3.metric("Tareas Registradas", len(df_filtrado))
    
    st.markdown("---")

    # --- 7. VISUALIZACIÓN: TREEMAP HÍBRIDO ---
    st.subheader("🧱 Distribución de Presupuesto y Esfuerzo por Tarea")
    
    # Agrupamos por Cliente y Tipo de tarea sumando Costo y Horas
    tipo_tarea_col = next((c for c in df_filtrado.columns if "tarea" in c.lower()), None)
    
    if cliente_col and tipo_tarea_col:
        df_treemap = df_filtrado.groupby([cliente_col, tipo_tarea_col])[['Costo_Devengado', 'Tiempo real']].sum().reset_index()
        # Filtramos costos huérfanos o en cero
        df_treemap = df_treemap[df_treemap['Costo_Devengado'] > 0]
        
        if not df_treemap.empty:
            fig_tree = px.treemap(
                df_treemap, 
                path=[cliente_col, tipo_tarea_col], 
                values='Costo_Devengado',
                custom_data=['Tiempo real'],
                color=cliente_col,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            
            fig_tree.update_traces(
                texttemplate="<b>%{label}</b><br>Costo: $%{value:,.0f}<br>Esfuerzo: %{customdata[0]:.1f} hrs",
                textposition="middle center",
                hovertemplate="<b>%{label}</b><br>Costo: $%{value:,.0f}<br>Esfuerzo: %{customdata[0]:.1f} hrs<extra></extra>"
            )
            
            fig_tree.update_layout(
                template="plotly_dark", 
                margin=dict(t=30, l=10, r=10, b=10),
                height=500
            )
            
            st.plotly_chart(fig_tree, use_container_width=True)
        else:
            st.info("No hay tareas con costos mayores a cero para el filtro seleccionado.")
    else:
        st.error("No se encontraron las columnas de Cliente o Tipo de Tarea en la base de datos.")

else:
    st.warning("⚠️ Sin datos para procesar. Verifica que el Backlog y el Diccionario de Recursos tengan registros activos.")
