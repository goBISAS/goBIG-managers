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
        
        # Diccionario de homologación
        mapeo_nombres = {
            'Sergio Velandia': 'SERGIO ANDRES VELANDIA MURCIA',
            'Alejandra Buriticá': 'ALEJANDRA BURITICA',
            'Alejandra Cardenas': 'MARIA ALEJANDRA CARDENAS',
            'Jimmy Peña': 'JIMMY PEÑA',
            'Sebastian Saenz': 'SEBASTIAN SAENZ'
        }
        
        df_operativo['Persona HR'] = df_operativo['Persona a cargo'].map(mapeo_nombres).fillna(df_operativo['Persona a cargo'].str.upper())
        
        # Preparamos los costos
        costos_limpios = df_costos[['COLABORADOR', 'Costo Hora Real (2026)']].copy()
        costos_limpios['Costo Hora Real (2026)'] = costos_limpios['Costo Hora Real (2026)'].astype(str).replace(r'[\$,\s]', '', regex=True)
        costos_limpios['Costo Hora Real (2026)'] = pd.to_numeric(costos_limpios['Costo Hora Real (2026)'], errors='coerce').fillna(0)
        
        # Cruzamos las bases
        df_final = pd.merge(df_operativo, costos_limpios, left_on='Persona HR', right_on='COLABORADOR', how='left')
        
        df_final['Tiempo real'] = pd.to_numeric(df_final['Tiempo real'], errors='coerce').fillna(0)
        df_final['Tiempo estimado'] = pd.to_numeric(df_final['Tiempo estimado'], errors='coerce').fillna(0)
        
        # D. Cálculos financieros (NUEVO NOMBRE ESTRATÉGICO)
        df_final['Valor Operativo Invertido ($)'] = df_final['Tiempo real'] * df_final['Costo Hora Real (2026)']
        df_final['Valor Operativo Estimado ($)'] = df_final['Tiempo estimado'] * df_final['Costo Hora Real (2026)']
        
        df_final = df_final.dropna(subset=['Nombre del cliente'])
        
        return df_final
    
    except Exception as e:
        st.error(f"Error al procesar los datos: {e}")
        return pd.DataFrame()

# 3. Interfaz Visual 
if st.button("🔄 Actualizar Datos"):
    st.cache_data.clear()

with st.spinner("Descargando base de datos y preparando filtros..."):
    df = load_data()

if not df.empty:
    st.success("✅ Datos listos para analizar.")
    
    # 4. 🎛️ SECCIÓN DE FILTROS (NUEVO)
    st.subheader("🔍 Consola de Filtros")
    
    # Organizamos los filtros en dos columnas para que se vea bien en celular
    col_f1, col_f2 = st.columns(2)
    
    # Extraemos la lista única de clientes y personas para los menús desplegables
    lista_clientes = ["Todos"] + sorted(list(df['Nombre del cliente'].dropna().unique()))
    cliente_sel = col_f1.selectbox("Filtrar por Cliente:", lista_clientes)
    
    lista_personas = ["Todas"] + sorted(list(df['Persona HR'].dropna().unique()))
    persona_sel = col_f2.selectbox("Filtrar por Colaborador:", lista_personas)
    
    # Aplicamos la lógica de filtrado según lo que escoja el directivo
    df_filtrado = df.copy()
    
    if cliente_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Nombre del cliente'] == cliente_sel]
        
    if persona_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado['Persona HR'] == persona_sel]
        
    st.markdown("---")
    
    # 5. 📊 TARJETAS DE RESUMEN (REACTIVAS)
    st.subheader("📊 Métricas de Rendimiento")
    col1, col2, col3 = st.columns(3)
    
    # Ahora las sumas se hacen sobre "df_filtrado", por lo que cambiarán con los filtros
    total_horas = df_filtrado['Tiempo real'].sum()
    valor_invertido = df_filtrado['Valor Operativo Invertido ($)'].sum()
    total_tareas = len(df_filtrado)
    
    col1.metric("Total Horas Invertidas", f"{total_horas:,.2f} hrs")
    col2.metric("Valor Operativo Invertido", f"${valor_invertido:,.2f}")
    col3.metric("Total de Tareas", f"{total_tareas:,}")
    
    # Vista previa de la tabla (Aumentamos a 50 filas e incluimos el nuevo nombre)
    with st.expander("👀 Ver tabla detallada (Expande para confirmar los datos filtrados)"):
        st.dataframe(df_filtrado[['Nombre del cliente', 'Tipo de tarea', 'Persona HR', 'Tiempo real', 'Valor Operativo Invertido ($)']].head(50))
        
else:
    st.warning("No se encontraron datos.")
