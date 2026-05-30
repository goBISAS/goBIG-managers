import streamlit as st

# Configuración de la página (opcional pero recomendada para cada hoja)
st.set_page_config(page_title="Operativo", page_icon="⚙️", layout="wide")

st.title("⚙️ Dashboard Operativo y de Costos")
st.markdown("Visualización en tiempo real del Backlog cruzado con Costos de Nómina.")

st.markdown("---")

# Aquí creamos el espacio "reservado" donde irán los filtros y KPIs en el siguiente paso
st.subheader("🎛️ Filtros y KPIs (Próximamente)")
st.info("Conectando con Google Sheets para extraer horas reales y estimadas...")

# Espacio reservado para las gráficas
col1, col2 = st.columns(2)

with col1:
    st.write("📊 **Espacio para Treemap de Clientes**")
    
with col2:
    st.write("📈 **Espacio para Gráfico de Desempeño**")
