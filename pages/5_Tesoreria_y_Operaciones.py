import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Configuración de la página
st.set_page_config(page_title="Tesorería y Operaciones", page_icon="🏦", layout="wide")

# --- CANDADO DE SEGURIDAD ---
if not st.session_state.get("authentication_status"):
    st.warning("🔒 Acceso denegado. Por favor dirígete a la página de inicio (app) para iniciar sesión.")
    st.stop()
# ----------------------------

with st.sidebar:
    st.image("goBIG_logo.jpg", width=200)
    st.markdown("---")
    st.caption("v2.0 - Consola de Control Financiero Integral")

st.title("🏦 Tesorería, Cartera y Operaciones")
st.markdown("Control integrado de flujo de caja, cuentas por cobrar (CXC), proveedores (CXP) y previsión tributaria.")
st.markdown("---")

# 2. Funciones de limpieza de datos
def clean_numeric_series(series):
    cleaned = series.astype(str).str.replace('$', '', regex=False).str.replace(' ', '', regex=False)
    cleaned = cleaned.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    return pd.to_numeric(cleaned, errors='coerce').fillna(0)

def parse_dates(series):
    return pd.to_datetime(series, errors='coerce', dayfirst=True)

# 3. Descarga y limpieza de datos
@st.cache_data(ttl=300)
def load_tesoreria_data():
    url_doc = "https://docs.google.com/spreadsheets/d/1ldntONNpWFgXPcF8VINDKzNAhG_vGMdzGEOESM3aLNU/export?format=xlsx"
    xls = pd.ExcelFile(url_doc)
    
    # Buscar pestañas por palabra clave
    s_fact = [s for s in xls.sheet_names if 'facturaci' in s.lower()]
    s_prov = [s for s in xls.sheet_names if 'proveedor' in s.lower()]
    
    df_fact = pd.read_excel(xls, sheet_name=s_fact[0]) if s_fact else pd.DataFrame()
    df_prov = pd.read_excel(xls, sheet_name=s_prov[0]) if s_prov else pd.DataFrame()
    
    # --- Limpieza Facturación ---
    if not df_fact.empty:
        # Renombrar columnas clave si existen para estandarizar
        cols_fact = df_fact.columns.astype(str).str.lower()
        col_total = next((c for c in df_fact.columns if 'total factura' in c.lower()), None)
        col_pagado = next((c for c in df_fact.columns if 'monto pagado' in c.lower()), None)
        col_iva = next((c for c in df_fact.columns if 'iva' == c.lower().strip()), None)
        col_rst = next((c for c in df_fact.columns if 'rst - tarifa (12%)' in c.lower()), None)
        
        if col_total: df_fact['Total_Limpio'] = clean_numeric_series(df_fact[col_total])
        if col_pagado: df_fact['Pagado_Limpio'] = clean_numeric_series(df_fact[col_pagado])
        if col_iva: df_fact['IVA_Limpio'] = clean_numeric_series(df_fact[col_iva])
        if col_rst: df_fact['RST_Limpio'] = clean_numeric_series(df_fact[col_rst])
        
        # Fechas
        col_emision = next((c for c in df_fact.columns if 'fecha de emisi' in c.lower()), None)
        if col_emision: df_fact['Fecha_Emision_Clean'] = parse_dates(df_fact[col_emision])

    # --- Limpieza Proveedores ---
    if not df_prov.empty:
        col_total_prov = next((c for c in df_prov.columns if 'total a pagar' in c.lower()), None)
        col_pagado_prov = next((c for c in df_prov.columns if 'monto pagado' in c.lower()), None)
        
        if col_total_prov: df_prov['Total_Limpio'] = clean_numeric_series(df_prov[col_total_prov])
        if col_pagado_prov: df_prov['Pagado_Limpio'] = clean_numeric_series(df_prov[col_pagado_prov])

    return df_fact, df_prov

with st.spinner("Sincronizando Tesorería y Proveedores..."):
    try:
        df_fact, df_prov = load_tesoreria_data()
    except Exception as e:
        st.error(f"Error cargando bases de datos operativas: {e}")
        st.stop()

# 4. Consola de KPIs (Resumen Global)
st.subheader("🌐 Consola de Liquidez YTD (Year-To-Date)")

