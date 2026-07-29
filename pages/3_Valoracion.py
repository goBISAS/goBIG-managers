import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Configuración
st.set_page_config(page_title="goBIG Valoración", page_icon="💎", layout="wide")

# --- CANDADO DE SEGURIDAD ---
if not st.session_state.get("authentication_status"):
    st.warning("🔒 Acceso denegado. Por favor dirígete a la página de inicio (app) para iniciar sesión.")
    st.stop()
# ----------------------------

with st.sidebar:
    st.image("goBIG_logo.jpg", width=200)
    st.markdown("---")
    st.caption("v2.0 - Consola de Control Financiero Integral")

st.title("💎 Rendimientos y Valoración Corporativa")
st.markdown("Análisis histórico de rentabilidad y evolución de la valoración Pre-Money de goBIG S.A.S.")
st.markdown("---")

# Función traductora de formatos latinos a formato de computadora
def clean_currency_global(val):
    if pd.isna(val) or str(val).strip() in ['', 'nan', 'None', '<NA>']: return 0.0
    if isinstance(val, (int, float)): return float(val)
    val_str = str(val).replace('$', '').replace('%', '').replace(' ', '').strip()
    
    if ',' in val_str and '.' in val_str:
        if val_str.rfind(',') > val_str.rfind('.'): 
            val_str = val_str.replace('.', '').replace(',', '.')
        else: 
            val_str = val_str.replace(',', '')
    elif '.' in val_str:
        parts = val_str.split('.')
        if len(parts) > 2 or len(parts[-1]) == 3:
            val_str = val_str.replace('.', '')
    elif ',' in val_str: 
        parts = val_str.split(',')
        if len(parts) > 2 or len(parts[-1]) == 3:
            val_str = val_str.replace(',', '')
        else:
            val_str = val_str.replace(',', '.')
            
    try: return float(val_str)
    except ValueError: return 0.0

# 2. Extractor de Datos
@st.cache_data(ttl=600)
def load_valuation_data():
    try:
        url_doc = "https://docs.google.com/spreadsheets/d/1ldntONNpWFgXPcF8VINDKzNAhG_vGMdzGEOESM3aLNU/export?format=xlsx"
        xls = pd.ExcelFile(url_doc)
        sheet_names = xls.sheet_names
        
        s_rendimientos = [s for s in sheet_names if 'rendimient' in s.lower()]
        s_valoracion = [s for s in sheet_names if 'valoraci' in s.lower()]
        
        df_rend = pd.read_excel(xls, sheet_name=s_rendimientos[0]) if s_rendimientos else pd.DataFrame()
        df_val = pd.read_excel(xls, sheet_name=s_valoracion[0]) if s_valoracion else pd.DataFrame()
        
        return df_rend, df_val
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame()

with st.spinner("Descargando modelos financieros y de valoración..."):
    df_rend, df_val = load_valuation_data()

if df_rend.empty and df_val.empty:
    st.warning("No se encontraron datos. Asegúrate de haber nombrado las pestañas como 'rendimientos' y 'valoración'.")
    st.stop()

# --- SECCIÓN 1: RENDIMIENTOS ---
st.subheader("📈 1. Rendimientos Anuales Históricos")

