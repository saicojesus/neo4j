import streamlit as st


def render_metricas(conn):
    """Renderiza las tarjetas de métricas principales"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        count = get_count(conn, "Almacen")
        st.metric("🏭 Almacenes", count)

    with col2:
        count = get_count(conn, "PuntoEntrega")
        st.metric("📦 Puntos de Entrega", count)

    with col3:
        count = get_relationship_count(conn)
        st.metric("🛣️ Rutas", count)

    with col4:
        count = get_count(conn, "Interseccion")
        st.metric("🚦 Intersecciones", count)


def get_count(conn, label):
    """Obtiene conteo de nodos por etiqueta"""
    try:
        result = conn.query(f"MATCH (n:{label}) RETURN count(n) as count")
        return result[0]["count"] if result else 0
    except:
        return 0


def get_relationship_count(conn):
    """Obtiene conteo de relaciones"""
    try:
        result = conn.query("MATCH ()-[r:CONECTA_A]->() RETURN count(r) as count")
        return result[0]["count"] if result else 0
    except:
        return 0
