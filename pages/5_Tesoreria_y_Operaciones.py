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

# 2. Funciones de Formato y Limpieza
def clean_numeric_series(series):
    cleaned = series.astype(str).str.replace('$', '', regex=False).str.replace(' ', '', regex=False)
    cleaned = cleaned.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    return pd.to_numeric(cleaned, errors='coerce').fillna(0)

def parse_dates(series):
    return pd.to_datetime(series, errors='coerce', dayfirst=True)

def formato_cop(valor):
    """Convierte un número a formato de moneda colombiana estricto."""
    try:
        return f"$ {float(valor):,.0f} COP".replace(",", ".")
    except:
        return "$ 0 COP"

# 3. Descarga y limpieza de datos
@st.cache_data(ttl=300)
def load_tesoreria_data():
    url_doc = "https://docs.google.com/spreadsheets/d/1ldntONNpWFgXPcF8VINDKzNAhG_vGMdzGEOESM3aLNU/export?format=xlsx"
    xls = pd.ExcelFile(url_doc)
    
    s_fact = [s for s in xls.sheet_names if 'facturaci' in s.lower()]
    s_prov = [s for s in xls.sheet_names if 'proveedor' in s.lower()]
    
    df_fact = pd.read_excel(xls, sheet_name=s_fact[0]) if s_fact else pd.DataFrame()
    df_prov = pd.read_excel(xls, sheet_name=s_prov[0]) if s_prov else pd.DataFrame()
    
    # --- DEPURACIÓN DE FILAS VACÍAS (Punto 5) ---
    if not df_fact.empty and 'Cliente' in df_fact.columns:
        df_fact = df_fact[df_fact['Cliente'].notna()]
        df_fact = df_fact[df_fact['Cliente'].astype(str).str.strip() != '']
        df_fact = df_fact[df_fact['Cliente'].astype(str).str.lower() != 'none']
        
    if not df_prov.empty and 'Cliente' in df_prov.columns:
        df_prov = df_prov[df_prov['Cliente'].notna()]
        df_prov = df_prov[df_prov['Cliente'].astype(str).str.strip() != '']
        df_prov = df_prov[df_prov['Cliente'].astype(str).str.lower() != 'none']

    # --- Limpieza Facturación ---
    if not df_fact.empty:
        col_total = next((c for c in df_fact.columns if 'total factura' in c.lower()), None)
        col_pagado = next((c for c in df_fact.columns if 'monto pagado' in c.lower()), None)
        col_iva = next((c for c in df_fact.columns if 'iva' == c.lower().strip()), None)
        col_rst = next((c for c in df_fact.columns if 'rst - tarifa' in c.lower()), None)
        
        if col_total: df_fact['Monto_Facturado'] = clean_numeric_series(df_fact[col_total])
        if col_pagado: df_fact['Valor_Recaudado'] = clean_numeric_series(df_fact[col_pagado])
        if col_iva: df_fact['IVA'] = clean_numeric_series(df_fact[col_iva])
        if col_rst: df_fact['RST_12%'] = clean_numeric_series(df_fact[col_rst])
        
        col_emision = next((c for c in df_fact.columns if 'fecha de emisi' in c.lower()), None)
        if col_emision: df_fact['Fecha_Emision_Real'] = parse_dates(df_fact[col_emision])

    # --- Limpieza Proveedores ---
    if not df_prov.empty:
        col_total_prov = next((c for c in df_prov.columns if 'total a pagar' in c.lower()), None)
        col_pagado_prov = next((c for c in df_prov.columns if 'monto pagado' in c.lower()), None)
        
        if col_total_prov: df_prov['Costo_Proyectado'] = clean_numeric_series(df_prov[col_total_prov])
        if col_pagado_prov: df_prov['Pago_Realizado'] = clean_numeric_series(df_prov[col_pagado_prov])

    return df_fact, df_prov

with st.spinner("Sincronizando Tesorería y Operaciones..."):
    try:
        df_fact, df_prov = load_tesoreria_data()
    except Exception as e:
        st.error(f"Error cargando bases de datos operativas: {e}")
        st.stop()

# 4. Consola de KPIs (Resumen Global)
st.subheader("🌐 Consola de Liquidez YTD (Year-To-Date)")

tot_fact = df_fact['Monto_Facturado'].sum() if 'Monto_Facturado' in df_fact.columns else 0
tot_cobr = df_fact['Valor_Recaudado'].sum() if 'Valor_Recaudado' in df_fact.columns else 0
tot_prov_pagar = df_prov['Costo_Proyectado'].sum() if 'Costo_Proyectado' in df_prov.columns else 0
tot_prov_pagado = df_prov['Pago_Realizado'].sum() if 'Pago_Realizado' in df_prov.columns else 0

