import os

import streamlit as st

from components.algoritmos import ejecutar_algoritmos

# Importar componentes
from components.conexion import init_connection, test_connection
from components.consultas import render_consultas
from components.metricas import render_metricas
from components.sidebar import render_sidebar
from components.visualizacion import render_grafo


def load_css():
    css_file = os.path.join(os.path.dirname(__file__), "assets", "style.css")
    if os.path.exists(css_file):
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("Archivo de estilos no encontrado")


# Configuración de la página
st.set_page_config(
    page_title="Logistics Optimizer - Smart Routing", page_icon="🚚", layout="wide"
)


# load_css()
# Título principal
st.title("🚚 Logistics Optimizer - Smart Routing Dashboard")
st.markdown("---")

# Inicializar conexión
conn = init_connection()

# Probar conexión
success, message = test_connection(conn)
if not success:
    st.error(f"Error de conexión a Neo4j: {message}")
    st.stop()

# Renderizar sidebar
origen, destino, capacidad, algoritmo, location_options = render_sidebar(conn)

if not location_options:
    st.warning("No hay ubicaciones disponibles. Verifica la carga de datos.")
    st.stop()

# Renderizar métricas
render_metricas(conn)

st.markdown("---")

# Estado para mantener la ruta actual
if "ruta_actual" not in st.session_state:
    st.session_state.ruta_actual = None
if "ultima_busqueda" not in st.session_state:
    st.session_state.ultima_busqueda = None

# Sección de algoritmos
st.header("🛣️ Optimización de Rutas")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    st.markdown(f"**Origen:** {origen}")
    st.markdown(f"**Destino:** {destino}")

with col2:
    st.markdown(f"**Algoritmo:** {algoritmo}")
    st.markdown(f"**Capacidad:** {capacidad} ton")

with col3:
    if st.button("🚀 Calcular Ruta Óptima", type="primary", use_container_width=True):
        with st.spinner("Calculando rutas..."):
            origen_id = location_options[origen]
            destino_id = location_options[destino]

            # Guardar parámetros de búsqueda
            st.session_state.ultima_busqueda = {
                "origen": origen,
                "destino": destino,
                "algoritmo": algoritmo,
                "capacidad": capacidad,
            }

            # Ejecutar algoritmos y guardar resultado
            st.session_state.ruta_actual = ejecutar_algoritmos(
                conn, origen_id, destino_id, algoritmo, capacidad
            )

# Mostrar información de la última búsqueda si existe
if st.session_state.ultima_busqueda:
    st.info(
        f"📌 Mostrando última ruta calculada: {st.session_state.ultima_busqueda['origen']} → {st.session_state.ultima_busqueda['destino']} ({st.session_state.ultima_busqueda['algoritmo']})"
    )

st.markdown("---")

# Renderizar visualización del grafo con la ruta actual
render_grafo(conn, st.session_state.ruta_actual)

# Renderizar consultas complejas
render_consultas(conn)

# Botón para limpiar la ruta destacada
if st.session_state.ruta_actual:
    if st.button("🧹 Limpiar ruta destacada", use_container_width=True):
        st.session_state.ruta_actual = None
        st.session_state.ultima_busqueda = None
        st.rerun()

# Pie de página
st.markdown("---")
st.markdown("© 2025 - Proyecto III: Logistics Optimizer (Smart Routing)")
st.markdown("Sistemas de Bases de Datos II - UNEG")
