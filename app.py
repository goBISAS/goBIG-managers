import streamlit as st
import streamlit_authenticator as stauth

st.set_page_config(page_title="goBIG Managers", page_icon="📈", layout="wide")

# 1. Cargar configuración de seguridad desde los secretos
credenciales = dict(st.secrets["credentials"])
cookie_config = dict(st.secrets["cookie"])

# 2. Inicializar el Autenticador (Sintaxis moderna)
authenticator = stauth.Authenticate(
    credentials=credenciales,
    cookie_name=cookie_config["name"],
    cookie_key=cookie_config["key"],
    cookie_expiry_days=cookie_config["expiry_days"]
)

# 3. Mostrar el formulario de Login
authenticator.login()

# 4. Lógica de acceso basada en la sesión
if st.session_state.get("authentication_status") is False:
    st.error("🔴 Usuario o contraseña incorrectos")
elif st.session_state.get("authentication_status") is None:
    st.warning("🟡 Por favor ingresa tu usuario y contraseña para acceder.")
elif st.session_state.get("authentication_status"):
    # --- SI EL LOGIN ES EXITOSO, MUESTRA ESTO ---
    with st.sidebar:
        st.write(f"Bienvenido/a, **{st.session_state['name']}**")
        authenticator.logout("Cerrar Sesión", "sidebar")
        st.markdown("---")
        
    st.title("🚀 Bienvenido a la Consola de goBIG Managers")
    st.markdown("""
    Has accedido exitosamente al entorno seguro. 
    Por favor, selecciona un módulo en la barra lateral izquierda para comenzar:
    
    *   **📈 Operativo:** Analítica comercial, leads y conversiones.
    *   **💰 Financiero:** Consolidación bancaria y flujo de caja real vs teórico.
    """)
    st.success(f"🟢 Sesión iniciada correctamente. Tu dispositivo será recordado por {cookie_config['expiry_days']} días.")
