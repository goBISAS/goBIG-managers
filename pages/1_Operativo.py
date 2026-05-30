import streamlit as st
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Operativo", page_icon="⚙️", layout="wide")

st.title("⚙️ Dashboard Operativo y de Costos")
st.markdown("Visualización en tiempo real del Backlog cruzado con Costos de Nómina.")
st.markdown("---")

# 2. Motor de extracción y procesamiento de datos
@st.cache_data(ttl=600) # Guarda los datos en memoria por 10 min
def load_data():
    try:
        # A. Extraer Backlog
        url_backlog = "https://docs.google.com/spreadsheets/d/1Vl5rhQDi6YooJgjYAF76oOO0aN8rbPtu07giky36wSo/export?format=xlsx"
        xls = pd.read_excel(url_backlog, sheet_name=None, header=4)
        
        dfs = []
        for sheet_name, df in xls.items():
            if 'Nombre del cliente' in df.columns:
                dfs.append(df)
        
        df_operativo = pd.concat(dfs, ignore_index=True)
        
        # B. Extraer Costos de Recursos
        url_recursos = "https://docs.google.com/spreadsheets/d/1ldntONNpWFgXPcF8VINDKzNAhG_vGMdzGEOESM3aLNU/export?format=csv&gid=1006395596"
        df_costos = pd.read_csv(url_recursos, header=0)
        
        # C. Limpieza inicial
        df_operativo['Persona a cargo'] = df_operativo['Persona a cargo'].astype(str).str.strip()
        df_costos['COLABORADOR'] = df_costos['COLABORADOR'].astype(str).str.strip()
        df_costos.columns = df_costos.columns.str.strip()
        
        # 🟢 TRUCO BI: DICCIONARIO DE HOMOLOGACIÓN DE NOMBRES 🟢
        mapeo_nombres = {
            'Sergio Velandia': 'SERGIO ANDRES VELANDIA MURCIA',
            'Alejandra Buriticá': 'ALEJANDRA BURITICA',
            'Alejandra Cardenas': 'MARIA ALEJANDRA CARDENAS',
            'Jimmy Peña': 'JIMMY PEÑA',
            'Sebastian Saenz': 'SEBASTIAN SAENZ'
        }
        
        # Traducimos el nombre del backlog al oficial de HR
        df_operativo['Persona HR'] = df_operativo['Persona a cargo'].map(mapeo_nombres).fillna(df_operativo['Persona a cargo'].str.upper())
        
        # Preparamos los costos
        costos_limpios = df_costos[['COLABORADOR', 'Costo Hora Real (2026)']].copy()
        
        # Súper limpieza de la moneda (asegura que quite '$', comas y espacios ocultos)
        costos_limpios['Costo Hora Real (2026)'] = costos_limpios['Costo Hora Real (2026)'].astype(str).replace(r'[\$,\s]', '', regex=True)
        costos_limpios['Costo Hora Real (2026)'] = pd.to_numeric(costos_limpios['Costo Hora Real (2026)'], errors='coerce').fillna(0)
        
        # Cruzamos las bases usando el nombre traducido
        df_final = pd.merge(df_operativo, costos_limpios, left_on='Persona HR', right_on='COLABORADOR', how='left')
        
        df_final['Tiempo real'] = pd.to_numeric(df_final['Tiempo real'], errors='coerce').fillna(0)
        df_final['Tiempo estimado'] = pd.to_numeric(df_final['Tiempo estimado'], errors='coerce').fillna(0)
        
        # D. Cálculos financieros
        df_final['Costo Operativo Real ($)'] = df_final['Tiempo real'] * df_final['Costo Hora Real (2026)']
        df_final['Costo Operativo Estimado ($)'] = df_final['Tiempo estimado'] * df_final['Costo Hora Real (2026)']
        
        df_final = df_final.dropna(subset=['Nombre del cliente'])
        
        return df_final
    
    except Exception as e:
        st.error(f"Error al procesar los datos: {e}")
        return pd.DataFrame()

# 3. Interfaz Visual de Comprobación
if st.button("🔄 Actualizar Datos desde Google Sheets"):
    st.cache_data.clear()

with st.spinner("Descargando hojas, cruzando salarios y calculando costos..."):
    df = load_data()

if not df.empty:
    st.success("✅ ¡Bases de datos homologadas y unidas en la sección Operativa!")
    
    st.subheader("📊 Datos Crudos Consolidados")
    col1, col2, col3 = st.columns(3)
    
    total_horas = df['Tiempo real'].sum()
    costo_total = df['Costo Operativo Real ($)'].sum()
    total_tareas = len(df)
    
    col1.metric("Total Horas Invertidas", f"{total_horas:,.2f} hrs")
    col2.metric("Costo Operativo Total", f"${costo_total:,.2f}")
    col3.metric("Total de Tareas Registradas", f"{total_tareas:,}")
    
    with st.expander("👀 Ver tabla (Expande para confirmar Costos)"):
        st.dataframe(df[['Nombre del cliente', 'Tipo de tarea', 'Persona a cargo', 'Persona HR', 'Tiempo real', 'Costo Hora Real (2026)', 'Costo Operativo Real ($)']].head(20))
        
else:
    st.warning("No se encontraron datos.")
