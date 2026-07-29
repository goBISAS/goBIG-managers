import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la página
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

# 2. Cargar Datos desde Google Drive
@st.cache_data(ttl=600)
def load_data():
    url_doc = "https://docs.google.com/spreadsheets/d/1ldntONNpWFgXPcF8VINDKzNAhG_vGMdzGEOESM3aLNU/export?format=xlsx"
    xls = pd.ExcelFile(url_doc)
    sheet_names = xls.sheet_names
    
    s_rend = [s for s in sheet_names if 'rendimient' in s.lower()]
    s_val = [s for s in sheet_names if 'valoraci' in s.lower()]
    
    df_rend = pd.read_excel(xls, sheet_name=s_rend[0]) if s_rend else pd.DataFrame()
    df_val = pd.read_excel(xls, sheet_name=s_val[0]) if s_val else pd.DataFrame()
    return df_rend, df_val

# Función auxiliar para convertir textos con formato ($ / .) a números limpios para la gráfica
def clean_numeric_series(series):
    cleaned = series.astype(str).str.replace('$', '', regex=False).str.replace(' ', '', regex=False)
    cleaned = cleaned.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    return pd.to_numeric(cleaned, errors='coerce').fillna(0)

try:
    df_rend, df_val = load_data()
except Exception as e:
    st.error(f"Error al cargar los datos de Excel: {e}")
    st.stop()

# 3. Sección de Rendimientos Anuales Históricos
st.subheader("📈 1. Rendimientos Anuales Históricos")

if not df_rend.empty:
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        st.markdown("##### 📊 Tabla de Datos")
        st.dataframe(df_rend, use_container_width=True)
        
    with col2:
        cols = df_rend.columns.tolist()
        c_ano = cols[0] if len(cols) > 0 else None
        c_ing = cols[1] if len(cols) > 1 else None
        c_ebitda = cols[3] if len(cols) > 3 else (cols[2] if len(cols) > 2 else None)
        
        if c_ano and c_ing:
            df_rend_plot = df_rend.copy()
            df_rend_plot[c_ing] = clean_numeric_series(df_rend_plot[c_ing])
            if c_ebitda:
                df_rend_plot[c_ebitda] = clean_numeric_series(df_rend_plot[c_ebitda])
            
            cols_grafico = [c for c in [c_ing, c_ebitda] if c]
            fig_rend = px.bar(
                df_rend_plot, 
                x=c_ano, 
                y=cols_grafico, 
                barmode="group",
                text_auto=True,
                title="Evolución de Ingresos vs. EBITDA",
                labels={"value": "Monto ($)", "variable": "Métrica"}
            )
            fig_rend.update_traces(textposition="outside")
            fig_rend.update_layout(margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_rend, use_container_width=True)
else:
    st.info("No se encontraron datos en la pestaña de Rendimientos.")

st.markdown("---")

# 4. Sección de Valoración Pre-Money
st.subheader("💎 2. Evolución de la Valoración Corporativa (Pre-Money)")

if not df_val.empty:
    col_v1, col_v2 = st.columns([1, 1.2])
    
    with col_v1:
        st.markdown("##### 📊 Tabla de Valoración")
        st.dataframe(df_val, use_container_width=True)
        
    with col_v2:
        cols_val = df_val.columns.tolist()
        if len(cols_val) >= 2:
            df_val_plot = df_val.copy()
            col_x = cols_val[0]
            col_y = cols_val[-1]
            
            # Limpieza limpia exclusiva para renderizar el gráfico
            df_val_plot[col_y] = clean_numeric_series(df_val_plot[col_y])
            
            fig_val = px.line(
                df_val_plot, 
                x=col_x, 
                y=col_y, 
                markers=True,
                text_auto=True,
                title="Evolución Valoración Pre-Money ($)"
            )
            fig_val.update_traces(textposition="top center")
            fig_val.update_layout(margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_val, use_container_width=True)
else:
    st.info("No se encontraron datos en la pestaña de Valoración.")