tot_fact = df_fact['Total_Limpio'].sum() if 'Total_Limpio' in df_fact.columns else 0
tot_cobr = df_fact['Pagado_Limpio'].sum() if 'Pagado_Limpio' in df_fact.columns else 0
tot_prov_pagar = df_prov['Total_Limpio'].sum() if 'Total_Limpio' in df_prov.columns else 0
tot_prov_pagado = df_prov['Pagado_Limpio'].sum() if 'Pagado_Limpio' in df_prov.columns else 0

iva_acum = df_fact['IVA_Limpio'].sum() if 'IVA_Limpio' in df_fact.columns else 0
rst_acum = df_fact['RST_Limpio'].sum() if 'RST_Limpio' in df_fact.columns else 0
reserva_fiscal = iva_acum + rst_acum

caja_neta = tot_cobr - tot_prov_pagado

col_k1, col_k2, col_k3, col_k4 = st.columns(4)
col_k1.metric("Facturado (Ingresos)", f"${tot_fact:,.0f}")
col_k2.metric("Recaudado (Caja Entrada)", f"${tot_cobr:,.0f}", f"{(tot_cobr/tot_fact*100) if tot_fact>0 else 0:.1f}% Efectividad")
col_k3.metric("Pagado a Proveedores", f"${tot_prov_pagado:,.0f}")
col_k4.metric("Reserva Fiscal (IVA+RST)", f"${reserva_fiscal:,.0f}", "Intocable", delta_color="off")

st.markdown("---")

# 5. Pestañas Integradas
tab1, tab2, tab3 = st.tabs(["💬 Cartera y Previsión Fiscal", "🤝 Proveedores y Rentabilidad", "📊 Mix de Ingresos"])

# ==========================================
# PESTAÑA 1: CARTERA Y FISCAL
# ==========================================
with tab1:
    st.markdown("### 🔍 Radar de Mora (Cuentas por Cobrar)")
    
    if not df_fact.empty and 'Fecha_Emision_Clean' in df_fact.columns:
        hoy = pd.to_datetime('today')
        # Filtramos facturas que NO dicen 'Sí' en pago (buscamos la columna de estado)
        col_estado_pago = next((c for c in df_fact.columns if 'pago / no pago' in c.lower()), None)
        
        if col_estado_pago:
            df_mora = df_fact[df_fact[col_estado_pago].astype(str).str.strip().str.lower() != 'sí'].copy()
            df_mora['Días de Mora'] = (hoy - df_mora['Fecha_Emision_Clean']).dt.days
            df_mora['Días de Mora'] = df_mora['Días de Mora'].apply(lambda x: x if x > 0 else 0)
            
            # Mostrar tabla de mora
            cols_mostrar = ['Cliente', 'Marca', '# factura', 'Fecha_Emision_Clean', 'Total_Limpio', 'Días de Mora']
            cols_disp = [c for c in cols_mostrar if c in df_mora.columns]
            
            if not df_mora.empty:
                st.dataframe(df_mora[cols_disp].sort_values(by='Días de Mora', ascending=False), use_container_width=True)
            else:
                st.success("✅ No hay facturas pendientes o en mora. ¡Excelente recaudo!")
                
    st.markdown("### 🏛️ Calendario Tributario y Reserva (Bimestral)")
    if not df_fact.empty and 'Mes' in df_fact.columns:
        # Lógica para agrupar por Bimestre según el Mes
        def asignar_bimestre(mes_str):
            m = str(mes_str).lower()
            if 'jan' in m or 'feb' in m: return '1 (Ene-Feb) -> Paga en Mayo'
            if 'mar' in m or 'apr' in m or 'abr' in m: return '2 (Mar-Abr) -> Paga en Junio'
            if 'may' in m or 'jun' in m: return '3 (May-Jun) -> Paga en Julio'
            if 'jul' in m or 'aug' in m or 'ago' in m: return '4 (Jul-Ago) -> Paga en Septiembre'
            if 'sep' in m or 'oct' in m: return '5 (Sep-Oct) -> Paga en Noviembre'
            if 'nov' in m or 'dec' in m or 'dic' in m: return '6 (Nov-Dic) -> Paga en Enero'
            return 'Sin clasificar'
            
        df_fact['Bimestre Fiscal'] = df_fact['Mes'].apply(asignar_bimestre)
        
        # Agrupar datos fiscales
        cols_fiscales = ['Bimestre Fiscal']
        agg_dict = {}
        if 'IVA_Limpio' in df_fact.columns: agg_dict['IVA_Limpio'] = 'sum'
        if 'RST_Limpio' in df_fact.columns: agg_dict['RST_Limpio'] = 'sum'
        
        if agg_dict:
            df_fiscal = df_fact.groupby('Bimestre Fiscal').agg(agg_dict).reset_index()
            df_fiscal['Reserva Total Sugerida'] = df_fiscal.sum(axis=1, numeric_only=True)
            st.dataframe(df_fiscal, use_container_width=True)

