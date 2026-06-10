import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la página
st.set_page_config(page_title="goBIG Financiero v1.6", page_icon="💰", layout="wide")

# Barra Lateral con Identidad Continua
with st.sidebar:
    st.image("goBIG_logo.jpg", width=200)
    st.markdown("---")
    st.caption("v1.6 - Consola de Control Financiero")
    st.info("💡 **Actualización:** Motor cronológico estricto con lectura de columna de 'Año'.")

st.title("💰 Consola Financiera y Control de Caja")
st.markdown("Consolidación bancaria unificada y auditoría contable avanzada.")
st.markdown("---")

# 2. Funciones de Limpieza Especializadas
def clean_currency_global(value):
    if pd.isna(value) or str(value).strip() in ['', 'nan', 'None']: return 0.0
    val_str = str(value).replace('$', '').replace(' ', '').strip()
    if ',' in val_str and '.' in val_str:
        if val_str.find('.') < val_str.find(','): 
            val_str = val_str.replace('.', '').replace(',', '.')
        else: 
            val_str = val_str.replace(',', '')
    elif ',' in val_str: 
        if len(val_str.split(',')[-1]) <= 2: 
            val_str = val_str.replace(',', '.')
        else: 
            val_str = val_str.replace(',', '')
    try:
        return float(val_str)
    except ValueError:
        return 0.0

