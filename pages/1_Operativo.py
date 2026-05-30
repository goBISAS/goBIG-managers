import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la página
st.set_page_config(page_title="Operativo", page_icon="⚙️", layout="wide")

st.title("⚙️ Dashboard Operativo y de Costos")
st.markdown("Visualización en tiempo real del Backlog cruzado con Costos de Nómina.")
st.markdown("---")

# 2. Motor de extracción y procesamiento de datos
@st.cache_data(ttl=600)
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
        
        # B. Extraer Costos de Recursos (Nómina)
        url_recursos = "https://docs.google.com/spreadsheets/d/1ldntONNpWFgXPcF8VINDKzNAhG_vGMdzGEOESM3aLNU/export?format=csv&gid=1006395596"
        df_costos = pd.read_csv(url_recursos, header=0)
        
        # C. Limpieza inicial de texto y columnas
        df_operativo['Persona a cargo'] = df_operativo['Persona a cargo'].astype(str).str.strip()
        df_costos['COLABORADOR'] = df_costos['COLABORADOR'].astype(str).str.strip()
        df_costos.columns = df_costos.columns.str.strip()
        
        # Diccionario de homologación de nombres de goBIG
        mapeo_nombres = {
            'Sergio Velandia': 'SERGIO ANDRES VELANDIA MURCIA',
            'Alejandra Buriticá': 'ALEJANDRA BURITICA',
            'Alejandra Cardenas': 'MARIA ALEJANDRA CARDENAS',
            'Jimmy Peña': 'JIMMY PEÑA',
            'Sebastian Saenz': 'SEBASTIAN SAENZ'
        }
        
        df_operativo['Persona HR'] = df_operativo['Persona a cargo'].map(mapeo_nombres).fillna(df_operativo['Persona a cargo'].str.upper())
        
        # Selección de columnas de nómina (Costo por hora y Costo Fijo Mensual de la Columna R/Costo total empresa)
        # Nota: Si prefieres la W, Python busca la columna por su nombre exacto. Usaremos 'Costo total empresa' que es la R.
        nombre_columna_total = 'Costo total empresa' if 'Costo total empresa' in df_costos.columns else df_costos.columns[17] # Respaldo por posición R
        
        costos_limpios = df_costos[['COLABORADOR', 'Costo Hora Real (2026)', nombre_columna_total]].copy()
        
        # Limpieza profunda de signos de moneda
        costos_limpios['Costo Hora Real (2026)'] = costos_limpios['Costo Hora Real (2026)'].astype(str).replace(r'[\$,\s]', '', regex=True)
        costos_limpios['Costo Hora Real (2026)'] = pd.to_numeric(costos_limpios['Costo Hora Real (2026)'], errors='coerce').fillna(0)
        
        costos_limpios[nombre_columna_total] = costos_limpios[nombre_columna_total].astype(str).replace(r'[\$,\s]', '', regex=True)
        costos_limpios['Costo Mensual Fijo'] = pd.to_numeric(costos_limpios[nombre_columna_total], errors='coerce').fillna(0)
        
        # Cruzamos las bases
        df_final = pd.merge(df_operativo, costos_limpios[['COLABORADOR', 'Costo Hora Real (2026)', 'Costo Mensual Fijo']], left_on='Persona HR', right_on='COLABORADOR', how='left')
        
        df_final['Tiempo real'] = pd.to_numeric(df_final['Tiempo real'], errors='coerce').fillna(0)
        df_final['Tiempo estimado'] = pd.to_numeric(df_final['Tiempo estimado'], errors='coerce').fillna(0)
        
        # D. Cálculos financieros avanzados
        # Valor operativo invertido (Horas de esfuerzo x Tarifa teórica por hora)
        df_final['Valor Operativo Invertido ($)'] = df_final['Tiempo real'] * df_final['Costo Hora Real (2026)']
        
        # Costo de Nómina Real Proporcional (Cuánto cuesta realmente ese tiempo según su salario fijo mensual considerando base de 170 horas al mes)
        df_final['Costo de Nómina Real ($)'] = (df_final['Tiempo real'] / 170) * df_final['Costo Mensual Fijo']
        
        df_final = df_final.dropna(subset=['Nombre del cliente'])
        
        return df_final
    
    except Exception as e:
        st.error(f"Error al procesar los datos: {e}")
        return pd.DataFrame()

# 3. Interfaz Visual 
if st.button("🔄 Actualizar Datos"):
    st.cache_data.clear()

with st.spinner("Descargando base de datos, cruzando salarios fijos y preparando gráficos..."):
    df = load_data()