iva_acum = df_fact['IVA'].sum() if 'IVA' in df_fact.columns else 0
rst_acum = df_fact['RST_12%'].sum() if 'RST_12%' in df_fact.columns else 0
reserva_fiscal = iva_acum + rst_acum

col_k1, col_k2, col_k3, col_k4 = st.columns(4)
col_k1.metric("Facturado (Ingresos)", formato_cop(tot_fact))
col_k2.metric("Recaudado (Caja Entrada)", formato_cop(tot_cobr), f"{(tot_cobr/tot_fact*100) if tot_fact>0 else 0:.1f}% Efectividad")
col_k3.metric("Pagado a Proveedores", formato_cop(tot_prov_pagado))
col_k4.metric("Reserva Fiscal (IVA+RST)", formato_cop(reserva_fiscal), "Intocable", delta_color="off")

st.markdown("---")

# 5. Pestañas Integradas
tab1, tab2, tab3 = st.tabs(["💬 Cartera y Previsión Fiscal", "🤝 Proveedores y Rentabilidad", "📊 Mix de Ingresos"])

# ==========================================
# PESTAÑA 1: CARTERA Y FISCAL
# ==========================================
with tab1:
    st.markdown("### 🔍 Radar de Mora (Cuentas por Cobrar)")
    
    if not df_fact.empty and 'Fecha_Emision_Real' in df_fact.columns:
        hoy = pd.to_datetime('today')
        col_estado_pago = next((c for c in df_fact.columns if 'pago / no pago' in c.lower()), None)
        col_factura_id = next((c for c in df_fact.columns if '# factura' in c.lower()), None)
        
        if col_estado_pago and col_factura_id:
            # Filtrar facturas sin pagar
            df_pendientes = df_fact[df_fact[col_estado_pago].astype(str).str.strip().str.lower() != 'sí'].copy()
            df_pendientes['Días Transcurridos'] = (hoy - df_pendientes['Fecha_Emision_Real']).dt.days
            df_pendientes['Días Transcurridos'] = df_pendientes['Días Transcurridos'].apply(lambda x: x if x > 0 else 0)
            
            # Clasificación de Mora (Punto 1)
            df_gracia = df_pendientes[df_pendientes['Días Transcurridos'] <= 30]
            df_mora = df_pendientes[df_pendientes['Días Transcurridos'] > 30]
            
            # Tarjetas de resumen
            c1, c2 = st.columns(2)
            c1.info(f"**⏳ Facturas por vencer (0 - 30 días):** {len(df_gracia)} facturas")
            c2.error(f"**🚨 Facturas en Mora Crítica (> 30 días):** {len(df_mora)} facturas")
            
            # Mostrar tabla de mora si existe
            if not df_mora.empty:
                st.markdown("##### Detalle de Cartera Vencida")
                df_mora_display = df_mora[['Cliente', 'Marca', col_factura_id, 'Fecha_Emision_Real', 'Monto_Facturado', 'Días Transcurridos']].copy()
                df_mora_display['Monto Facturado ($)'] = df_mora_display['Monto_Facturado'].apply(formato_cop)
                df_mora_display['Fecha Emisión'] = df_mora_display['Fecha_Emision_Real'].dt.strftime('%Y-%m-%d')
                df_mora_display = df_mora_display.sort_values(by='Días Transcurridos', ascending=False)
                
                st.dataframe(df_mora_display[['Cliente', 'Marca', col_factura_id, 'Fecha Emisión', 'Monto Facturado ($)', 'Días Transcurridos']], use_container_width=True)
            else:
                st.success("✅ No hay facturas en mora mayor a 30 días.")
                
    st.markdown("---")
    st.markdown("### 🏛️ Calendario Tributario y Reserva (Bimestral)")
    
    if not df_fact.empty and 'Mes' in df_fact.columns:
        # Lógica exacta de agrupación bimestral (Punto 4)
        def asignar_bimestre(mes_str):
            m = str(mes_str).lower()
            if 'jan' in m or 'feb' in m or 'ene' in m: return '1 (Ene-Feb) -> Paga en Mayo'
            if 'mar' in m or 'apr' in m or 'abr' in m: return '2 (Mar-Abr) -> Paga en Junio'
            if 'may' in m or 'jun' in m: return '3 (May-Jun) -> Paga en Julio'
            if 'jul' in m or 'aug' in m or 'ago' in m: return '4 (Jul-Ago) -> Paga en Septiembre'
            if 'sep' in m or 'oct' in m: return '5 (Sep-Oct) -> Paga en Noviembre'
            if 'nov' in m or 'dec' in m or 'dic' in m: return '6 (Nov-Dic) -> Paga en Enero'
            return None
            
        df_fact['Bimestre Fiscal'] = df_fact['Mes'].apply(asignar_bimestre)
        df_fiscal_base = df_fact[df_fact['Bimestre Fiscal'].notna()].copy()
        
        if not df_fiscal_base.empty:
            df_fiscal = df_fiscal_base.groupby('Bimestre Fiscal')[['IVA', 'RST_12%']].sum().reset_index()
            df_fiscal['Reserva Total Sugerida'] = df_fiscal['IVA'] + df_fiscal['RST_12%']
            
            # Aplicar formato COP (Puntos 2 y 3)
            df_fiscal['IVA ($)'] = df_fiscal['IVA'].apply(formato_cop)
            df_fiscal['RST 12% ($)'] = df_fiscal['RST_12%'].apply(formato_cop)
            df_fiscal['Reserva Sugerida ($)'] = df_fiscal['Reserva Total Sugerida'].apply(formato_cop)
            
            df_fiscal = df_fiscal.sort_values(by='Bimestre Fiscal')
            st.dataframe(df_fiscal[['Bimestre Fiscal', 'IVA ($)', 'RST 12% ($)', 'Reserva Sugerida ($)']], use_container_width=True)

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
                df_cxp_display = df_cxp.copy()
                df_cxp_display['Total a Pagar ($)'] = df_cxp_display['Costo_Proyectado'].apply(formato_cop)
                cols_prov_show = ['Mes', 'Cliente', 'Proveedor', 'Concepto', 'Total a Pagar ($)', 'Fecha estimada de pago']
                cols_p = [c for c in cols_prov_show if c in df_cxp_display.columns]
                st.dataframe(df_cxp_display[cols_p], use_container_width=True)
            else:
                st.success("✅ No hay cuentas por pagar a proveedores pendientes.")
                
    st.markdown("### 💎 Margen Directo Agrupado por Cliente")
    if not df_fact.empty and not df_prov.empty and 'Cliente' in df_fact.columns and 'Cliente' in df_prov.columns:
        df_ingresos = df_fact.groupby('Cliente')['Monto_Facturado'].sum().reset_index().rename(columns={'Monto_Facturado': 'Ingresos Facturados ($)'})
        df_costos = df_prov.groupby('Cliente')['Costo_Proyectado'].sum().reset_index().rename(columns={'Costo_Proyectado': 'Costo Proveedores ($)'})
        
        df_rentabilidad = pd.merge(df_ingresos, df_costos, on='Cliente', how='outer').fillna(0)
        
        fig_rent = px.bar(
            df_rentabilidad, 
            x='Cliente', 
            y=['Ingresos Facturados ($)', 'Costo Proveedores ($)'],
            barmode='group',
            text_auto='.3s', # Formato numérico abreviado sobre barras (Punto 6)
            title='Ingresos vs. Costos de Contratistas por Cliente'
        )
        fig_rent.update_traces(textposition='outside')
        st.plotly_chart(fig_rent, use_container_width=True)

