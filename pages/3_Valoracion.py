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

try:
    df_rend, df_val = load_data()
except Exception as e:
    st.error(f"Error al cargar los datos de Excel: {e}")
    st.stop()

# 3. Sección de Rendimientos Anuales Históricos
st.subheader("📈 1. Rendimientos Anuales Históricos")

if not df_rend.empty:
    st.dataframe(df_rend, use_container_width=True)
    
    # --- LECTURA SEGURA DE COLUMNAS (A PRUEBA DE INDEXERROR) ---
    cols = df_rend.columns.tolist()
    c_ano = cols[0] if len(cols) > 0 else None
    c_ing = cols[1] if len(cols) > 1 else None
    c_ebitda = cols[3] if len(cols) > 3 else (cols[2] if len(cols) > 2 else None)
    c_margen = cols[4] if len(cols) > 4 else (cols[-1] if len(cols) > 0 else None)
    
    # Gráficos dinámicos
    if c_ano and c_ing:
        cols_grafico = [c for c in [c_ing, c_ebitda] if c]
        fig_rend = px.bar(
            df_rend, 
            x=c_ano, 
            y=cols_grafico, 
            barmode="group",
            title="Evolución de Ingresos vs. EBITDA",
            labels={"value": "Monto ($)", "variable": "Métrica"}
        )
        st.plotly_chart(fig_rend, use_container_width=True)
else:
    st.info("No se encontraron datos en la pestaña de Rendimientos.")

st.markdown("---")

# 4. Sección de Valoración Pre-Money
st.subheader("💎 2. Evolución de la Valoración Corporativa (Pre-Money)")

if not df_val.empty:
    st.dataframe(df_val, use_container_width=True)
    
    cols_val = df_val.columns.tolist()
    if len(cols_val) >= 2:
        fig_val = px.line(
            df_val, 
            x=cols_val[0], 
            y=cols_val[-1], 
            markers=True,
            title="Evolución de la Valoración Pre-Money"
        )
        st.plotly_chart(fig_val, use_container_width=True)
else:
    st.info("No se encontraron datos en la pestaña de Valoración.")
