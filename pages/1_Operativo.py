import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la página (El tema se adaptará automáticamente al modo oscuro del sistema/app)
st.set_page_config(page_title="goBIG Operativo v1.0", page_icon="📈", layout="wide")

# 2. Barra Lateral: Logo Oficial de goBIG e Identidad
with st.sidebar:
    st.image("goBIG_logo.jpg", width=200)
    st.markdown("---")
    st.caption("v1.0 - Dashboard de Inteligencia Operativa")
    st.info("💡 **Consejo:** Filtra por mes para ver la rentabilidad exacta frente a la nómina fija.")

# 3. Encabezado Principal
st.title("⚙️ Panel de Inteligencia Operativa y Costos")
st.markdown("Análisis estratégico del esfuerzo, rentabilidad y capacidad de goBIG en tiempo real.")
st.markdown("---")

# 4. Motor de extracción y procesamiento de datos
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
        
        # B. Extraer Costos de Recursos
        url_recursos = "https://docs.google.com/spreadsheets/d/1ldntONNpWFgXPcF8VINDKzNAhG_vGMdzGEOESM3aLNU/export?format=csv&gid=1006395596"
        df_costos = pd.read_csv(url_recursos, header=0)
        
        # C. Limpieza y Homologación
        df_operativo['Persona a cargo'] = df_operativo['Persona a cargo'].astype(str).str.strip()
        df_costos['COLABORADOR'] = df_costos['COLABORADOR'].astype(str).str.strip()
        df_costos.columns = df_costos.columns.str.strip()
        
        mapeo = {
            'Sergio Velandia': 'SERGIO ANDRES VELANDIA MURCIA',
            'Alejandra Buriticá': 'ALEJANDRA BURITICA',
            'Alejandra Cardenas': 'MARIA ALEJANDRA CARDENAS',
            'Jimmy Peña': 'JIMMY PEÑA',
            'Sebastian Saenz': 'SEBASTIAN SAENZ'
        }
        df_operativo['Persona HR'] = df_operativo['Persona a cargo'].map(mapeo).fillna(df_operativo['Persona a cargo'].str.upper())
        
        # Procesar Nómina
        col_r = 'Costo total empresa' if 'Costo total empresa' in df_costos.columns else df_costos.columns[17]
        df_costos['Costo Mensual Fijo'] = pd.to_numeric(df_costos[col_r].astype(str).replace(r'[\$,\s]', '', regex=True), errors='coerce').fillna(0)
        df_costos['Costo Hora'] = pd.to_numeric(df_costos['Costo Hora Real (2026)'].astype(str).replace(r'[\$,\s]', '', regex=True), errors='coerce').fillna(0)
        df_costos['Fecha inicio del contrato'] = pd.to_datetime(df_costos['Fecha inicio del contrato'], dayfirst=True, errors='coerce')
        
        costos_limpios = df_costos[['COLABORADOR', 'Costo Hora', 'Costo Mensual Fijo', 'Fecha inicio del contrato']].copy()
        df_final = pd.merge(df_operativo, costos_limpios, left_on='Persona HR', right_on='COLABORADOR', how='left')
        
        df_final['Tiempo real'] = pd.to_numeric(df_final['Tiempo real'], errors='coerce').fillna(0)
        df_final['Tiempo estimado'] = pd.to_numeric(df_final['Tiempo estimado'], errors='coerce').fillna(0)
        df_final['Valor Invertido ($)'] = df_final['Tiempo real'] * df_final['Costo Hora']
        df_final['Costo Nómina Prop ($)'] = (df_final['Tiempo real'] / 170) * df_final['Costo Mensual Fijo']
        
        return df_final.dropna(subset=['Nombre del cliente']), costos_limpios
    
    except Exception as e:
        st.error(f"Error técnico en el motor de datos: {e}")
        return pd.DataFrame(), pd.DataFrame()

# 5. Sincronización
if st.button("🔄 Sincronizar Datos Maestros"):
    st.cache_data.clear()

df, df_costos_global = load_data()

