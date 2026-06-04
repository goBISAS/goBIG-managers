import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la página
st.set_page_config(page_title="goBIG Financiero v1.1", page_icon="💰", layout="wide")

# Barra Lateral con Identidad
with st.sidebar:
    st.image("goBIG_logo.jpg", width=200)
    st.markdown("---")
    st.caption("v1.1 - Consola de Control Financiero")
    st.info("💡 **Tip:** Esta versión incluye limpieza automática de formatos de moneda (USA/COL).")

st.title("💰 Consola Financiera y Control de Caja")
st.markdown("Consolidación bancaria unificada y auditoría contable avanzada.")
st.markdown("---")

# 2. Funciones de Limpieza Especializadas
def clean_currency_global(value):
    """Convierte formatos de moneda COL o USA a número puro."""
    if pd.isna(value) or value == '': return 0.0
    val_str = str(value).replace('$', '').replace(' ', '').strip()
    
    # Si tiene puntos y comas (ej: 1.234.567,89 o 1,234,567.89)
    if ',' in val_str and '.' in val_str:
        if val_str.find('.') < val_str.find(','): # Formato COL/EUR: 1.234,56
            val_str = val_str.replace('.', '').replace(',', '.')
        else: # Formato USA: 1,234.56
            val_str = val_str.replace(',', '')
    elif ',' in val_str: # Solo comas (podría ser decimal COL o miles USA)
        if len(val_str.split(',')[-1]) <= 2: # Es decimal (COL)
            val_str = val_str.replace(',', '.')
        else: # Es miles (USA)
            val_str = val_str.replace(',', '')
    
    return pd.to_numeric(val_str, errors='coerce') or 0.0

# 3. Motor de extracción con Búsqueda Flexible de Pestañas
@st.cache_data(ttl=600)
def load_financial_data():
    try:
        url_documento = "https://docs.google.com/spreadsheets/d/1ldntONNpWFgXPcF8VINDKzNAhG_vGMdzGEOESM3aLNU/export?format=xlsx"
        
        # Leemos el archivo completo para listar las pestañas existentes
        xls = pd.ExcelFile(url_documento)
        sheet_names = xls.sheet_names
        
        # Buscamos las pestañas por palabra clave para evitar errores de nombres exactos
        sheet_bancolombia = [s for s in sheet_names if 'Bancolombia' in s][0]
        sheet_bbva = [s for s in sheet_names if 'BBVA' in s][0]
        
        df_bancolombia = pd.read_excel(xls, sheet_name=sheet_bancolombia, header=0)
        df_bancolombia['Cuenta'] = 'Bancolombia'
        
        df_bbva = pd.read_excel(xls, sheet_name=sheet_bbva, header=0)
        df_bbva['Cuenta'] = 'BBVA'
        
        df_caja = pd.concat([df_bancolombia, df_bbva], ignore_index=True)
        df_caja.columns = df_caja.columns.str.replace(r'\n', ' ', regex=True).str.strip()
        
        # Normalización de fechas
        df_caja['Fecha del movimiento'] = pd.to_datetime(df_caja['Fecha del movimiento'], errors='coerce', dayfirst=True)
        df_caja = df_caja.dropna(subset=['Fecha del movimiento'])
        df_caja['Mes-Año'] = df_caja['Fecha del movimiento'].dt.strftime('%Y-%m')
        df_caja['Fecha_Texto'] = df_caja['Fecha del movimiento'].dt.strftime('%Y-%m-%d')
        
        # LIMPIEZA DE DINERO (USA / COL)
        monto_col = [c for c in df_caja.columns if 'Monto del movimiento' in c][0]
        saldo_col = [c for c in df_caja.columns if 'Saldo en la cuenta' in c][0]
        
        df_caja['Monto_Neto'] = df_caja[monto_col].apply(clean_currency_global)
        df_caja['Saldo_Neto'] = df_caja[saldo_col].apply(clean_currency_global)
        
        # Clasificación Inteligente (Fijos, Pauta y Variables)
        def clasificar(row):
            cc_manual = str(row['Centro de costos']).strip().lower()
            nota_manual = str(row['Notas sobre el movimiento']).strip().lower()
            desc = str(row['Descripción detalle del movimiento']).upper()
            
            if cc_manual not in ['', 'nan', 'none']: return cc_manual.upper()
            
            # Reglas de Pauta
            if any(x in desc for x in ['GOOGLE ADS', 'META ADS', 'FACEBOOK ADS', 'ADS']):
                return f"PAUTA: {nota_manual.upper()}" if nota_manual not in ['', 'nan'] else "ALERTA: PAUTA SIN CLIENTE"
            
            # Reglas Automáticas
            if 'WORKSPACE' in desc or 'GOOGLE *' in desc: return 'SOFTWARE (INTERNO)'
            if 'CANVA' in desc: return 'SOFTWARE (INTERNO)'
            if '4X1000' in desc or 'GOBIERNO' in desc: return 'IMPUESTOS BANCARIOS'
            if 'DIAN' in desc: return 'IMPUESTOS DIAN'
            if 'ARRIENDO' in desc: return 'OFICINA'
            if 'NEQUI' in desc and ('CONTADORA' in desc or 'CONTABIL' in desc): return 'HONORARIOS'
            if 'INTERBANC' in desc: return 'INGRESOS CLIENTES'
            
            # Sospecha de Variables
            if any(x in desc for x in ['UBER', 'DIDI', 'CABIFY']): return 'POR CLASIFICAR - TRANSPORTE'
            if any(x in desc for x in ['RESTAURANTE', 'ALMUERZO', 'CAFE', 'D1', 'ATELIER']): return 'POR CLASIFICAR - ALIMENTACIÓN'
            
            return 'POR CLASIFICAR - GENERAL' if row['Monto_Neto'] < 0 else 'OTROS INGRESOS'
            
        df_caja['Centro_Costos_BI'] = df_caja.apply(clasificar, axis=1)
        df_caja['Ingreso ($)'] = df_caja['Monto_Neto'].apply(lambda x: x if x > 0 else 0)
        df_caja['Egreso ($)'] = df_caja['Monto_Neto'].apply(lambda x: abs(x) if x < 0 else 0)
        
        return df_caja.sort_values(by='Fecha del movimiento', ascending=True)
        
    except Exception as e:
        st.error(f"Error técnico: {e}")
        return pd.DataFrame()