# 3. Motor de extracción elástico y cronológico
@st.cache_data(ttl=600)
def load_financial_data():
    try:
        url_documento = "https://docs.google.com/spreadsheets/d/1ldntONNpWFgXPcF8VINDKzNAhG_vGMdzGEOESM3aLNU/export?format=xlsx"
        
        xls = pd.ExcelFile(url_documento)
        sheet_names = xls.sheet_names
        
        matches_bancolombia = [s for s in sheet_names if s.startswith('01_')]
        matches_bbva = [s for s in sheet_names if s.startswith('001')]
        
        if not matches_bancolombia:
            st.error("❌ No se encontró la pestaña que inicia con '01_'.")
            return pd.DataFrame()
            
        df_bancolombia = pd.read_excel(xls, sheet_name=matches_bancolombia[0], header=0)
        df_bancolombia['Cuenta'] = 'Bancolombia'
        
        if matches_bbva:
            try:
                df_bbva_raw = pd.read_excel(xls, sheet_name=matches_bbva[0], header=0)
                if df_bbva_raw.empty or len(df_bbva_raw.columns) < 2:
                    df_bbva = pd.DataFrame(columns=df_bancolombia.columns)
                    df_bbva.loc[0] = [None] * len(df_bancolombia.columns)
                else:
                    df_bbva = df_bbva_raw.copy()
            except Exception:
                df_bbva = pd.DataFrame(columns=df_bancolombia.columns)
        else:
            df_bbva = pd.DataFrame(columns=df_bancolombia.columns)
            
        df_bbva['Cuenta'] = 'BBVA'
        
        # Unificar (pandas alinea las columnas por nombre automáticamente)
        df_caja = pd.concat([df_bancolombia, df_bbva], ignore_index=True)
        df_caja.columns = df_caja.columns.str.replace(r'\n', ' ', regex=True).str.strip()
        
        matches_monto = [c for c in df_caja.columns if 'monto' in c.lower()]
        matches_saldo = [c for c in df_caja.columns if 'saldo' in c.lower()]
        matches_fecha = [c for c in df_caja.columns if 'fecha' in c.lower()]
        matches_ano = [c for c in df_caja.columns if 'año' in c.lower() or 'ano' in c.lower() or 'year' in c.lower()]
        
        df_caja['Monto_Neto'] = df_caja[matches_monto[0]].apply(clean_currency_global)
        df_caja['Saldo_Neto'] = df_caja[matches_saldo[0]].apply(clean_currency_global)
        
        # 🛡️ ESCUDO DE FECHAS ESTRICTO CON COLUMNA AÑO
        date_col_name = matches_fecha[0] if matches_fecha else None
        year_col_name = matches_ano[0] if matches_ano else None
        
        def fix_strict_date(row):
            if not date_col_name: return pd.NaT
            d = str(row[date_col_name]).strip().replace('-', '/')
            if d.lower() in ['nan', 'none', 'nat', '']: return pd.NaT
            
            y = str(row[year_col_name]).strip() if year_col_name else "2026"
            if '.' in y: y = y.split('.')[0] # Limpiar si viene como 2026.0
            if not y.isdigit() or len(y) != 4: y = "2026" # Fallback de seguridad
            
            # Autocompletado si el banco exportó solo Día/Mes
            if len(d) <= 5 and '/' in d:
                parts = d.split('/')
                if len(parts) == 2:
                    d = f"{parts[0]}/{parts[1]}/{y}"
            return d

        cleaned_dates = df_caja.apply(fix_strict_date, axis=1)
        # Forzamos dayfirst=True para garantizar lectura latina estricta
        df_caja['Fecha del movimiento'] = pd.to_datetime(cleaned_dates, format='mixed', dayfirst=True, errors='coerce')
        
        df_caja = df_caja.dropna(subset=['Fecha del movimiento'])
        df_caja = df_caja[df_caja['Fecha del movimiento'].dt.year >= 2020] # Filtro Anti-Fantasmas
        
        df_caja['Mes-Año'] = df_caja['Fecha del movimiento'].dt.strftime('%Y-%m')
        df_caja['Fecha_Texto'] = df_caja['Fecha del movimiento'].dt.strftime('%Y-%m-%d')
        
        desc_cols = [c for c in df_caja.columns if 'descrip' in c.lower() or 'detalle' in c.lower()]
        cc_cols = [c for c in df_caja.columns if 'centro' in c.lower() or 'costo' in c.lower()]
        nota_cols = [c for c in df_caja.columns if 'nota' in c.lower()]
        
        desc_col = desc_cols[0] if desc_cols else df_caja.columns[1]
        cc_col = cc_cols[0] if cc_cols else 'Centro de costos'
        nota_col = nota_cols[0] if nota_cols else 'Notas sobre el movimiento'
        
        if cc_col not in df_caja.columns: df_caja[cc_col] = ''
        if nota_col not in df_caja.columns: df_caja[nota_col] = ''
        
        df_caja['CC_Limpio'] = df_caja[cc_col].astype(str).str.strip().str.lower()
        df_caja['Nota_Limpia'] = df_caja[nota_col].astype(str).str.strip().str.lower()
        df_caja['Desc_Limpia'] = df_caja[desc_col].astype(str).str.strip()
        
        # Clasificación Manual Actual (Próximo paso: El Diccionario)
        def clasificar(row):
            cc_manual = str(row['CC_Limpio']).strip()
            nota_manual = str(row['Nota_Limpia']).strip()
            desc = str(row['Desc_Limpia']).upper()
            
            if cc_manual not in ['', 'nan', 'none']: return cc_manual.upper()
            if any(x in desc for x in ['GOOGLE ADS', 'META ADS', 'FACEBOOK ADS', 'ADS']):
                return f"PAUTA: {nota_manual.upper()}" if nota_manual not in ['', 'nan'] else "ALERTA: PAUTA SIN CLIENTE"
            if 'WORKSPACE' in desc or 'GOOGLE *' in desc: return 'SOFTWARE (INTERNO)'
            if 'CANVA' in desc: return 'SOFTWARE (INTERNO)'
            if '4X1000' in desc or 'GOBIERNO' in desc: return 'IMPUESTOS BANCARIOS'
            if 'DIAN' in desc or 'IMPUESTO' in desc: return 'IMPUESTOS DIAN'
            if 'ARRIENDO' in desc: return 'OFICINA'
            if 'NEQUI' in desc and ('CONTADORA' in desc or 'CONTABIL' in desc): return 'HONORARIOS'
            if 'INTERBANC' in desc: return 'INGRESOS CLIENTES'
            if any(x in desc for x in ['UBER', 'DIDI', 'CABIFY']): return 'POR CLASIFICAR - TRANSPORTE'
            if any(x in desc for x in ['RESTAURANTE', 'ALMUERZO', 'CAFE', 'D1', 'ATELIER', 'SAN GIORGI']): return 'POR CLASIFICAR - ALIMENTACIÓN'
            return 'POR CLASIFICAR - GENERAL' if row['Monto_Neto'] < 0 else 'OTROS INGRESOS'
            
        df_caja['Centro_Costos_BI'] = df_caja.apply(clasificar, axis=1)
        df_caja['Ingreso ($)'] = df_caja['Monto_Neto'].apply(lambda x: x if x > 0 else 0)
        df_caja['Egreso ($)'] = df_caja['Monto_Neto'].apply(lambda x: abs(x) if x < 0 else 0)
        
        return df_caja.sort_values(by='Fecha del movimiento', ascending=True)
        
    except Exception as e:
        st.error(f"Error técnico profundo: {e}")
        return pd.DataFrame()

