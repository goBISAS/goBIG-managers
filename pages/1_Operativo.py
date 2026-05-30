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
                if 'Fecha de entrega' in df.columns:
                    df['Fecha de entrega'] = pd.to_datetime(df['Fecha de entrega'], errors='coerce')
                dfs.append(df)
        
        df_operativo = pd.concat(dfs, ignore_index=True)
        df_operativo['Mes-Año'] = df_operativo['Fecha de entrega'].dt.strftime('%Y-%m')
        df_operativo['Fecha_Texto'] = df_operativo['Fecha de entrega'].dt.strftime('%Y-%m-%d')
        
        # B. Extraer Costos de Recursos (Nómina Completa)
        url_recursos = "https://docs.google.com/spreadsheets/d/1ldntONNpWFgXPcF8VINDKzNAhG_vGMdzGEOESM3aLNU/export?format=csv&gid=1006395596"
        df_costos = pd.read_csv(url_recursos, header=0)
        
        # C. Limpieza de texto y columnas
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
        
        # Identificar Columna R (Costo total empresa) y Columna D (Fecha inicio del contrato)
        nombre_columna_total = 'Costo total empresa' if 'Costo total empresa' in df_costos.columns else df_costos.columns[17]
        
        df_costos[nombre_columna_total] = df_costos[nombre_columna_total].astype(str).replace(r'[\$,\s]', '', regex=True)
        df_costos['Costo Mensual Fijo'] = pd.to_numeric(df_costos[nombre_columna_total], errors='coerce').fillna(0)
        
        df_costos['Costo Hora Real (2026)'] = df_costos['Costo Hora Real (2026)'].astype(str).replace(r'[\$,\s]', '', regex=True)
        df_costos['Costo Hora Real (2026)'] = pd.to_numeric(df_costos['Costo Hora Real (2026)'], errors='coerce').fillna(0)
        
        # Convertimos la Fecha de inicio de contrato a un formato de tiempo real para Python
        df_costos['Fecha inicio del contrato'] = pd.to_datetime(df_costos['Fecha inicio del contrato'], errors='coerce')
        
        # Crear base limpia para el cruce por tarea incluyendo la fecha de contratación
        costos_limpios = df_costos[['COLABORADOR', 'Costo Hora Real (2026)', 'Costo Mensual Fijo', 'Fecha inicio del contrato']].copy()
        
        df_final = pd.merge(df_operativo, costos_limpios, left_on='Persona HR', right_on='COLABORADOR', how='left')
        df_final['Tiempo real'] = pd.to_numeric(df_final['Tiempo real'], errors='coerce').fillna(0)
        df_final['Tiempo estimado'] = pd.to_numeric(df_final['Tiempo estimado'], errors='coerce').fillna(0)
        
        # Cálculos de valor por esfuerzo individual
        df_final['Valor Operativo Invertido ($)'] = df_final['Tiempo real'] * df_final['Costo Hora Real (2026)']
        df_final['Costo de Nómina Real ($)'] = (df_final['Tiempo real'] / 170) * df_final['Costo Mensual Fijo']
        
        df_final = df_final.dropna(subset=['Nombre del cliente'])
        
        return df_final, costos_limpios
    
    except Exception as e:
        st.error(f"Error al procesar los datos: {e}")
        return pd.DataFrame(), pd.DataFrame()

# 3. Interfaz Visual 
if st.button("🔄 Actualizar Datos"):
    st.cache_data.clear()

with st.spinner("Sincronizando registros y aplicando filtros de contratación cronológica..."):
    df, df_costos_global = load_data()

