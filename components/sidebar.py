import streamlit as st


def render_sidebar(conn):
    """Renderiza la barra lateral con configuración"""
    with st.sidebar:
        st.header("⚙️ Configuración")

        # Obtener ubicaciones
        locations = get_locations(conn)

        if not locations:
            st.error("No hay ubicaciones disponibles")
            return None, None, None, None

        st.subheader("📍 Puntos de Ruta")

        location_options = {
            f"{loc['nombre']} ({loc['tipo']})": loc["id"] for loc in locations
        }

        origen = st.selectbox(
            "Punto de Origen",
            options=list(location_options.keys()),
            index=0,
            key="origen_select",
        )

        destino = st.selectbox(
            "Punto de Destino",
            options=list(location_options.keys()),
            index=min(1, len(location_options) - 1),
            key="destino_select",
        )

        st.subheader("⚖️ Restricciones")
        capacidad = st.slider(
            "Capacidad del camión (toneladas)",
            min_value=1,
            max_value=50,
            value=15,
            help="Rutas con capacidad menor serán filtradas",
            key="capacidad_slider",
        )

        st.subheader("🧮 Algoritmo")
        algoritmo = st.radio(
            "Seleccionar algoritmo",
            ["Dijkstra (Distancia)", "A* (Tiempo + Tráfico)", "Comparar ambos"],
            key="algoritmo_radio",
        )
        return origen, destino, capacidad, algoritmo, location_options


def get_locations(conn):
    """Obtiene lista de ubicaciones"""
    try:
        return conn.query("""
            MATCH (n)
            WHERE n:Almacen OR n:PuntoEntrega
            RETURN n.id as id, n.nombre as nombre, labels(n)[0] as tipo
            ORDER BY tipo, nombre
        """)
    except Exception as e:
        st.error(f"Error cargando ubicaciones: {e}")
        return []
