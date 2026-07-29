import streamlit as st
import streamlit_authenticator as stauth

st.set_page_config(page_title="goBIG Managers", page_icon="📈", layout="wide")

# 1. Cargar configuración de seguridad desde los secretos
credenciales = dict(st.secrets["credentials"])
cookie_config = dict(st.secrets["cookie"])
preauth = dict(st.secrets["preauthorized"])

# 2. Inicializar el Autenticador
authenticator = stauth.Authenticate(
    credenciales,
    cookie_config["name"],
    cookie_config["key"],
    cookie_config["expiry_days"],
    preauth
)

# 3. Mostrar el formulario de Login
name, authentication_status, username = authenticator.login("Login - goBIG Managers", "main")

if authentication_status == False:
    st.error("🔴 Usuario o contraseña incorrectos")
elif authentication_status == None:
    st.warning("🟡 Por favor ingresa tu usuario y contraseña")
elif authentication_status:
    # --- SI EL LOGIN ES EXITOSO, MUESTRA ESTO ---
    with st.sidebar:
        st.write(f"Bienvenido/a, **{name}**")
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
