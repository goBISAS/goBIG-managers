import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la página
st.set_page_config(page_title="Operativo v1.0", page_icon="⚙️", layout="wide")

st.title("⚙️ Dashboard Operativo y de Costos v1.0")
st.markdown("Gestión de rentabilidad, esfuerzo y bienestar del talento en tiempo real.")
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
                    df['Fecha de entrega'] = pd.to_datetime(df['Fecha de entrega'], dayfirst=True, errors='coerce')
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
        
        # Diccionario de homologación
        mapeo_nombres = {'Sergio Velandia': 'SERGIO ANDRES VELANDIA MURCIA', 'Alejandra Buriticá': 'ALEJANDRA BURITICA', 'Alejandra Cardenas': 'MARIA ALEJANDRA CARDENAS', 'Jimmy Peña': 'JIMMY PEÑA', 'Sebastian Saenz': 'SEBASTIAN SAENZ'}
        df_operativo['Persona HR'] = df_operativo['Persona a cargo'].map(mapeo_nombres).fillna(df_operativo['Persona a cargo'].str.upper())
        
        # Identificar Columna R y limpiar
        nombre_columna_total = 'Costo total empresa' if 'Costo total empresa' in df_costos.columns else df_costos.columns[17]
        df_costos[nombre_columna_total] = df_costos[nombre_columna_total].astype(str).replace(r'[\$,\s]', '', regex=True)
        df_costos['Costo Mensual Fijo'] = pd.to_numeric(df_costos[nombre_columna_total], errors='coerce').fillna(0)
        df_costos['Costo Hora Real (2026)'] = df_costos['Costo Hora Real (2026)'].astype(str).replace(r'[\$,\s]', '', regex=True)
        df_costos['Costo Hora Real (2026)'] = pd.to_numeric(df_costos['Costo Hora Real (2026)'], errors='coerce').fillna(0)
        df_costos['Fecha inicio del contrato'] = pd.to_datetime(df_costos['Fecha inicio del contrato'], dayfirst=True, errors='coerce')
        
        # Cruzar bases
        costos_limpios = df_costos[['COLABORADOR', 'Costo Hora Real (2026)', 'Costo Mensual Fijo', 'Fecha inicio del contrato']].copy()
        df_final = pd.merge(df_operativo, costos_limpios, left_on='Persona HR', right_on='COLABORADOR', how='left')
        df_final['Tiempo real'] = pd.to_numeric(df_final['Tiempo real'], errors='coerce').fillna(0)
        df_final['Tiempo estimado'] = pd.to_numeric(df_final['Tiempo estimado'], errors='coerce').fillna(0)
        
        df_final['Valor Operativo Invertido ($)'] = df_final['Tiempo real'] * df_final['Costo Hora Real (2026)']
        df_final['Costo de Nómina Real ($)'] = (df_final['Tiempo real'] / 170) * df_final['Costo Mensual Fijo']
        df_final = df_final.dropna(subset=['Nombre del cliente'])
        
        return df_final, costos_limpios
    
    except Exception as e:
        st.error(f"Error al procesar los datos: {e}")
        return pd.DataFrame(), pd.DataFrame()

# 3. Interfaz Visual 
if st.button("🔄 Sincronizar Todo"):
    st.cache_data.clear()

df, df_costos_global = load_data()

