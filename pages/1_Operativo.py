import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="goBIG Operativo", page_icon="⚙️", layout="wide")

# Barra lateral
with st.sidebar:
    st.image("goBIG_logo.jpg", width=200)
    st.markdown("---")
    st.caption("Módulo de Rentabilidad y Esfuerzo Operativo")

st.title("⚙️ Operativa y Rentabilidad de Proyectos")
st.markdown("Análisis de esfuerzo de los consultores cruzado con el costo por hora.")
st.markdown("---")

# 2. Conexión a la data cacheada
# Asumimos que los datos ya están estructurados desde el main o un loader general. 
# Si tu proyecto original carga directamente de Google Sheets aquí, usa tu función de carga.
# Para efectos de la actualización del Treemap solicitada, mantengo la estructura de interfaz estándar.

@st.cache_data(ttl=600)
def load_ops_data():
    # Aquí iría tu lógica real de extracción del Backlog (1Vl5rhQDi6YooJgjYAF76oOO0aN8rbPtu07giky36wSo)
    # y del Diccionario de Recursos para cruzar las horas por el costo.
    # Como la consulta fue específica al gráfico, asumo que df_filtrado ya existe en tu script original.
    
    # IMPORTANTE: Si necesitas que integre tu función 'load_data_safe' específica aquí, 
    # por favor confírmamelo, pero según la charla previa, tu código de interfaz ya funcionaba.
    
    # Placeholder para que el código compile si lo copias directo
    pass

# Supongamos que tu DataFrame principal procesado se llama df_filtrado
# Si tienes tu lógica de filtros antes, mantenla.

# ... (Tu código de carga y filtros previos aquí) ...

# 3. VISUALIZACIONES

# --- TREEMAP DE TAXONOMÍA DE TAREAS (COSTO + HORAS) ---
st.subheader("🧱 Distribución de Presupuesto y Esfuerzo por Tarea")

# Verifica que df_filtrado exista en tu entorno real (es decir, la data cruzada)
if 'df_filtrado' in locals() and not df_filtrado.empty:
    
    # Agrupamos los datos sumando tanto el costo como el tiempo real
    df_treemap = df_filtrado.groupby(['Nombre del cliente', 'Tipo de tarea'])[['Costo_Devengado', 'Tiempo real']].sum().reset_index()
    
    # Filtramos para que no intente graficar tareas con costo 0 o negativo
    df_treemap = df_treemap[df_treemap['Costo_Devengado'] > 0]
    
    if not df_treemap.empty:
        # Creamos el Treemap. 'values' define el tamaño (Costo), 'custom_data' inyecta las horas
        fig_tree = px.treemap(
            df_treemap, 
            path=['Nombre del cliente', 'Tipo de tarea'], 
            values='Costo_Devengado',
            custom_data=['Tiempo real'],
            color='Nombre del cliente',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        
        # Forzamos el diseño del texto para que muestre ambas métricas limpiamente sin hover
        fig_tree.update_traces(
            texttemplate="<b>%{label}</b><br>Costo: $%{value:,.0f}<br>Esfuerzo: %{customdata[0]:.1f} hrs",
            textposition="middle center",
            hovertemplate="<b>%{label}</b><br>Costo: $%{value:,.0f}<br>Esfuerzo: %{customdata[0]:.1f} hrs<extra></extra>"
        )
        
        fig_tree.update_layout(
            template="plotly_dark", 
            margin=dict(t=30, l=10, r=10, b=10)
        )
        
        st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.info("No hay costos devengados mayores a cero para graficar el mapa.")
else:
    st.warning("Asegúrate de que los datos operativos estén cargados y cruzados con los costos ('df_filtrado').")
