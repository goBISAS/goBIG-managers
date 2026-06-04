import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la página
st.set_page_config(page_title="goBIG Financiero v1.0", page_icon="💰", layout="wide")

# 2. Barra Lateral: Logo Corporativo e Identidad Continua
with st.sidebar:
    st.image("goBIG_logo.jpg", width=200)
    st.markdown("---")
    st.caption("v1.0 - Consola de Control Financiero")
    st.info("💡 **Consejo:** El sistema separa automáticamente Google Workspace (gasto fijo) de Google Ads (pauta de clientes).")

# 3. Encabezado Principal
st.title("💰 Consola Financiera y Control de Caja")
st.markdown("Consolidación bancaria unificada, flujos de pauta publicitaria y auditoría contable.")
st.markdown("---")

# 4. Motor de extracción, normalización y reglas de BI
@st.cache_data(ttl=600)
def load_financial_data():
    try:
        url_documento = "https://docs.google.com/spreadsheets/d/1ldntONNpWFgXPcF8VINDKzNAhG_vGMdzGEOESM3aLNU/export?format=xlsx"
        
        # A. Extraer Cuenta Bancolombia
        df_bancolombia = pd.read_excel(url_documento, sheet_name="01_Movimientos financieros desde 2026 - Bancolombia", header=0)
        df_bancolombia['Cuenta'] = 'Bancolombia'
        
        # B. Extraer Cuenta BBVA
        df_bbva = pd.read_excel(url_documento, sheet_name="001_Movimientos Financieros BBVA desde 2026", header=0)
        df_bbva['Cuenta'] = 'BBVA'
        
        # C. Consolidar ambas fuentes
        df_caja = pd.concat([df_bancolombia, df_bbva], ignore_index=True)
        
        # Limpieza de nombres de columnas para evitar errores por saltos de línea
        df_caja.columns = df_caja.columns.str.replace(r'\n', ' ', regex=True).str.strip()
        
        # D. Normalización de fechas mixtas (Standard Latinoamericano)
        df_caja['Fecha del movimiento'] = pd.to_datetime(df_caja['Fecha del movimiento'], errors='coerce', dayfirst=True)
        df_caja = df_caja.dropna(subset=['Fecha del movimiento'])
        
        df_caja['Mes-Año'] = df_caja['Fecha del movimiento'].dt.strftime('%Y-%m')
        df_caja['Fecha_Texto'] = df_caja['Fecha del movimiento'].dt.strftime('%Y-%m-%d')
        
        # E. Conversión de montos financieros
        monto_col = [c for c in df_caja.columns if 'Monto del movimiento' in c][0]
        saldo_col = [c for c in df_caja.columns if 'Saldo en la cuenta' in c][0]
        
        df_caja['Monto_Neto'] = pd.to_numeric(df_caja[monto_col], errors='coerce').fillna(0)
        df_caja['Saldo_Neto'] = pd.to_numeric(df_caja[saldo_col], errors='coerce').fillna(0)
        
        # F. Limpieza de texto de control
        df_caja['Centro de costos'] = df_caja['Centro de costos'].astype(str).str.strip().str.lower()
        df_caja['Notas sobre el movimiento'] = df_caja['Notas sobre el movimiento'].astype(str).str.strip().str.lower()
        df_caja['Descripción detalle del movimiento'] = df_caja['Descripción detalle del movimiento'].astype(str).str.strip()
        
        # 🧠 MOTOR DE REGLAS JERÁRQUICAS (Clasificación Inteligente Blindada)
        def clasificar_movimiento(row):
            cc_manual = row['Centro de costos']
            nota_manual = row['Notas sobre el movimiento']
            desc = row['Descripción detalle del movimiento'].upper()
            
            # REGLA 1: Prioridad Absoluta al Centro de Costos escrito por el usuario
            if cc_manual != '' and cc_manual != 'nan':
                return cc_manual.upper()
                
            # REGLA 2: Blindaje de Pauta Publicitaria (Google/Meta Ads)
            if 'GOOGLE ADS' in desc or 'META ADS' in desc or 'FACEBOOK ADS' in desc or 'ADS' in desc:
                if nota_manual != '' and nota_manual != 'nan':
                    return f"PAUTA CLIENTE: {nota_manual.upper()}"
                else:
                    return "ALERTA: PAUTA SIN ASIGNAR CLIENTE"
            
            # REGLA 3: Gastos Fijos Internos Obvios (No requieren notas manuales)
            if 'GOOGLE WORKSPACE' in desc or 'SUCRIPCION GOOGLE' in desc or 'GOOGLE *WORKSPACE' in desc:
                return 'TECNOLOGÍA / SOFTWARE (INTERNO)'
            if 'CANVA' in desc:
                return 'TECNOLOGÍA / SOFTWARE (INTERNO)'
            if '4X1000' in desc or 'IMPTO GOBIERNO' in desc:
                return 'IMPUESTOS / GASTOS BANCARIOS'
            if 'DIAN' in desc or 'IMPUESTO DIAN' in desc:
                return 'IMPUESTOS'
            if 'ARRIENDO' in desc:
                return 'OFICINA / OPERACIÓN'
            if 'NEQUI' in desc and ('CONTADORA' in desc or 'CONTABIL' in desc):
                return 'HONORARIOS / CONTABILIDAD'
            if 'INTERBANC LAATARA' in desc or 'INTERBANC SOCIEDAD HOTELE' in desc:
                return 'INGRESOS CLIENTES'
                
            # REGLA 4: Identificación de sospecha de Gastos Variables (Uber, Didi, Restaurantes)
            if 'UBER' in desc or 'DIDI' in desc or 'CABIFY' in desc:
                return 'POR CLASIFICAR - TRANSPORTE'
            if 'RESTAURANTE' in desc or 'TIENDA D1' in desc or 'ALMUERZO' in desc or 'CAFE' in desc or 'SAN GIORGI' in desc or 'ATELIER' in desc:
                return 'POR CLASIFICAR - ALIMENTACIÓN'
                
            # REGLA 5: Fallback general para egresos desconocidos
            if row['Monto_Neto'] < 0:
                return 'POR CLASIFICAR - GENERAL'
            return 'OTROS INGRESOS'
            
        df_caja['Centro_Costos_BI'] = df_caja.apply(clasificar_movimiento, axis=1)
        
        df_caja['Ingreso ($)'] = df_caja['Monto_Neto'].apply(lambda x: x if x > 0 else 0)
        df_caja['Egreso ($)'] = df_caja['Monto_Neto'].apply(lambda x: abs(x) if x < 0 else 0)
        
        return df_caja.sort_values(by='Fecha del movimiento', ascending=True)
        
    except Exception as e:
        st.error(f"Error al procesar los extractos financieros: {e}")
        return pd.DataFrame()

