import streamlit as st
import pandas as pd
import google.generativeai as genai

# 1. Configuración de la página
st.set_page_config(page_title="goBIG AI", page_icon="🧠", layout="wide")

# --- CANDADO DE SEGURIDAD ---
if not st.session_state.get("authentication_status"):
    st.warning("🔒 Acceso denegado. Por favor dirígete a la página de inicio (app) para iniciar sesión.")
    st.stop()
# ----------------------------

with st.sidebar:
    st.image("goBIG_logo.jpg", width=200)
    st.markdown("---")
    st.caption("v2.0 - Motor de IA impulsado por Google Gemini")

st.title("🧠 Analista Financiero de Inteligencia Artificial")
st.markdown("Consulta en lenguaje natural o genera reportes ejecutivos basados en los datos financieros de goBIG.")
st.markdown("---")

# 2. Configurar Gemini API
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("🔑 No se encontró la variable 'GEMINI_API_KEY' en los Secrets de Streamlit.")
    st.stop()

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"⚠️ Error al inicializar Gemini: {e}")
    st.stop()

# 3. Descargar datos para darle contexto a la IA
@st.cache_data(ttl=600)
def load_data_for_ai():
    url_doc = "https://docs.google.com/spreadsheets/d/1ldntONNpWFgXPcF8VINDKzNAhG_vGMdzGEOESM3aLNU/export?format=xlsx"
    xls = pd.ExcelFile(url_doc)
    sheet_names = xls.sheet_names
    s_rend = [s for s in sheet_names if 'rendimient' in s.lower()]
    s_val = [s for s in sheet_names if 'valoraci' in s.lower()]
    
    df_rend = pd.read_excel(xls, sheet_name=s_rend[0]) if s_rend else pd.DataFrame()
    df_val = pd.read_excel(xls, sheet_name=s_val[0]) if s_val else pd.DataFrame()
    return df_rend, df_val

with st.spinner("Sincronizando cerebro de IA con Google Drive..."):
    df_rend, df_val = load_data_for_ai()

# Convertir los datos a texto formateado para la IA
contexto_datos = f"""
Aquí están los datos financieros históricos de la empresa goBIG S.A.S.:

1. Tabla de Rendimientos (Ingresos, Utilidad, EBITDA, Margen):
{df_rend.to_string()}

2. Tabla de Valoración Pre-Money (Múltiplos EBITDA):
{df_val.to_string()}

Instrucciones para la IA:
- Eres el Director Financiero (CFO) analítico de goBIG S.A.S.
- Responde siempre en español, con un tono ejecutivo, profesional pero directo.
- Basa tus respuestas ÚNICAMENTE en los datos proporcionados arriba.
- Si te preguntan algo que no está en los datos, dilo honestamente.
- Al analizar, resalta crecimientos, eficiencias y da una perspectiva de negocio.
"""

# 4. Construir la Interfaz de Pestañas (Chat y Reporte)
# --- AQUÍ CAMBIAMOS EL NOMBRE DE LA PESTAÑA ---
tab1, tab2 = st.tabs(["💬 Chatbot de Datos", "📄 Generador de reporte mensual AGE"])

# --- PESTAÑA 1: CHATBOT ---
with tab1:
    st.subheader("Conversa con tus datos")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ej: ¿Cuál fue el año con mayor crecimiento de EBITDA y por qué?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        historial_texto = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
        prompt_completo = f"{contexto_datos}\n\nHistorial reciente:\n{historial_texto}\n\nUsuario: {prompt}\nCFO AI:"

        with st.chat_message("assistant"):
            with st.spinner("Analizando..."):
                try:
                    response = model.generate_content(prompt_completo)
                    respuesta_ia = response.text
                    st.markdown(respuesta_ia)
                    st.session_state.messages.append({"role": "assistant", "content": respuesta_ia})
                except Exception as e:
                    st.error(f"Error al generar respuesta: {e}")

# --- PESTAÑA 2: REPORTE AGE ---
with tab2:
    st.subheader("Reporte Gerencial Automatizado")
    st.info("Genera un artículo narrativo profundo sobre la salud financiera y la valoración de goBIG S.A.S., estructurado para la presentación en la Asamblea General de Accionistas (AGE).")
    
    # --- AQUÍ CAMBIAMOS EL NOMBRE DEL BOTÓN ---
    if st.button("🚀 Generar de reporte mensual AGE"):
        with st.spinner("Redactando reporte estratégico... esto puede tomar unos segundos."):
            prompt_mckinsey = f"""
            {contexto_datos}
            
            Tarea: Actúa como un Socio Senior de McKinsey & Company estructurando un informe para la Asamblea General de Accionistas. 
            Escribe un artículo informativo y de análisis estratégico sobre los resultados financieros y la evolución de la valoración de goBIG S.A.S. (2020-2025).
            
            Estructura obligatoria del artículo:
            1. Título atractivo y profesional (mencionando a la AGE).
            2. "Executive Summary" (Resumen ejecutivo de 1 párrafo).
            3. "El Viaje del Crecimiento" (Análisis de Ingresos vs EBITDA).
            4. "Evolución de la Valoración Pre-Money" (Explicación del salto de Etapa Semilla a Fase Escala).
            5. "Perspectiva de Negocio y Recomendación Estratégica" (Un párrafo de cierre brillante y accionable).
            
            Usa negritas, listas y un tono sumamente elocuente, persuasivo y analítico.
            """
            try:
                response_report = model.generate_content(prompt_mckinsey)
                st.markdown("---")
                st.markdown(response_report.text)
            except Exception as e:
                st.error(f"Error al generar el reporte: {e}")