# ==========================================
# PESTAÑA 2: PROVEEDORES Y RENTABILIDAD
# ==========================================
with tab2:
    st.markdown("### 📤 Cuentas por Pagar (CXP)")
    if not df_prov.empty:
        col_estado_prov = next((c for c in df_prov.columns if 'pago / no pago' in c.lower()), None)
        if col_estado_prov:
            df_cxp = df_prov[df_prov[col_estado_prov].astype(str).str.strip().str.lower() != 'sí']
            
            if not df_cxp.empty:
                cols_prov_show = ['Mes', 'Cliente', 'Proveedor', 'Concepto', 'Total_Limpio', 'Fecha estimada de pago']
                cols_p = [c for c in cols_prov_show if c in df_cxp.columns]
                st.dataframe(df_cxp[cols_p], use_container_width=True)
            else:
                st.success("✅ No hay cuentas por pagar a proveedores pendientes.")
                
    st.markdown("### 💎 Margen Directo Agrupado por Cliente")
    if not df_fact.empty and not df_prov.empty and 'Cliente' in df_fact.columns and 'Cliente' in df_prov.columns:
        # Agrupar ingresos por cliente
        df_ingresos = df_fact.groupby('Cliente')['Total_Limpio'].sum().reset_index().rename(columns={'Total_Limpio': 'Ingresos Facturados'})
        # Agrupar costos por cliente
        df_costos = df_prov.groupby('Cliente')['Total_Limpio'].sum().reset_index().rename(columns={'Total_Limpio': 'Costo Proveedores'})
        
        # Unir ambas tablas
        df_rentabilidad = pd.merge(df_ingresos, df_costos, on='Cliente', how='outer').fillna(0)
        df_rentabilidad['Margen Bruto ($)'] = df_rentabilidad['Ingresos Facturados'] - df_rentabilidad['Costo Proveedores']
        
        fig_rent = px.bar(
            df_rentabilidad, 
            x='Cliente', 
            y=['Ingresos Facturados', 'Costo Proveedores'],
            barmode='group',
            title='Ingresos vs. Costos de Contratistas por Cliente'
        )
        st.plotly_chart(fig_rent, use_container_width=True)

# ==========================================
# PESTAÑA 3: MIX DE INGRESOS
# ==========================================
with tab3:
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        st.markdown("### 🔁 MRR vs Proyectos")
        if not df_fact.empty and 'Concepto de factura' in df_fact.columns:
            def clasificar_ingreso(concepto):
                c = str(concepto).lower()
                if 'fee' in c or 'fidelización' in c or 'mensual' in c: return 'MRR (Recurrente)'
                return 'Proyectos / Pauta (Puntual)'
                
            df_fact['Tipo Ingreso'] = df_fact['Concepto de factura'].apply(clasificar_ingreso)
            df_mix = df_fact.groupby('Tipo Ingreso')['Total_Limpio'].sum().reset_index()
            
            fig_mix = px.pie(df_mix, values='Total_Limpio', names='Tipo Ingreso', hole=0.4)
            st.plotly_chart(fig_mix, use_container_width=True)
            
    with col_m2:
        st.markdown("### 🎯 Concentración por Marca")
        if not df_fact.empty and 'Marca' in df_fact.columns:
            df_marca = df_fact.groupby('Marca')['Total_Limpio'].sum().reset_index().sort_values(by='Total_Limpio', ascending=True)
            fig_marca = px.bar(df_marca, x='Total_Limpio', y='Marca', orientation='h', title='Participación de Clientes')
            st.plotly_chart(fig_marca, use_container_width=True)