if not df.empty:
    # 4. SECCIÓN DE FILTROS
    st.subheader("🔍 Consola de Filtros")
    col_f1, col_f2, col_f3 = st.columns(3)
    
    lista_clientes = ["Todos"] + sorted(list(df['Nombre del cliente'].dropna().unique()))
    cliente_sel = col_f1.selectbox("Filtrar por Cliente:", lista_clientes)
    
    lista_personas = ["Todas"] + sorted(list(df['Persona HR'].dropna().unique()))
    persona_sel = col_f2.selectbox("Filtrar por Colaborador:", lista_personas)
    
    lista_meses = ["Todos"] + sorted(list(df['Mes-Año'].dropna().unique()), reverse=True)
    mes_sel = col_f3.selectbox("Filtrar por Mes Calendario:", lista_meses)
    
    df_filtrado = df.copy()
    if cliente_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Nombre del cliente'] == cliente_sel]
    if persona_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado['Persona HR'] == persona_sel]
    if mes_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Mes-Año'] == mes_sel]
        
    st.markdown("---")
    
    # 5. 🧠 NUEVA LÓGICA ULTRA-INTELIGENTE DE FECHA DE CONTRATACIÓN
    # Evaluamos qué empleados ya habían iniciado contrato según el mes seleccionado
    if mes_sel != "Todos":
        # Creamos el límite: Último día del mes seleccionado
        fecha_limite_mes = pd.to_datetime(mes_sel + "-01") + pd.offsets.MonthEnd(0)
        df_costos_activos = df_costos_global[df_costos_global['Fecha inicio del contrato'] <= fecha_limite_mes]
    else:
        # Si ve todo el histórico, solo quitamos contratos que no tengan fecha válida
        df_costos_activos = df_costos_global.dropna(subset=['Fecha inicio del contrato'])

    # 6. CÁLCULO DEL KPI DE NÓMINA FIJA
    if cliente_sel == "Todos" and persona_sel == "Todas":
        # Sumamos la nómina fija SOLO de los que ya estaban contratados en este periodo
        nomina_base_mensual = df_costos_activos['Costo Mensual Fijo'].sum()
        if mes_sel == "Todos":
            num_meses = max(1, df_filtrado['Mes-Año'].nunique())
            nomina_real = nomina_base_mensual * num_meses
        else:
            nomina_real = nomina_base_mensual
    elif persona_sel != "Todas":
        # Si selecciona a alguien específico, verifica si ya estaba contratado
        colab_df = df_costos_activos[df_costos_activos['COLABORADOR'] == persona_sel]
        nomina_real = colab_df['Costo Mensual Fijo'].sum() if not colab_df.empty else 0
    else:
        # Filtro por cliente: Proporción de horas consumidas
        nomina_real = df_filtrado['Costo de Nómina Real ($)'].sum()

    # 7. TARJETAS DE RESUMEN FINALES
    st.subheader("📊 Métricas de Rendimiento y Comparativa de Costos")
    col1, col2, col3, col4 = st.columns(4)
    
    total_horas = df_filtrado['Tiempo real'].sum()
    valor_invertido = df_filtrado['Valor Operativo Invertido ($)'].sum()
    total_tareas = len(df_filtrado)
    
    col1.metric("Total Horas Invertidas", f"{total_horas:,.2f} hrs")
    col2.metric("Valor Operativo Invertido (Esfuerzo)", f"${valor_invertido:,.2f}")
    col3.metric("Costo de Nómina Real (Fijo)", f"${nomina_real:,.2f}")
    col4.metric("Total de Tareas", f"{total_tareas:,}")
    
    # Mensaje adaptado
    desviacion = valor_invertido - nomina_real
    if cliente_sel == "Todos" and persona_sel == "Todas":
        if desviacion > 0:
            st.warning(f"⚠️ **Alerta Financiera:** El valor del esfuerzo operativo invertido supera la nómina fija activa por **${desviacion:,.2f}**.")
        else:
            st.success(f"💡 **Rentabilidad de Nómina:** goBIG operó con una holgura de capacidad sin costo extra de **${abs(desviacion):,.2f}** frente al costo de los contratos activos de este periodo.")
    else:
        st.info(f"📊 Diferencia entre Esfuerzo Comercial Proyectado y Costo Fijo Activo: **${desviacion:,.2f}**")

    st.markdown("---")
    
    # 8. SECCIÓN DE GRÁFICOS
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
    
    # 9. EVOLUCIÓN CRONOLÓGICA
    st.subheader("📅 Evolución Temporal del Esfuerzo Operativo")
    df_line = df_filtrado.groupby('Fecha_Texto').agg({'Tiempo real': 'sum'}).reset_index().sort_values(by='Fecha_Texto')
    
    if not df_line.empty:
        fig_line = px.line(df_line, x='Fecha_Texto', y='Tiempo real', labels={'Fecha_Texto': 'Fecha del Calendario', 'Tiempo real': 'Horas Invertidas'}, markers=True)
        fig_line.update_traces(text=df_line['Tiempo real'].map('{:,.1f}h'.format), textposition="top center")
        fig_line.update_layout(margin=dict(t=20, l=10, r=10, b=20), xaxis_tickangle=-45)
        st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("---")
    
    # 10. TABLA DETALLADA
    with st.expander("👀 Ver tabla detallada (Datos Filtrados)"):
        st.dataframe(df_filtrado[['Nombre del cliente', 'Tipo de tarea', 'Persona HR', 'Tiempo real', 'Valor Operativo Invertido ($)', 'Mes-Año']].head(50))
        
else:
    st.warning("No se encontraron datos.")