if not df_rend.empty:
    df_rend.columns = [str(c).strip() for c in df_rend.columns]
    
    # Mapeo EXACTO por la posición de las columnas en tu Excel
    c_ano_r = df_rend.columns[0]
    c_ingresos = df_rend.columns[1]
    c_utilidad_r = df_rend.columns[2]
    c_ebitda = df_rend.columns[3]
    c_margen = df_rend.columns[4]

    # Limpiar datos
    df_rend[c_ingresos] = df_rend[c_ingresos].apply(clean_currency_global)
    df_rend[c_utilidad_r] = df_rend[c_utilidad_r].apply(clean_currency_global)
    df_rend[c_ebitda] = df_rend[c_ebitda].apply(clean_currency_global)
    df_rend[c_margen] = df_rend[c_margen].apply(clean_currency_global)
    
    # Ajuste de porcentaje (Si es mayor a 2, asumimos que dice 33.6 en vez de 0.33)
    if df_rend[c_margen].abs().max() > 2: 
        df_rend[c_margen] = df_rend[c_margen] / 100.0

    # Layout de KPIs
    c1, c2, c3 = st.columns(3)
    ult_ano_r = str(df_rend[c_ano_r].iloc[-1]).replace('.0', '')
    ingresos_ult = df_rend[c_ingresos].iloc[-1]
    ebitda_ult = df_rend[c_ebitda].iloc[-1]
    margen_ult = df_rend[c_margen].iloc[-1]

    c1.metric(f"Ingresos Ordinarios ({ult_ano_r})", f"${ingresos_ult:,.0f}")
    c2.metric(f"EBITDA ({ult_ano_r})", f"${ebitda_ult:,.0f}")
    c3.metric(f"Margen EBITDA ({ult_ano_r})", f"{margen_ult:.1%}")

    # Gráfico y Tabla lado a lado
    col_chart, col_table = st.columns([5, 5])
    
    with col_chart:
        fig_r = go.Figure()
        fig_r.add_trace(go.Bar(x=df_rend[c_ano_r], y=df_rend[c_ingresos], name='Ingresos', marker_color='#1f77b4'))
        fig_r.add_trace(go.Bar(x=df_rend[c_ano_r], y=df_rend[c_ebitda], name='EBITDA', marker_color='#2ca02c'))
        fig_r.update_layout(title="Crecimiento: Ingresos vs EBITDA", barmode='group', height=350, margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig_r, use_container_width=True)

    with col_table:
        st.write("**Tabla de Rendimientos**")
        df_rend_disp = df_rend.copy()
        df_rend_disp[c_ano_r] = df_rend_disp[c_ano_r].astype(str).str.replace('.0', '', regex=False)
        df_rend_disp[c_ingresos] = df_rend_disp[c_ingresos].apply(lambda x: f"${x:,.0f}")
        df_rend_disp[c_utilidad_r] = df_rend_disp[c_utilidad_r].apply(lambda x: f"${x:,.0f}")
        df_rend_disp[c_ebitda] = df_rend_disp[c_ebitda].apply(lambda x: f"${x:,.0f}")
        df_rend_disp[c_margen] = df_rend_disp[c_margen].apply(lambda x: f"{x:.2%}")
        st.dataframe(df_rend_disp, hide_index=True, use_container_width=True)

st.markdown("---")

# --- SECCIÓN 2: VALORACIÓN PRE-MONEY ---
st.subheader("💎 2. Valoración Pre-Money (Múltiplo EBITDA)")

if not df_val.empty:
    df_val.columns = [str(c).strip() for c in df_val.columns]
    
    # Mapeo EXACTO por la posición de las columnas
    c_ano_v = df_val.columns[0]
    c_utilidad_v = df_val.columns[1]
    c_multiplo = df_val.columns[2]
    c_val_cop = df_val.columns[3]
    c_val_usd = df_val.columns[4] if len(df_val.columns) > 4 else None

    # Limpiar datos numéricos
    df_val[c_utilidad_v] = df_val[c_utilidad_v].apply(clean_currency_global)
    df_val[c_val_cop] = df_val[c_val_cop].apply(clean_currency_global)
    if c_val_usd: df_val[c_val_usd] = df_val[c_val_usd].apply(clean_currency_global)

    ult_ano_v = str(df_val[c_ano_v].iloc[-1]).replace('.0', '')
    val_cop_ult = df_val[c_val_cop].iloc[-1]
    
    delta_cop = 0
    if len(df_val) > 1:
        val_cop_prev = df_val[c_val_cop].iloc[-2]
        delta_cop = val_cop_ult - val_cop_prev

    # KPI principal gigante
    st.metric(f"Valoración Actual de la Compañía ({ult_ano_v})", f"${val_cop_ult:,.0f} COP", delta=f"+${delta_cop:,.0f} de crecimiento patrimonial vs año anterior" if delta_cop > 0 else None)

    col_v_chart, col_v_table = st.columns([5, 5])
    
    with col_v_chart:
        fig_v = px.line(df_val, x=c_ano_v, y=c_val_cop, markers=True, title="Curva de Valoración Exponencial (COP)")
        fig_v.update_traces(line=dict(width=4, color='#ff7f0e'), marker=dict(size=12, color='white', line=dict(width=2, color='#ff7f0e')))
        fig_v.update_layout(height=350, margin=dict(t=40, b=10, l=10, r=10), yaxis_title="Valoración (COP)", xaxis_title="Año", xaxis=dict(dtick=1))
        st.plotly_chart(fig_v, use_container_width=True)

    with col_v_table:
        st.write("**Histórico de Múltiplos y Valoración**")
        df_val_disp = df_val.copy()
        df_val_disp[c_ano_v] = df_val_disp[c_ano_v].astype(str).str.replace('.0', '', regex=False)
        df_val_disp[c_utilidad_v] = df_val_disp[c_utilidad_v].apply(lambda x: f"${x:,.0f}")
        df_val_disp[c_val_cop] = df_val_disp[c_val_cop].apply(lambda x: f"${x:,.0f}")
        if c_val_usd: df_val_disp[c_val_usd] = df_val_disp[c_val_usd].apply(lambda x: f"${x:,.0f}")
        st.dataframe(df_val_disp, hide_index=True, use_container_width=True)
