import streamlit as st

# 1. Configuración principal de la aplicación (Debe ir siempre al inicio)
st.set_page_config(
    page_title="goBIG - Dashboard Directivo",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Diseño de la página de inicio
st.title("🏢 goBIG - Portal Directivo")
st.markdown("---")

st.write("Bienvenido al panel de control central en tiempo real.")
st.write("👈 **Por favor, selecciona el área que deseas analizar en el menú lateral.**")

# 3. Mensaje de confirmación
st.info("✅ Entorno principal configurado correctamente.")