if not df.empty:
    # 6. FILTROS
    st.subheader("🔍 Consola de Mandos")
    c1, c2, c3 = st.columns(3)
    cliente_sel = c1.selectbox("Filtrar Cliente:", ["Todos"] + sorted(list(df['Nombre del cliente'].dropna().unique())))
    persona_sel = c2.selectbox("Filtrar Colaborador:", ["Todas"] + sorted(list(df['Persona HR'].dropna().unique())))
    mes_sel = c3.selectbox("Filtrar Mes Calendario:", ["Todos"] + sorted(list(df['Mes-Año'].dropna().unique()), reverse=True))
    
    df_f = df.copy()
    if cliente_sel != "Todos": df_f = df_f[df_f['Nombre del cliente'] == cliente_sel]
    if persona_sel != "Todas": df_f = df_f[df_f['Persona HR'] == persona_sel]
    if mes_sel != "Todos": df_f = df_f[df_f['Mes-Año'] == mes_sel]
        
    st.markdown("---")
    
    # 7. CÁLCULO INTELIGENTE DE NÓMINA FIJA ACTIVA
    if mes_sel != "Todos":
        f_l = pd.to_datetime(mes_sel + "-01") + pd.offsets.MonthEnd(0)
        df_activos = df_costos_global[df_costos_global['Fecha inicio del contrato'] <= f_l]
    else:
        df_activos = df_costos_global.dropna(subset=['Fecha inicio del contrato'])

    if cliente_sel == "Todos" and persona_sel == "Todas":
        nomina_real = df_activos['Costo Mensual Fijo'].sum() * (max(1, df_f['Mes-Año'].nunique()) if mes_sel == "Todos" else 1)
    elif persona_sel != "Todas":
        nomina_real = df_activos[df_activos['COLABORADOR'] == persona_sel]['Costo Mensual Fijo'].sum()
    else:
        nomina_real = df_f['Costo Nómina Prop ($)'].sum()

    # 8. KPIs PRINCIPALES
    k1, k2, k3, k4 = st.columns(4)
    v_inv = df_f['Valor Invertido ($)'].sum()
    k1.metric("Horas Invertidas", f"{df_f['Tiempo real'].sum():,.1f} h")
    k2.metric("Valor del Esfuerzo", f"${v_inv:,.2f}")
    k3.metric("Nómina Fija Activa", f"${nomina_real:,.2f}")
    k4.metric("Tareas Ejecutadas", f"{len(df_f):,}")

    # 9. SEMÁFOROS BI
    st.subheader("🚨 Diagnóstico Operativo")
    h_est = df_f['Tiempo estimado'].sum()
    if h_est > 0:
        desv = ((df_f['Tiempo real'].sum() - h_est) / h_est) * 100
        if desv > 10: st.error(f"🔴 **Over-servicing:** +{desv:.1f}% sobre lo presupuestado.")
        else: st.success(f"🟢 **Eficiencia Comercial:** Desviación de {abs(desv):.1f}% (Bajo control).")
    
    df_burn = df_f.groupby('Persona HR').agg({'Tiempo real': 'sum', 'Fecha_Texto': 'nunique'})
    burn = [f"{n} ({h/d:.1f}h/d)" for n, (h, d) in df_burn.iterrows() if d > 0 and h/d > 8.5]
    if burn: st.error(f"🔴 **Alerta Burnout:** {', '.join(burn)}")

    st.markdown("---")
    
    # 10. ANÁLISIS VISUAL
    st.subheader("📈 Visualización Estratégica de Datos")
    g1, g2 = st.columns(2)
    
    with g1:
        st.write("**¼ Concentración de Valor por Cliente**")
        df_t1 = df_f.groupby('Nombre del cliente').agg({'Valor Invertido ($)': 'sum'}).reset_index()
        total_m = df_t1['Valor Invertido ($)'].sum()
        df_t1['Etiqueta'] = df_t1['Nombre del cliente'] + "<br>$" + df_t1['Valor Invertido ($)'].map('{:,.0f}'.format) + "<br>" + (df_t1['Valor Invertido ($)']/total_m*100).round(1).astype(str) + "%"
        fig1 = px.treemap(df_t1, path=['Etiqueta'], values='Valor Invertido ($)', color='Valor Invertido ($)', color_continuous_scale='Blues')
        fig1.update_traces(textinfo="label")
        fig1.update_layout(margin=dict(t=10, l=10, r=10, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig1, use_container_width=True)

    with g2:
        st.write("**📊 Esfuerzo de Equipo (Horas Netas)**")
        df_b = df_f.groupby('Persona HR').agg({'Tiempo real': 'sum'}).reset_index().sort_values(by='Tiempo real')
        fig2 = px.bar(df_b, x='Tiempo real', y='Persona HR', orientation='h', text=df_b['Tiempo real'].map('{:,.1f}h'.format), color='Tiempo real', color_continuous_scale='Purples')
        fig2.update_traces(textposition='inside')
        fig2.update_layout(margin=dict(t=10, l=10, r=10, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.write("**🌿 Taxonomía de Tareas (Costo por Actividad en Clientes)**")
    df_t2 = df_f.groupby(['Nombre del cliente', 'Tipo de tarea']).agg({'Valor Invertido ($)': 'sum'}).reset_index()
    fig3 = px.treemap(df_t2, path=['Nombre del cliente', 'Tipo de tarea'], values='Valor Invertido ($)', color='Tipo de tarea', color_discrete_sequence=px.colors.qualitative.Safe)
    fig3.update_traces(texttemplate="%{label}<br>$%{value:,.0f}")
    fig3.update_layout(margin=dict(t=10, l=10, r=10, b=10))
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    
    # 11. EVOLUCIÓN CRONOLÓGICA
    st.subheader("📅 Tendencia Diaria del Esfuerzo")
    df_l = df_f.groupby('Fecha_Texto').agg({'Tiempo real': 'sum'}).reset_index()
    if not df_l.empty:
        fig4 = px.line(df_l, x='Fecha_Texto', y='Tiempo real', markers=True)
        fig4.update_traces(text=df_l['Tiempo real'].map('{:,.1f}h'.format), textposition="top center")
        st.plotly_chart(fig4, use_container_width=True)
    
    st.markdown("---")
    st.caption("goBIG Dashboard | Propiedad Intelectual 2026 | Desarrollado para Junta Directiva")
            
else:
    st.warning("Sin datos para mostrar. Verifique las fuentes en Google Sheets.")