if not df.empty:
    # 4. FILTROS
    st.subheader("🔍 Consola de Filtros")
    col_f1, col_f2, col_f3 = st.columns(3)
    cliente_sel = col_f1.selectbox("Cliente:", ["Todos"] + sorted(list(df['Nombre del cliente'].unique())))
    persona_sel = col_f2.selectbox("Colaborador:", ["Todas"] + sorted(list(df['Persona HR'].unique())))
    mes_sel = col_f3.selectbox("Mes:", ["Todos"] + sorted(list(df['Mes-Año'].unique()), reverse=True))
    
    df_filtrado = df.copy()
    if cliente_sel != "Todos": df_filtrado = df_filtrado[df_filtrado['Nombre del cliente'] == cliente_sel]
    if persona_sel != "Todas": df_filtrado = df_filtrado[df_filtrado['Persona HR'] == persona_sel]
    if mes_sel != "Todos": df_filtrado = df_filtrado[df_filtrado['Mes-Año'] == mes_sel]
        
    st.markdown("---")
    
    # 5. CÁLCULO NÓMINA FIJA
    if mes_sel != "Todos":
        f_limite = pd.to_datetime(mes_sel + "-01") + pd.offsets.MonthEnd(0)
        df_c_act = df_costos_global[df_costos_global['Fecha inicio del contrato'] <= f_limite]
    else:
        df_c_act = df_costos_global.dropna(subset=['Fecha inicio del contrato'])

    if cliente_sel == "Todos" and persona_sel == "Todas":
        nomina_real = df_c_act['Costo Mensual Fijo'].sum() * (max(1, df_filtrado['Mes-Año'].nunique()) if mes_sel == "Todos" else 1)
    elif persona_sel != "Todas":
        nomina_real = df_c_act[df_c_act['COLABORADOR'] == persona_sel]['Costo Mensual Fijo'].sum()
    else:
        nomina_real = df_filtrado['Costo de Nómina Real ($)'].sum()

    # 6. MÉTRICAS
    col1, col2, col3, col4 = st.columns(4)
    total_horas = df_filtrado['Tiempo real'].sum()
    valor_inv = df_filtrado['Valor Operativo Invertido ($)'].sum()
    col1.metric("Horas Invertidas", f"{total_horas:,.2f} h")
    col2.metric("Valor Esfuerzo", f"${valor_inv:,.2f}")
    col3.metric("Costo Nómina Fija", f"${nomina_real:,.2f}")
    col4.metric("Tareas", f"{len(df_filtrado):,}")

    # 7. SEMÁFOROS
    st.subheader("🚨 Diagnóstico de Negocio")
    h_est = df_filtrado['Tiempo estimado'].sum()
    if h_est > 0:
        desv = ((total_horas - h_est) / h_est) * 100
        if desv > 10: st.error(f"🔴 **Over-servicing:** +{desv:.1f}% sobre lo estimado.")
        else: st.success(f"🟢 **Rentabilidad:** Ejecución {abs(desv):.1f}% bajo presupuesto.")
    
    df_burn = df_filtrado.groupby('Persona HR').agg({'Tiempo real': 'sum', 'Fecha_Texto': 'nunique'})
    burn_p = [f"{n} ({h/d:.1f}h/d)" for n, (h, d) in df_burn.iterrows() if d > 0 and h/d > 8.5]
    if burn_p: st.error(f"🔴 **Riesgo Burnout:** {', '.join(burn_p)}")

    st.markdown("---")
    
    # 8. GRÁFICOS (ACTUALIZADO: 3 GRÁFICOS)
    st.subheader("📈 Análisis de Valor y Taxonomía")
    g1, g2 = st.columns(2)
    
    with g1:
        st.write("🧱 **Distribución por Cliente**")
        df_t1 = df_filtrado.groupby('Nombre del cliente').agg({'Valor Operativo Invertido ($)': 'sum'}).reset_index()
        fig1 = px.treemap(df_t1, path=['Nombre del cliente'], values='Valor Operativo Invertido ($)', color='Valor Operativo Invertido ($)', color_continuous_scale='Blues')
        fig1.update_layout(margin=dict(t=10, l=10, r=10, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig1, use_container_width=True)

    with g2:
        st.write("📊 **Esfuerzo por Colaborador**")
        df_b = df_filtrado.groupby('Persona HR').agg({'Tiempo real': 'sum'}).reset_index().sort_values(by='Tiempo real')
        fig2 = px.bar(df_b, x='Tiempo real', y='Persona HR', orientation='h', text=df_b['Tiempo real'].map('{:,.1f}h'.format), color='Tiempo real', color_continuous_scale='Purples')
        fig2.update_layout(margin=dict(t=10, l=10, r=10, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.write("🌿 **Taxonomía de Tareas (Cruce Cliente vs. Actividad)**")
    df_t2 = df_filtrado.groupby(['Nombre del cliente', 'Tipo de tarea']).agg({'Valor Operativo Invertido ($)': 'sum'}).reset_index()
    fig3 = px.treemap(df_t2, path=['Nombre del cliente', 'Tipo de tarea'], values='Valor Operativo Invertido ($)', color='Tipo de tarea', color_discrete_sequence=px.colors.qualitative.Pastel)
    fig3.update_layout(margin=dict(t=10, l=10, r=10, b=10))
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    
    # 9. LÍNEA DE TIEMPO
    st.subheader("📅 Tendencia Diaria")
    df_l = df_filtrado.groupby('Fecha_Texto').agg({'Tiempo real': 'sum'}).reset_index()
    fig4 = px.line(df_l, x='Fecha_Texto', y='Tiempo real', markers=True)
    fig4.update_traces(text=df_l['Tiempo real'].map('{:,.1f}h'.format), textposition="top center")
    st.plotly_chart(fig4, use_container_width=True)
        
else:
    st.warning("No se encontraron datos.")