# 4. Construcción de Interfaz Visual
if st.button("🔄 Actualizar Datos Financieros"):
    st.cache_data.clear()

with st.spinner("Ensamblando meses correctamente..."):
    df_caja = load_financial_data()

if not df_caja.empty:
    c1, c2, c3 = st.columns(3)
    cuenta_sel = c1.selectbox("Filtrar Cuenta:", ["Consolidado (Ambas)", "Bancolombia", "BBVA"])
    mes_sel = c2.selectbox("Filtrar por Mes:", ["Todos"] + sorted(list(df_caja['Mes-Año'].unique()), reverse=True))
    cc_sel = c3.selectbox("Filtrar por Centro Costos:", ["Todos"] + sorted(list(df_caja['Centro_Costos_BI'].unique())))
    
    df_f = df_caja.copy()
    if cuenta_sel != "Consolidado (Ambas)": df_f = df_f[df_f['Cuenta'] == cuenta_sel]
    if mes_sel != "Todos": df_f = df_f[df_f['Mes-Año'] == mes_sel]
    if cc_sel != "Todos": df_f = df_f[df_f['Centro_Costos_BI'] == cc_sel]
    
    st.subheader("📊 Resumen de Flujo de Caja")
    k1, k2, k3, k4 = st.columns(4)
    
    df_ban_c = df_caja[df_caja['Cuenta'] == 'Bancolombia']
    df_bbva_c = df_caja[df_caja['Cuenta'] == 'BBVA']
    
    s_ban = df_ban_c['Saldo_Neto'].iloc[-1] if not df_ban_c.empty else 0
    s_bbva = df_bbva_c['Saldo_Neto'].iloc[-1] if not df_bbva_c.empty else 0
    
    if cuenta_sel == "Consolidado (Ambas)":
        saldo_dispo = s_ban + s_bbva
    else:
        saldo_dispo = df_f['Saldo_Neto'].iloc[-1] if not df_f.empty else 0

    k1.metric("Saldo Disponible Total", f"${saldo_dispo:,.2f}")
    k2.metric("Ingresos Periodo", f"${df_f['Ingreso ($)'].sum():,.2f}")
    k3.metric("Egresos Periodo", f"${df_f['Egreso ($)'].sum():,.2f}")
    flujo = df_f['Ingreso ($)'].sum() - df_f['Egreso ($)'].sum()
    k4.metric("Flujo Neto Caja", f"${flujo:,.2f}", delta=f"${flujo:,.2f}")

    st.subheader("🚨 Auditoría Contable Automatizada")
    alertas = df_f[df_f['Centro_Costos_BI'].str.contains('POR CLASIFICAR|ALERTA')]
    
    if not alertas.empty:
        st.error(f"🔴 **Semáforo de Higiene Contable:** Se detectaron **{len(alertas)} transacciones** pendientes. Agrégales su nota en Google Sheets:")
        st.dataframe(alertas[['Fecha_Texto', 'Desc_Limpia', 'Cuenta', 'Monto_Neto', 'Centro_Costos_BI']], use_container_width=True)
    else:
        st.success("🟢 **Semáforo de Higiene Contable:** ¡Caja impecable! No hay gastos colados ni pautas sin asignar.")

    gasto_4x1000 = df_f[df_f['Centro_Costos_BI'] == 'IMPUESTOS BANCARIOS']['Egreso ($)'].sum()
    if gasto_4x1000 > 0:
        st.info(f"💸 **Fuga Gravamen Bancario:** El cobro del 4x1000 y comisiones bancarias suman **${gasto_4x1000:,.2f}** en este recorte.")

    with st.expander("👀 Ver Libro de Caja Detallado (Datos Unificados)"):
        st.dataframe(df_f[['Fecha_Texto', 'Desc_Limpia', 'Cuenta', 'Monto_Neto', 'Centro_Costos_BI', 'Saldo_Neto']], use_container_width=True)
