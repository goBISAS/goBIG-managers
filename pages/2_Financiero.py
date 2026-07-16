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
    if pd.isna(value) or str(value).strip() in ['', 'nan', 'None']: return 0.0
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

        # --- A. DICCIONARIO DE CLASIFICACIÓN AVANZADO (ORDEN INDIFERENTE) ---
        reglas_procesadas = []
        if s_dicc:
            df_d = pd.read_excel(xls, sheet_name=s_dicc[0])
            if len(df_d.columns) >= 2:
                df_d = df_d.dropna(subset=[df_d.columns[0]])
                for _, row in df_d.iterrows():
                    patron = str(row.iloc[0]).upper().strip()
                    cc = str(row.iloc[1]).upper().strip()
                    if patron != 'NAN' and patron != '':
                        reglas_procesadas.append((patron, cc))
                
                # AUTO-PRIORIZACIÓN: Ordena las reglas automáticamente de la más específica a la más general.
                # Prioriza patrones que tengan un '+' (and) y luego por longitud de caracteres (frases más largas primero).
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
        
        # --- DETECTIVE DE FECHAS INTELIGENTE ---
        def fix_strict_date(row):
            if not c_fecha: return pd.NaT
            d = str(row[c_fecha]).strip().replace('-', '/')
            if d.lower() in ['nan', 'none', 'nat', '']: return pd.NaT
            
            # Obtener el año de tu columna "Año del movimiento"
            y = str(row[c_ano]).strip() if c_ano else "2026"
            if '.' in y: y = y.split('.')[0]
            if not y.isdigit() or len(y) != 4: y = "2026"
            
            parts = d.split('/')
            
            # Caso de 2 partes (ej: "13/03") -> Siempre es Día/Mes
            if len(parts) == 2:
                try:
                    p1, p2 = int(parts[0]), int(parts[1])
                    return f"{y}-{p2:02d}-{p1:02d}"
                except ValueError:
                    return pd.NaT
            
            # Caso de 3 partes (ej: "1/9/2026" o "11/3/2026")
            elif len(parts) == 3:
                try:
                    p1, p2 = int(parts[0]), int(parts[1])
                    
                    if p1 == 1:
                        month = 1
                        day = p2
                    else:
                        day = p1
                        month = p2
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
        df_caja['CC_Manual'] = df_caja[c_cc].astype(str).str.strip().str.upper()

        # MOTOR DE CLASIFICACIÓN CON SUPERPODERES Y LÓGICA BOOLEANA
        def auto_clasificar(row):
            desc = row['Desc_Limpia']
            cc_man = row['CC_Manual']
            
            # 1. Buscar en el listado de reglas procesadas y auto-ordenadas por prioridad
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
                    if cumple_todas:
                        match = True
                elif '|' in patron:
                    partes = [p.strip() for p in patron.split('|')]
                    if any(p in desc for p in partes if p):
                        match = True
                else:
                    if patron in desc:
                        match = True
                
                if match:
                    return cc_auto
                    
            if cc_man not in ['', 'NAN', 'NONE']: return cc_man
            if 'ARRIENDO' in desc: return 'OFICINA'
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
    
    # Extraer variables del mes seleccionado para cálculos teóricos
    año_sel = int(mes_sel.split('-')[0])
    mes_num_sel = int(mes_sel.split('-')[1])
    fecha_corte_mes = pd.to_datetime(f"{año_sel}-{mes_num_sel}-01") + pd.offsets.MonthEnd(0)
    fecha_inicio_mes = pd.to_datetime(f"{año_sel}-{mes_num_sel}-01")

    # Filtro Bancario
    df_f = df_caja[df_caja['Mes-Año'] == mes_sel].copy()
    if cuenta_sel != "Consolidado (Ambas)": df_f = df_f[df_f['Cuenta'] == cuenta_sel]
    
    # KPIs Bancarios
    st.markdown("---")
    st.subheader("🏦 Realidad Bancaria (Flujo de Caja Real)")
    k1, k2, k3 = st.columns(3)
    
    ingresos = df_f['Ingreso ($)'].sum()
    egresos = df_f['Egreso ($)'].sum()
    flujo = ingresos - egresos
    
    k1.metric("Ingresos (Banco)", f"${ingresos:,.0f}")
    k2.metric("Egresos (Banco)", f"${egresos:,.0f}")
    k3.metric("Flujo Neto Mes", f"${flujo:,.0f}", delta=f"${flujo:,.0f}")
    
    # --- GRÁFICO CORREGIDO: Formateo Nativo de Plotly ---
    if egresos > 0:
        st.write("**¿En qué se fue el dinero este mes? (Desglose de Egresos Reales)**")
        df_egresos = df_f[df_f['Egreso ($)'] > 0].groupby('Centro_Costos_BI')['Egreso ($)'].sum().reset_index()
        
        # Ordenamos los datos de menor a mayor antes de pasarlos a Plotly
        df_egresos_sorted = df_egresos.sort_values('Egreso ($)', ascending=True)
        
        fig_egresos = px.bar(df_egresos_sorted, 
                             x='Egreso ($)', y='Centro_Costos_BI', orientation='h', 
                             text='Egreso ($)', # Aquí usamos la columna nativa
                             color='Egreso ($)', color_continuous_scale='Reds')
                             
        # Le aplicamos el formato de moneda directamente en el texttemplate para que nunca se desalinee
        fig_egresos.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        fig_egresos.update_layout(margin=dict(t=10, l=10, r=10, b=10), coloraxis_showscale=False, height=400)
        st.plotly_chart(fig_egresos, use_container_width=True)

    # Proyección Teórica
    st.markdown("---")
    st.subheader("📋 Auditoría Teórica (Lo que debió costar vs Banco)")
    
    t1, t2 = st.columns(2)
    
    with t1:
        # Cálculo Nómina Dinámica
        if not df_nomina.empty:
            activos = df_nomina[
                (df_nomina['Fecha_Inicio'] <= fecha_corte_mes) & 
                (df_nomina['Fecha_Fin'].isna() | (df_nomina['Fecha_Fin'] >= fecha_inicio_mes))
            ]
            total_nomina = activos['Costo_Mensual'].sum()
            st.metric("Nómina Teórica del Mes (Activos)", f"${total_nomina:,.0f}")
            with st.expander("Ver personas activas este mes"):
                st.dataframe(activos[['COLABORADOR', 'Costo_Mensual']], hide_index=True)
                
    with t2:
        # Cálculo Costos Fijos Históricos
        if not df_fijos.empty:
            fijos_activos = df_fijos[
                (df_fijos['M_Inicio_Num'] <= mes_num_sel) & 
                (df_fijos['M_Fin_Num'].isna() | (df_fijos['M_Fin_Num'] >= mes_num_sel))
            ]
            fijos_activos = fijos_activos[~fijos_activos[fijos_activos.columns[0]].astype(str).str.contains("Nómina", case=False, na=False)]
            
            total_fijos = fijos_activos['Monto_Limpio'].sum()
            st.metric("Costos Fijos Operativos (Teóricos)", f"${total_fijos:,.0f}")
            with st.expander("Ver desglose de costos fijos de este mes"):
                st.dataframe(fijos_activos[[fijos_activos.columns[0], 'Monto_Limpio']], hide_index=True)

    st.markdown("---")
    st.subheader("🚨 Semáforo de Auto-Clasificación (Auditoría)")
    alertas = df_f[df_f['Centro_Costos_BI'].str.contains('POR CLASIFICAR', na=False)]
    
    if not alertas.empty:
        st.error(f"🔴 Se detectaron **{len(alertas)} transacciones** sin regla en el Diccionario. Agrégalas a tu pestaña '06_Diccionario_Clasificacion':")
        st.dataframe(alertas[['Fecha_OK', 'Desc_Limpia', 'Monto_Neto', 'Centro_Costos_BI']], use_container_width=True)
    else:
        st.success("🟢 ¡Excelente! El 100% de los gastos de este mes fueron clasificados exitosamente por el Diccionario y tu ingreso manual.")
            
else:
    st.warning("Sin datos para mostrar. Verifique las fuentes en Google Sheets.")