# 5. Ejecución del motor
if st.button("🔄 Actualizar Extractos Bancarios"):
    st.cache_data.clear()

with st.spinner("Sincronizando bancos y aplicando reglas de pauta y gastos variables..."):
    df_caja = load_financial_data()

if not df_caja.empty:
    # 6. CONSOLA DE FILTROS
    st.subheader("🔍 Consola de Mandos Financiera")
    col_f1, col_f2, col_f3 = st.columns(3)
    
    cuenta_sel = col_f1.selectbox("Cuenta Bancaria:", ["Consolidado (Ambas)", "Bancolombia", "BBVA"])
    mes_sel = col_f2.selectbox("Mes Calendario:", ["Todos"] + sorted(list(df_caja['Mes-Año'].unique()), reverse=True))
    lista_cc = ["Todos"] + sorted(list(df_caja['Centro_Costos_BI'].unique()))
    cc_sel = col_f3.selectbox("Centro de Costos:", lista_cc)
    
    df_filtrado = df_caja.copy()
    if cuenta_sel != "Consolidado (Ambas)":
        df_filtrado = df_filtrado[df_filtrado['Cuenta'] == cuenta_sel]
    if mes_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Mes-Año'] == mes_sel]
    if cc_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Centro_Costos_BI'] == cc_sel]
        
    st.markdown("---")
    
    # 7. KPIs NETOS DE LIQUIDEZ
    st.subheader("📊 Resumen de Caja y Flujo de Efectivo")
    k1, k2, k3, k4 = st.columns(4)
    
    if cuenta_sel == "Consolidado (Ambas)":
        ultimo_bancolombia = df_caja[df_caja['Cuenta'] == 'Bancolombia']['Saldo_Neto'].iloc[-1] if not df_caja[df_caja['Cuenta'] == 'Bancolombia'].empty else 0
        ultimo_bbva = df_caja[df_caja['Cuenta'] == 'BBVA']['Saldo_Neto'].iloc[-1] if not df_caja[df_caja['Cuenta'] == 'BBVA'].empty else 0
        saldo_disponible = ultimo_bancolombia + ultimo_bbva
    else:
        saldo_disponible = df_filtrado['Saldo_Neto'].iloc[-1] if not df_filtrado.empty else 0
        
    ingresos_totales = df_filtrado['Ingreso ($)'].sum()
    egresos_totales = df_filtrado['Egreso ($)'].sum()
    flujo_neto = ingresos_totales - egresos_totales
    
    k1.metric("Saldo Disponible Total", f"${saldo_disponible:,.2f}")
    k2.metric("Ingresos (Entradas)", f"${ingresos_totales:,.2f}")
    k3.metric("Egresos (Salidas)", f"${egresos_totales:,.2f}")
    k4.metric("Flujo de Caja Neto", f"${flujo_neto:,.2f}", delta=f"${flujo_neto:,.2f}")
    
    st.markdown("---")
    
    # 8. 🚨 PANEL DE AUDITORÍA AUTOMÁTICA (Semáforos Detallados con Mini-Tabla Directa)
    st.subheader("🚨 Semáforos e Insights de Auditoría Bancaria")
    
    # Buscamos las transacciones huérfanas que requieren atención del director
    df_alertas = df_filtrado[df_filtrado['Centro_Costos_BI'].str.startswith('POR CLASIFICAR') | (df_filtrado['Centro_Costos_BI'] == 'ALERTA: PAUTA SIN ASIGNAR CLIENTE')]
    
    if not df_alertas.empty:
        st.error(f"🔴 **Semáforo de Higiene Contable:** Se detectaron **{len(df_alertas)} transacciones** variables o pautas publicitarias pendientes de revisión. Aquí tienes los datos exactos para completarlos en tu Google Sheets:")
        
        # Pintamos la mini-tabla detallada interactiva en pantalla
        st.dataframe(
            df_alertas[['Fecha_Texto', 'Descripción detalle del movimiento', 'Cuenta', 'Monto_Neto', 'Centro_Costos_BI']],
            use_container_width=True
        )
    else:
        st.success("🟢 **Semáforo de Higiene Contable:** ¡Caja Impecable! Todos los movimientos de este recorte corresponden a gastos fijos mapeados o tienen su centro de costos al día.")
        
    # B. Alerta Informativa del 4x1000
    gasto_4x1000 = df_filtrado[df_filtrado['Centro_Costos_BI'] == 'IMPUESTOS / GASTOS BANCARIOS']['Egreso ($)'].sum()
    if gasto_4x1000 > 0:
        st.info(f"💸 **Fuga por Gravamen Bancario:** El cobro del 4x1000 y comisiones le han costado a goBIG un acumulado de **${gasto_4x1000:,.2f}** en el periodo seleccionado.")

    st.markdown("---")
    st.caption("goBIG Financial Dashboard v1.0 | Área de Control de Caja Seguro")

else:
    st.warning("No se encontraron datos financieros válidos.")