# ==========================================
# PESTAÑA 3: MIX DE INGRESOS
# ==========================================
with tab3:
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        st.markdown("### 🔁 MRR vs Proyectos")
        if not df_fact.empty and 'Concepto de factura' in df_fact.columns:
            # Regla binaria exacta (Punto 7)
            def clasificar_ingreso(concepto):
                if 'fee' in str(concepto).lower():
                    return 'MRR (Recurrente)'
                return 'Proyecto (Puntual)'
                
            df_fact['Tipo Ingreso'] = df_fact['Concepto de factura'].apply(clasificar_ingreso)
            df_mix = df_fact.groupby('Tipo Ingreso')['Monto_Facturado'].sum().reset_index()
            
            fig_mix = px.pie(
                df_mix, 
                values='Monto_Facturado', 
                names='Tipo Ingreso', 
                hole=0.4,
                title='Distribución de Ingresos'
            )
            fig_mix.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_mix, use_container_width=True)
            
    with col_m2:
        st.markdown("### 🎯 Concentración por Marca")
        if not df_fact.empty and 'Marca' in df_fact.columns:
            df_marca = df_fact.groupby('Marca')['Monto_Facturado'].sum().reset_index().sort_values(by='Monto_Facturado', ascending=True)
            fig_marca = px.bar(
                df_marca, 
                x='Monto_Facturado', 
                y='Marca', 
                orientation='h', 
                text_auto='.3s', # Datos visibles (Punto 6)
                title='Participación de Ingresos por Marca',
                labels={'Monto_Facturado': 'Ingreso Total ($)'}
            )
            st.plotly_chart(fig_marca, use_container_width=True)
