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
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Usamos el modelo más rápido y eficiente para texto
    model = genai.GenerativeModel('gemini-1.5-flash') 
except Exception as e:
    st.error("⚠️ Error al conectar con la API de Gemini. Revisa tus secretos en Streamlit.")
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

# Convertir los datos a texto para que Gemini los entienda
contexto_datos = f"""
Aquí están los datos financieros históricos de la empresa goBIG S.A.S.:

1. Tabla de Rendimientos (Ingresos, Utilidad, EBITDA, Margen):
{df_rend.to_markdown()}

2. Tabla de Valoración Pre-Money (Múltiplos EBITDA):
{df_val.to_markdown()}

Instrucciones para la IA:
- Eres el Director Financiero (CFO) analítico de goBIG S.A.S.
- Responde siempre en español, con un tono ejecutivo, profesional pero directo.
- Basa tus respuestas ÚNICAMENTE en los datos proporcionados arriba.
- Si te preguntan algo que no está en los datos, dilo honestamente.
- Al analizar, resalta crecimientos, eficiencias y da una perspectiva de negocio.
"""

# 4. Construir la Interfaz de Pestañas (Chat y Reporte)
tab1, tab2 = st.tabs(["💬 Chatbot de Datos", "📄 Generador Reporte McKinsey"])

# --- PESTAÑA 1: CHATBOT ---
with tab1:
    st.subheader("Conversa con tus datos")
    
    # Inicializar el historial del chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Mostrar mensajes anteriores
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Caja de texto para el usuario
    if prompt := st.chat_input("Ej: ¿Cuál fue el año con mayor crecimiento de EBITDA y por qué?"):
        # Guardar y mostrar mensaje del usuario
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Preparar prompt completo (Contexto + Historial + Pregunta)
        historial_texto = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
        prompt_completo = f"{contexto_datos}\n\nHistorial reciente:\n{historial_texto}\n\nUsuario: {prompt}\nCFO AI:"

        # Llamar a Gemini
        with st.chat_message("assistant"):
            with st.spinner("Analizando..."):
                try:
                    response = model.generate_content(prompt_completo)
                    respuesta_ia = response.text
                    st.markdown(respuesta_ia)
                    # Guardar respuesta
                    st.session_state.messages.append({"role": "assistant", "content": respuesta_ia})
                except Exception as e:
                    st.error(f"Error al generar respuesta: {e}")

# --- PESTAÑA 2: REPORTE MCKINSEY ---
with tab2:
    st.subheader("Reporte Gerencial Automatizado")
    st.info("Genera un artículo narrativo profundo sobre la salud financiera y la valoración de goBIG S.A.S., estructurado con la rigurosidad de la consultoría estratégica de alto nivel.")
    
    if st.button("🚀 Generar Reporte Mensual (Estilo McKinsey)"):
        with st.spinner("Redactando reporte estratégico... esto puede tomar unos segundos."):
            prompt_mckinsey = f"""
            {contexto_datos}
            
            Tarea: Actúa como un Socio Senior de McKinsey & Company. 
            Escribe un artículo informativo y de análisis estratégico sobre los resultados financieros y la evolución de la valoración de goBIG S.A.S. (2020-2025).
            
            Estructura obligatoria del artículo:
            1. Título atractivo y profesional.
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
