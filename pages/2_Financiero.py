import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Configuración de la página
st.set_page_config(page_title="goBIG Financiero v2.0", page_icon="💰", layout="wide")

with st.sidebar:
    st.image("goBIG_logo.jpg", width=200)
    st.markdown("---")
    st.caption("v2.0 - Consola de Control Financiero Integral")
    st.info("🧠 **Novedad:** Diccionario de auto-clasificación, nómina dinámica y proyección de costos fijos por periodo.")

st.title("💰 Consola Financiera y Control de Caja")
st.markdown("Consolidación bancaria, auto-clasificación de gastos y auditoría de flujo neto.")
st.markdown("---")

# 2. Funciones Utilitarias
def clean_currency_global(value):
    if pd.isna(value) or str(value).strip() in ['', 'nan', 'None', '<NA>']: return 0.0
    val_str = str(value).replace('$', '').replace(' ', '').strip()
    if ',' in val_str and '.' in val_str:
        if val_str.find('.') < val_str.find(','): 
            val_str = val_str.replace('.', '').replace(',', '.')
        else: 
            val_str = val_str.replace(',', '')
    elif ',' in val_str: 
        if len(val_str.split(',')[-1]) <= 2: val_str = val_str.replace(',', '.')
        else: val_str = val_str.replace(',', '')
    try: return float(val_str)
    except ValueError: return 0.0

MESES_NUM = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 
             'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}