# 4. Interfaz
if st.button("🔄 Actualizar Datos"):
    st.cache_data.clear()

with st.spinner("Limpiando formatos de moneda y unificando cuentas..."):
    df_caja = load_financial_data()

if not df_caja.empty:
    # FILTROS
    c1, c2, c3 = st.columns(3)
    cuenta_sel = c1.selectbox("Cuenta:", ["Consolidado (Ambas)", "Bancolombia", "BBVA"])
    mes_sel = c2.selectbox("Mes:", ["Todos"] + sorted(list(df_caja['Mes-Año'].unique()), reverse=True))
    cc_sel = c3.selectbox("Centro de Costos:", ["Todos"] + sorted(list(df_caja['Centro_Costos_BI'].unique())))
    
    df_f = df_caja.copy()
    if cuenta_sel != "Consolidado (Ambas)": df_f = df_f[df_f['Cuenta'] == cuenta_sel]
    if mes_sel != "Todos": df_f = df_f[df_f['Mes-Año'] == mes_sel]
    if cc_sel != "Todos": df_f = df_f[df_f['Centro_Costos_BI'] == cc_sel]
    
    # KPIs
    st.subheader("📊 Resumen de Flujo de Caja")
    k1, k2, k3, k4 = st.columns(4)
    
    # Saldo final real
    if cuenta_sel == "Consolidado (Ambas)":
        s_ban = df_caja[df_caja['Cuenta'] == 'Bancolombia']['Saldo_Neto'].iloc[-1] if not df_caja[df_caja['Cuenta'] == 'Bancolombia'].empty else 0
        s_bbva = df_caja[df_caja['Cuenta'] == 'BBVA']['Saldo_Neto'].iloc[-1] if not df_caja[df_caja['Cuenta'] == 'BBVA'].empty else 0
        saldo_dispo = s_ban + s_bbva
    else:
        saldo_dispo = df_f['Saldo_Neto'].iloc[-1] if not df_f.empty else 0

    k1.metric("Saldo Disponible", f"${saldo_dispo:,.2f}")
    k2.metric("Ingresos", f"${df_f['Ingreso ($)'].sum():,.2f}")
    k3.metric("Egresos", f"${df_f['Egreso ($)'].sum():,.2f}")
    flujo = df_f['Ingreso ($)'].sum() - df_f['Egreso ($)'].sum()
    k4.metric("Flujo Neto", f"${flujo:,.2f}", delta=f"${flujo:,.2f}")

    # AUDITORÍA
    st.subheader("🚨 Auditoría de Movimientos")
    alertas = df_f[df_f['Centro_Costos_BI'].str.contains('POR CLASIFICAR|ALERTA')]
    if not alertas.empty:
        st.error(f"🔴 Se detectaron **{len(alertas)} transacciones** pendientes de clasificar:")
        st.dataframe(alertas[['Fecha_Texto', 'Descripción detalle del movimiento', 'Monto_Neto', 'Centro_Costos_BI']], use_container_width=True)
    else:
        st.success("🟢 ¡Caja Impecable! Todos los movimientos están mapeados.")

    with st.expander("👀 Ver Libro de Caja Completo"):
        st.dataframe(df_f[['Fecha_Texto', 'Descripción detalle del movimiento', 'Cuenta', 'Monto_Neto', 'Centro_Costos_BI', 'Saldo_Neto']])