if not df.empty:
    # 4. SECCIÓN DE FILTROS
    st.subheader("🔍 Consola de Filtros")
    col_f1, col_f2 = st.columns(2)
    
    lista_clientes = ["Todos"] + sorted(list(df['Nombre del cliente'].dropna().unique()))
    cliente_sel = col_f1.selectbox("Filtrar por Cliente:", lista_clientes)
    
    lista_personas = ["Todas"] + sorted(list(df['Persona HR'].dropna().unique()))
    persona_sel = col_f2.selectbox("Filtrar por Colaborador:", lista_personas)
    
    df_filtrado = df.copy()
    if cliente_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Nombre del cliente'] == cliente_sel]
    if persona_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado['Persona HR'] == persona_sel]
        
    st.markdown("---")
    
    # 5. TARJETAS DE RESUMEN (REDISEÑADAS CON TU PROPUESTA)
    st.subheader("📊 Métricas de Rendimiento y Comparativa de Costos")
    col1, col2, col3, col4 = st.columns(4)
    
    total_horas = df_filtrado['Tiempo real'].sum()
    valor_invertido = df_filtrado['Valor Operativo Invertido ($)'].sum()
    nomina_real = df_filtrado['Costo de Nómina Real ($)'].sum()
    total_tareas = len(df_filtrado)
    
    col1.metric("Total Horas Invertidas", f"{total_horas:,.2f} hrs")
    col2.metric("Valor Operativo Invertido (Esfuerzo)", f"${valor_invertido:,.2f}")
    col3.metric("Costo de Nómina Real (Fijo)", f"${nomina_real:,.2f}")
    col4.metric("Total de Tareas", f"{total_tareas:,}")
    
    # Alerta gerencial intuitiva
    desviacion = valor_invertido - nomina_real
    if desviacion > 0:
        st.warning(f"⚠️ **Alerta de Capacidad:** El valor del esfuerzo invertido supera en **${desviacion:,.2f}** al costo de nómina real fija contratada (Over-servicing o sobrecarga de tareas).")
    else:
        st.success(f"💡 **Eficiencia Operativa:** Contamos con una holgura de capacidad equivalente a **${abs(desviacion):,.2f}** respecto a la nómina fija.")

    st.markdown("---")
    
    # 6. SECCIÓN DE GRÁFICOS
    st.subheader("📈 Análisis Visual Dinámico")
    g_col1, g_col2 = st.columns(2)
    
    with g_col1:
        st.write("🧱 **Proporción del Valor Invertido por Cliente (Treemap)**")
        df_tree = df_filtrado.groupby('Nombre del cliente').agg({'Valor Operativo Invertido ($)': 'sum'}).reset_index()
        total_global_money = df_tree['Valor Operativo Invertido ($)'].sum()
        df_tree['Porcentaje'] = (df_tree['Valor Operativo Invertido ($)'] / total_global_money * 100).round(1) if total_global_money > 0 else 0
        df_tree['Etiqueta'] = df_tree['Nombre del cliente'] + "<br>$" + df_tree['Valor Operativo Invertido ($)'].map('{:,.0f}'.format) + "<br>" + df_tree['Porcentaje'].astype(str) + "%"
        
        fig_tree = px.treemap(df_tree, path=['Etiqueta'], values='Valor Operativo Invertido ($)', color='Valor Operativo Invertido ($)', color_continuous_scale='Blues')
        fig_tree.update_traces(textinfo="label")
        fig_tree.update_layout(margin=dict(t=10, l=10, r=10, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig_tree, use_container_width=True)
        
    with g_col2:
        st.write("📊 **Esfuerzo en Tiempo Real por Colaborador**")
        df_bar = df_filtrado.groupby('Persona HR').agg({'Tiempo real': 'sum'}).reset_index().sort_values(by='Tiempo real', ascending=True)
        
        fig_bar = px.bar(df_bar, x='Tiempo real', y='Persona HR', orientation='h', text=df_bar['Tiempo real'].map('{:,.1f} hrs'.format), color='Tiempo real', color_continuous_scale='Purples')
        fig_bar.update_traces(textposition='inside')
        fig_bar.update_layout(margin=dict(t=10, l=10, r=10, b=10), coloraxis_showscale=False, xaxis_title="Horas Reales", yaxis_title="")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    
    # 7. TABLA DETALLADA
    with st.expander("👀 Ver tabla detallada (Datos Filtrados)"):
        st.dataframe(df_filtrado[['Nombre del cliente', 'Tipo de tarea', 'Persona HR', 'Tiempo real', 'Valor Operativo Invertido ($)', 'Costo de Nómina Real ($)']].head(50))
        
else:
    st.warning("No se encontraron datos.")