# 3. Motor de Extracción Multidocumento
@st.cache_data(ttl=600)
def load_all_financials():
    try:
        url_doc = "https://docs.google.com/spreadsheets/d/1ldntONNpWFgXPcF8VINDKzNAhG_vGMdzGEOESM3aLNU/export?format=xlsx"
        xls = pd.ExcelFile(url_doc)
        sheet_names = xls.sheet_names
        
        # Identificar pestañas
        s_banco = [s for s in sheet_names if s.startswith('01_')]
        s_bbva = [s for s in sheet_names if s.startswith('001')]
        s_recursos = [s for s in sheet_names if s.startswith('04_')]
        s_fijos = [s for s in sheet_names if s.startswith('05_')]
        s_dicc = [s for s in sheet_names if s.startswith('06_')]

        # --- A. DICCIONARIO DE CLASIFICACIÓN AVANZADO ---
        reglas_procesadas = []
        if s_dicc:
            df_d = pd.read_excel(xls, sheet_name=s_dicc[0])
            if len(df_d.columns) >= 2:
                df_d = df_d.dropna(subset=[df_d.columns[0]])
                for _, row in df_d.iterrows():
                    patron = str(row.iloc[0]).upper().strip()
                    cc = str(row.iloc[1]).upper().strip()
                    if patron not in ['NAN', 'NONE', '<NA>', '']:
                        reglas_procesadas.append((patron, cc))
                
                # Auto-priorización
                reglas_procesadas.sort(key=lambda x: (x[0].count('+') > 0, len(x[0])), reverse=True)

        # --- B. BANCOS (FLUJO REAL) ---
        if not s_banco: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        df_bancolombia = pd.read_excel(xls, sheet_name=s_banco[0], header=0)
        df_bancolombia['Cuenta'] = 'Bancolombia'
        
        if s_bbva:
            df_bbva_raw = pd.read_excel(xls, sheet_name=s_bbva[0], header=0)
            df_bbva = df_bbva_raw.copy() if not df_bbva_raw.empty else pd.DataFrame(columns=df_bancolombia.columns)
        else:
            df_bbva = pd.DataFrame(columns=df_bancolombia.columns)
            
        df_bbva['Cuenta'] = 'BBVA'
        df_caja = pd.concat([df_bancolombia, df_bbva], ignore_index=True)
        df_caja.columns = df_caja.columns.str.replace(r'\n', ' ', regex=True).str.strip()
        
        c_monto = next((c for c in df_caja.columns if 'monto' in c.lower()), None)
        c_saldo = next((c for c in df_caja.columns if 'saldo' in c.lower()), None)
        c_fecha = next((c for c in df_caja.columns if 'fecha' in c.lower()), None)
        c_ano = next((c for c in df_caja.columns if 'año' in c.lower() or 'ano' in c.lower() or 'year' in c.lower()), None)
        
        df_caja['Monto_Neto'] = df_caja[c_monto].apply(clean_currency_global)
        df_caja['Saldo_Neto'] = df_caja[c_saldo].apply(clean_currency_global)
        
        # --- DETECTIVE DE FECHAS (CON BYPASS PARA ENERO) ---
        def fix_strict_date(row):
            if not c_fecha: return pd.NaT
            val = row[c_fecha]
            
            # 1. BYPASS: Si Pandas ya lo convirtió a un objeto de tiempo nativo (Ej: Enero)
            if isinstance(val, (pd.Timestamp, datetime)):
                return val
                
            d = str(val).strip()
            if d.lower() in ['nan', 'none', 'nat', '<na>', '']: return pd.NaT
            
            # 2. BYPASS: Si es un texto que ya tiene formato de base de datos 'YYYY-MM-DD'
            if len(d) >= 10 and d[4] == '-' and d[7] == '-':
                try:
                    return pd.to_datetime(d).normalize()
                except:
                    pass
            
            # 3. MODO DETECTIVE: Para formatos raros (Ej: 13/03)
            d = d.replace('-', '/')
            
            y = str(row[c_ano]).strip() if c_ano else "2026"
            if '.' in y: y = y.split('.')[0]
            if not y.isdigit() or len(y) != 4: y = "2026"
            
            parts = d.split('/')
            
            if len(parts) == 2:
                try:
                    p1, p2 = int(parts[0]), int(parts[1])
                    return f"{y}-{p2:02d}-{p1:02d}"
                except ValueError:
                    return pd.NaT
            elif len(parts) == 3:
                try:
                    # Usamos .split()[0] por si el banco pegó la hora "13 00:00:00"
                    p1 = int(parts[0].split()[0])
                    p2 = int(parts[1].split()[0])
                    if p1 == 1:
                        month, day = 1, p2
                    else:
                        day, month = p1, p2
                    return f"{y}-{month:02d}-{day:02d}"
                except ValueError:
                    return pd.NaT
            return pd.NaT

        df_caja['Fecha_OK'] = pd.to_datetime(df_caja.apply(fix_strict_date, axis=1), errors='coerce')
        df_caja = df_caja.dropna(subset=['Fecha_OK'])
        
        df_caja['Mes-Año'] = df_caja['Fecha_OK'].dt.strftime('%Y-%m')
        df_caja['Mes_Num'] = df_caja['Fecha_OK'].dt.month
        df_caja['Año_Num'] = df_caja['Fecha_OK'].dt.year
        
        c_desc = next((c for c in df_caja.columns if 'descrip' in c.lower() or 'detalle' in c.lower()), df_caja.columns[1])
        c_cc = next((c for c in df_caja.columns if 'centro' in c.lower() or 'costo' in c.lower()), 'Centro de costos')
        if c_cc not in df_caja.columns: df_caja[c_cc] = ''
        
        df_caja['Desc_Limpia'] = df_caja[c_desc].astype(str).str.strip().str.upper()
        
        # --- SELLADO DE VACÍOS (Filtro anti-fantasmas) ---
        df_caja['CC_Manual'] = df_caja[c_cc].fillna('').astype(str).str.strip().str.upper()
        df_caja.loc[df_caja['CC_Manual'].isin(['NAN', 'NONE', '<NA>', 'NULL', 'NAT']), 'CC_Manual'] = ''

        # --- MOTOR DE CLASIFICACIÓN CON SUPERPODERES Y DETECCIÓN DE COMPRAS ---
        def auto_clasificar(row):
            desc = row['Desc_Limpia']
            cc_man = row['CC_Manual']
            
            # 1. Diccionario
            for patron, cc_auto in reglas_procesadas:
                match = False
                if '+' in patron:
                    partes = [p.strip() for p in patron.split('+')]
                    cumple_todas = True
                    for parte in partes:
                        if '|' in parte:
                            subpartes = [sp.strip() for sp in parte.split('|')]
                            if not any(sp in desc for sp in subpartes if sp):
                                cumple_todas = False
                                break
                        else:
                            if parte not in desc:
                                cumple_todas = False
                                break
                    if cumple_todas: match = True
                elif '|' in patron:
                    partes = [p.strip() for p in patron.split('|')]
                    if any(p in desc for p in partes if p): match = True
                else:
                    if patron in desc: match = True
                
                if match: return cc_auto
                    
            # 2. Respetar Input Manual
            if cc_man != '': return cc_man
            
            # 3. Reglas por defecto y Forzado de "COMPRAS"
            if 'ARRIENDO' in desc: return 'OFICINA'
            if 'COMPRA' in desc: return 'POR CLASIFICAR - COMPRAS'
            
            return 'POR CLASIFICAR - GENERAL' if row['Monto_Neto'] < 0 else 'OTROS INGRESOS'

        df_caja['Centro_Costos_BI'] = df_caja.apply(auto_clasificar, axis=1)
        df_caja['Ingreso ($)'] = df_caja['Monto_Neto'].apply(lambda x: x if x > 0 else 0)
        df_caja['Egreso ($)'] = df_caja['Monto_Neto'].apply(lambda x: abs(x) if x < 0 else 0)

        # --- C. NÓMINA DINÁMICA (04) ---
        df_nomina = pd.DataFrame()
        if s_recursos:
            df_n = pd.read_excel(xls, sheet_name=s_recursos[0], header=0)
            c_inicio = next((c for c in df_n.columns if 'inicio' in c.lower()), None)
            c_fin = next((c for c in df_n.columns if 'fin' in c.lower() or 'retiro' in c.lower()), None)
            c_costo = next((c for c in df_n.columns if 'costo total' in c.lower()), df_n.columns[17])
            
            if c_inicio:
                df_n['Fecha_Inicio'] = pd.to_datetime(df_n[c_inicio], dayfirst=True, errors='coerce')
                df_n['Fecha_Fin'] = pd.to_datetime(df_n[c_fin], dayfirst=True, errors='coerce') if c_fin else pd.NaT
                df_n['Costo_Mensual'] = df_n[c_costo].apply(clean_currency_global)
                df_nomina = df_n[['COLABORADOR', 'Fecha_Inicio', 'Fecha_Fin', 'Costo_Mensual']].copy()

        # --- D. COSTOS FIJOS HISTÓRICOS (05) ---
        df_fijos = pd.DataFrame()
        if s_fijos:
            df_f = pd.read_excel(xls, sheet_name=s_fijos[0], header=0)
            c_m = next((c for c in df_f.columns if 'monto' in c.lower()), None)
            c_mi = next((c for c in df_f.columns if 'mes inicio' in c.lower()), None)
            c_mf = next((c for c in df_f.columns if 'mes fin' in c.lower()), None)
            
            if c_m and c_mi:
                df_f['Monto_Limpio'] = df_f[c_m].apply(clean_currency_global)
                df_f['M_Inicio_Num'] = df_f[c_mi].astype(str).str.strip().str.lower().map(MESES_NUM)
                df_f['M_Fin_Num'] = df_f[c_mf].astype(str).str.strip().str.lower().map(MESES_NUM) if c_mf else None
                df_fijos = df_f.copy()

        return df_caja, df_nomina, df_fijos
        
    except Exception as e:
        st.error(f"Error técnico profundo: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# 4. Construcción de Interfaz
if st.button("🔄 Actualizar Datos y Diccionario"):
    st.cache_data.clear()

with st.spinner("Conectando con el Diccionario de Datos y Extractos..."):
    df_caja, df_nomina, df_fijos = load_all_financials()

if not df_caja.empty:
    st.subheader("🔍 Filtros de Auditoría")
    c1, c2 = st.columns(2)
    cuenta_sel = c1.selectbox("Filtrar Cuenta:", ["Consolidado (Ambas)", "Bancolombia", "BBVA"])
    
    lista_meses = sorted(list(df_caja['Mes-Año'].unique()), reverse=True)
    mes_sel = c2.selectbox("Filtrar por Mes:", lista_meses)
    
    año_sel = int(mes_sel.split('-')[0])
    mes_num_sel = int(mes_sel.split('-')[1])
    fecha_corte_mes = pd.to_datetime(f"{año_sel}-{mes_num_sel}-01") + pd.offsets.MonthEnd(0)
    fecha_inicio_mes = pd.to_datetime(f"{año_sel}-{mes_num_sel}-01")

    df_f = df_caja[df_caja['Mes-Año'] == mes_sel].copy()
    if cuenta_sel != "Consolidado (Ambas)": df_f = df_f[df_f['Cuenta'] == cuenta_sel]
    
    st.markdown("---")
    st.subheader("🏦 Realidad Bancaria (Flujo de Caja Real)")
    k1, k2, k3 = st.columns(3)
    
    ingresos = df_f['Ingreso ($)'].sum()
    egresos = df_f['Egreso ($)'].sum()
    flujo = ingresos - egresos
    
    k1.metric("Ingresos (Banco)", f"${ingresos:,.0f}")
    k2.metric("Egresos (Banco)", f"${egresos:,.0f}")
    k3.metric("Flujo Neto Mes", f"${flujo:,.0f}", delta=f"${flujo:,.0f}")
    
    if egresos > 0:
        st.write("**¿En qué se fue el dinero este mes? (Desglose de Egresos Reales)**")
        df_egresos = df_f[df_f['Egreso ($)'] > 0].groupby('Centro_Costos_BI')['Egreso ($)'].sum().reset_index()
        df_egresos_sorted = df_egresos.sort_values('Egreso ($)', ascending=True)
        
        fig_egresos = px.bar(df_egresos_sorted, 
                             x='Egreso ($)', y='Centro_Costos_BI', orientation='h', 
                             text='Egreso ($)',
                             color='Egreso ($)', color_continuous_scale='Reds')
                             
        fig_egresos.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        fig_egresos.update_layout(margin=dict(t=10, l=10, r=10, b=10), coloraxis_showscale=False, height=400)
        st.plotly_chart(fig_egresos, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Auditoría Teórica (Lo que debió costar vs Banco)")
    
    t1, t2 = st.columns(2)
    
    with t1:
        if not df_nomina.empty:
            activos = df_nomina[
                (df_nomina['Fecha_Inicio'] <= fecha_corte_mes) & 
                (df_nomina['Fecha_Fin'].isna() | (df_nomina['Fecha_Fin'] >= fecha_inicio_mes))
            ]
            total_nomina = activos['Costo_Mensual'].sum()
            st.metric("Nómina Teórica del Mes (Activos)", f"${total_nomina:,.0f}")
            with st.expander("Ver personas activas este mes"):
                df_activos_disp = activos[['COLABORADOR', 'Costo_Mensual']].copy()
                df_activos_disp['Costo_Mensual'] = df_activos_disp['Costo_Mensual'].apply(lambda x: f"${x:,.0f}")
                st.dataframe(df_activos_disp, hide_index=True, use_container_width=True)
                
    with t2:
        if not df_fijos.empty:
            fijos_activos = df_fijos[
                (df_fijos['M_Inicio_Num'] <= mes_num_sel) & 
                (df_fijos['M_Fin_Num'].isna() | (df_fijos['M_Fin_Num'] >= mes_num_sel))
            ]
            fijos_activos = fijos_activos[~fijos_activos[fijos_activos.columns[0]].astype(str).str.contains("Nómina", case=False, na=False)]
            
            total_fijos = fijos_activos['Monto_Limpio'].sum()
            st.metric("Costos Fijos Operativos (Teóricos)", f"${total_fijos:,.0f}")
            with st.expander("Ver desglose de costos fijos de este mes"):
                df_fijos_disp = fijos_activos[[fijos_activos.columns[0], 'Monto_Limpio']].copy()
                df_fijos_disp['Monto_Limpio'] = df_fijos_disp['Monto_Limpio'].apply(lambda x: f"${x:,.0f}")
                st.dataframe(df_fijos_disp, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.subheader("🚨 Semáforo de Auto-Clasificación (Auditoría)")
    alertas = df_f[df_f['Centro_Costos_BI'].str.contains('POR CLASIFICAR', na=False)]
    
    if not alertas.empty:
        st.error(f"🔴 Se detectaron **{len(alertas)} transacciones** sin regla en el Diccionario. Agrégalas a tu pestaña '06_Diccionario_Clasificacion':")
        alertas_disp = alertas[['Fecha_OK', 'Desc_Limpia', 'Monto_Neto', 'Centro_Costos_BI']].copy()
        alertas_disp['Fecha'] = alertas_disp['Fecha_OK'].dt.strftime('%Y-%m-%d')
        alertas_disp['Monto'] = alertas_disp['Monto_Neto'].apply(lambda x: f"${x:,.0f}")
        st.dataframe(alertas_disp[['Fecha', 'Desc_Limpia', 'Monto', 'Centro_Costos_BI']], hide_index=True, use_container_width=True)
    else:
        st.success("🟢 ¡Excelente! El 100% de los gastos de este mes fueron clasificados exitosamente por el Diccionario y tu ingreso manual.")
        
    st.markdown("---")
    st.subheader("🔍 Tabla de Auditoría General")
    with st.expander("Ver el detalle de todas las transacciones del mes"):
        df_todas = df_f[['Fecha_OK', 'Desc_Limpia', 'Egreso ($)', 'Ingreso ($)', 'Centro_Costos_BI']].copy()
        df_todas['Fecha'] = df_todas['Fecha_OK'].dt.strftime('%Y-%m-%d')
        df_todas['Egreso'] = df_todas['Egreso ($)'].apply(lambda x: f"${x:,.0f}" if x > 0 else "-")
        df_todas['Ingreso'] = df_todas['Ingreso ($)'].apply(lambda x: f"${x:,.0f}" if x > 0 else "-")
        st.dataframe(df_todas[['Fecha', 'Desc_Limpia', 'Egreso', 'Ingreso', 'Centro_Costos_BI']], hide_index=True, use_container_width=True)
            
else:
    st.warning("Sin datos para mostrar. Verifique las fuentes en Google Sheets.")
