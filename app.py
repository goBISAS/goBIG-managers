import streamlit as st
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Operativo", page_icon="⚙️", layout="wide")

st.title("⚙️ Dashboard Operativo y de Costos")
st.markdown("Visualización en tiempo real del Backlog cruzado con Costos de Nómina.")
st.markdown("---")

# 2. Motor de extracción y procesamiento de datos
@st.cache_data(ttl=600) # Guarda los datos en memoria por 10 min para que cargue rápido
def load_data():
    try:
        # A. Extraer Backlog (todas las hojas unidas)
        url_backlog = "https://docs.google.com/spreadsheets/d/1Vl5rhQDi6YooJgjYAF76oOO0aN8rbPtu07giky36wSo/export?format=xlsx"
        # La fila 5 tiene los encabezados reales (índice 4 en Python)
        xls = pd.read_excel(url_backlog, sheet_name=None, header=4)
        
        dfs = []
        for sheet_name, df in xls.items():
            # Filtramos para asegurar que es una hoja de tareas (debe tener la columna de Cliente)
            if 'Nombre del cliente' in df.columns:
                dfs.append(df)
        
        df_operativo = pd.concat(dfs, ignore_index=True)
        
        # B. Extraer Costos de Recursos (Solo la hoja necesaria vía CSV para mayor velocidad)
        url_recursos = "https://docs.google.com/spreadsheets/d/1ldntONNpWFgXPcF8VINDKzNAhG_vGMdzGEOESM3aLNU/export?format=csv&gid=1006395596"
        # La fila 2 tiene los encabezados (índice 1 en Python)
        df_costos = pd.read_csv(url_recursos, header=1)
        
        # C. Limpieza y Cruce de Datos
        # Quitamos espacios en blanco accidentales en los nombres para que el cruce sea exacto
        df_operativo['Persona a cargo'] = df_operativo['Persona a cargo'].astype(str).str.strip()
        df_costos['COLABORADOR'] = df_costos['COLABORADOR'].astype(str).str.strip()
        df_costos.columns = df_costos.columns.str.strip()
        
        # Extraemos solo las dos columnas que nos importan de la nómina
        costos_limpios = df_costos[['COLABORADOR', 'Costo Hora Real (2026)']].copy()
        
        # Limpiamos el texto de moneda (quitamos '$' y comas) para convertirlo a número matemático
        costos_limpios['Costo Hora Real (2026)'] = costos_limpios['Costo Hora Real (2026)'].replace('[\$,]', '', regex=True).astype(float)
        
        # Hacemos el cruce (VLOOKUP / BuscarV en lenguaje Python)
        df_final = pd.merge(df_operativo, costos_limpios, left_on='Persona a cargo', right_on='COLABORADOR', how='left')
        
        # Convertimos las horas a números asegurando que no haya errores si alguien escribió un texto
        df_final['Tiempo real'] = pd.to_numeric(df_final['Tiempo real'], errors='coerce').fillna(0)
        df_final['Tiempo estimado'] = pd.to_numeric(df_final['Tiempo estimado'], errors='coerce').fillna(0)
        
        # D. ¡MAGIA! Cálculos financieros de la operación
        df_final['Costo Operativo Real ($)'] = df_final['Tiempo real'] * df_final['Costo Hora Real (2026)']
        df_final['Costo Operativo Estimado ($)'] = df_final['Tiempo estimado'] * df_final['Costo Hora Real (2026)']
        
        # Eliminamos filas en blanco (donde no hay cliente)
        df_final = df_final.dropna(subset=['Nombre del cliente'])
        
        return df_final
    
    except Exception as e:
        st.error(f"Error al procesar los datos: {e}")
        return pd.DataFrame()

# 3. Interfaz Visual de Comprobación
with st.spinner("Descargando hojas, cruzando salarios y calculando costos en tiempo real..."):
    df = load_data()

if not df.empty:
    st.success("✅ ¡Conexión exitosa! Las bases de datos se unieron correctamente.")
    
    # Tarjetas de Resumen (KPIs Base)
    st.subheader("📊 Datos Crudos Consolidados (Previo a Gráficos)")
    col1, col2, col3 = st.columns(3)
    
    total_horas = df['Tiempo real'].sum()
    costo_total = df['Costo Operativo Real ($)'].sum()
    total_tareas = len(df)
    
    col1.metric("Total Horas Invertidas", f"{total_horas:,.2f} hrs")
    col2.metric("Costo Operativo Total", f"${costo_total:,.0f}")
    col3.metric("Total de Tareas Registradas", total_tareas)
    
    # Vista previa de la base de datos (Ocultable para celular)
    with st.expander("👀 Ver tabla consolidada cruzada (Toca para expandir)"):
        st.dataframe(df[['Nombre del cliente', 'Tipo de tarea', 'Persona a cargo', 'Tiempo real', 'Costo Hora Real (2026)', 'Costo Operativo Real ($)']].head(20))
        
else:
    st.warning("No se encontraron datos. Por favor verifica los enlaces de Google Sheets.")
