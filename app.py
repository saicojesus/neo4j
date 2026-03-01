import os

import streamlit as st

# --- MODIFICADO: Importar las funciones de cálculo Y de visualización ---
from components.algoritmos import (
    ejecutar_algoritmos,
    mostrar_comparacion,
    mostrar_resultado_astar,
    mostrar_resultado_dijkstra,
)

# Importar otros componentes
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
        # CSS de respaldo
        st.markdown(
            """
        <style>
            .main .block-container {
                max-width: 100% !important;
                padding-left: 2rem !important;
                padding-right: 2rem !important;
            }
            .st-emotion-cache-4j9vvg, .st-emotion-cache-keje6w {
                max-width: 100% !important;
                width: 100% !important;
            }
        </style>
        """,
            unsafe_allow_html=True,
        )


# Configuración de la página
st.set_page_config(
    page_title="Logistics Optimizer - Smart Routing", page_icon="🚚", layout="wide"
)

load_css()
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

# --- MODIFICADO: Añadido 'resultados_calculados' para guardar los datos ---
if "ruta_actual" not in st.session_state:
    st.session_state.ruta_actual = None
if "ultima_busqueda" not in st.session_state:
    st.session_state.ultima_busqueda = None
if "resultados_calculados" not in st.session_state:
    st.session_state.resultados_calculados = None


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
    # --- MODIFICADO: El botón ahora solo calcula y guarda los resultados ---
    if st.button("🚀 Calcular Ruta Óptima", type="primary", use_container_width=True):
        with st.spinner("Calculando rutas..."):
            origen_id = location_options[origen]
            destino_id = location_options[destino]

            st.session_state.ultima_busqueda = {
                "origen": origen,
                "destino": destino,
                "algoritmo": algoritmo,
                "capacidad": capacidad,
            }

            # La función ahora devuelve la ruta para el mapa y los datos para mostrar
            ruta_mapa, resultados_display = ejecutar_algoritmos(
                conn, origen_id, destino_id, algoritmo, capacidad
            )
            st.session_state.ruta_actual = ruta_mapa
            st.session_state.resultados_calculados = resultados_display

# --- NUEVA SECCIÓN: Mostrar los resultados a todo lo ancho ---
# Esta sección se encuentra fuera de las columnas, por lo que usará todo el espacio.
if st.session_state.resultados_calculados:
    algo_usado = st.session_state.ultima_busqueda["algoritmo"]
    resultados = st.session_state.resultados_calculados

    if algo_usado == "Dijkstra (Distancia)":
        mostrar_resultado_dijkstra(resultados.get("dijkstra"))

    elif algo_usado == "A* (Tiempo + Tráfico)":
        mostrar_resultado_astar(resultados.get("astar"))

    else:  # Comparar ambos
        mostrar_comparacion(resultados.get("dijkstra"), resultados.get("astar"))


# Mostrar información de la última búsqueda si existe
if st.session_state.ultima_busqueda:
    st.info(
        f"📌 **Mostrando última ruta calculada:** "
        f"{st.session_state.ultima_busqueda['origen']} → "
        f"{st.session_state.ultima_busqueda['destino']} "
        f"({st.session_state.ultima_busqueda['algoritmo']})"
    )

st.markdown("---")

# Renderizar visualización del grafo con la ruta actual
render_grafo(conn, st.session_state.ruta_actual)

# Renderizar consultas complejas
render_consultas(conn)

# --- MODIFICADO: El botón de limpiar ahora resetea también los resultados ---
if st.session_state.ruta_actual:
    if st.button("🧹 Limpiar ruta destacada", use_container_width=True):
        st.session_state.ruta_actual = None
        st.session_state.ultima_busqueda = None
        st.session_state.resultados_calculados = None  # <-- Añadido
        st.rerun()
