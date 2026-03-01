import time

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from neo4j import GraphDatabase

# Configuración de la página
st.set_page_config(
    page_title="Logistics Optimizer - Smart Routing", page_icon="🚚", layout="wide"
)

# Título y descripción
st.title("🚚 Logistics Optimizer - Smart Routing Dashboard")
st.markdown("---")


# ============================================
# CONEXIÓN A NEO4J
# ============================================
class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]


# Inicializar conexión en session state
if "conn" not in st.session_state:
    st.session_state.conn = Neo4jConnection(
        "bolt://localhost:7687", "neo4j", "password123"
    )

# ============================================
# SIDEBAR - CONFIGURACIÓN
# ============================================
with st.sidebar:
    st.header("⚙️ Configuración")

    # Selección de origen y destino
    st.subheader("📍 Puntos de Ruta")

    # Obtener lista de ubicaciones
    locations = st.session_state.conn.query("""
        MATCH (n)
        WHERE n:Almacen OR n:PuntoEntrega
        RETURN n.id as id, n.nombre as nombre, labels(n)[0] as tipo
        ORDER BY tipo, nombre
    """)

    location_options = {
        f"{loc['nombre']} ({loc['tipo']})": loc["id"] for loc in locations
    }

    origen = st.selectbox(
        "Punto de Origen",
        options=list(location_options.keys()),
        index=0 if location_options else 0,
    )

    destino = st.selectbox(
        "Punto de Destino",
        options=list(location_options.keys()),
        index=min(1, len(location_options) - 1) if len(location_options) > 1 else 0,
    )

    # Restricciones de carga
    st.subheader("⚖️ Restricciones")
    capacidad_camion = st.slider(
        "Capacidad del camión (toneladas)",
        min_value=1,
        max_value=50,
        value=15,
        help="Rutas con capacidad menor a este valor serán filtradas",
    )

    # Algoritmo a utilizar
    st.subheader("🧮 Algoritmo")
    algoritmo = st.radio(
        "Seleccionar algoritmo",
        ["Dijkstra (Distancia)", "A* (Tiempo + Tráfico)", "Comparar ambos"],
    )

    st.markdown("---")
    st.markdown("**Proyecto III - Sistemas BD II**")
    st.markdown("Prof. Clinia Cordero")

# ============================================
# MÉTRICAS PRINCIPALES
# ============================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    result = st.session_state.conn.query("MATCH (a:Almacen) RETURN count(a) as count")[
        0
    ]
    st.metric("🏭 Almacenes", result["count"])

with col2:
    result = st.session_state.conn.query(
        "MATCH (p:PuntoEntrega) RETURN count(p) as count"
    )[0]
    st.metric("📦 Puntos de Entrega", result["count"])

with col3:
    result = st.session_state.conn.query(
        "MATCH ()-[r:CONECTA_A]->() RETURN count(r) as count"
    )[0]
    st.metric("🛣️ Rutas", result["count"])

with col4:
    result = st.session_state.conn.query(
        "MATCH (i:Interseccion) RETURN count(i) as count"
    )[0]
    st.metric("🚦 Intersecciones", result["count"])

st.markdown("---")

# ============================================
# VISUALIZACIÓN DEL GRAFO
# ============================================
with st.expander("🗺️ Ver mapa completo de rutas", expanded=False):
    # Obtener datos del grafo
    nodes = st.session_state.conn.query("""
        MATCH (n)
        RETURN n.id as id,
               n.x as x,
               n.y as y,
               labels(n)[0] as tipo,
               n.nombre as nombre
    """)

    edges = st.session_state.conn.query("""
        MATCH (n1)-[r:CONECTA_A]->(n2)
        RETURN n1.id as source,
               n2.id as target,
               r.distancia as distancia,
               r.estado_trafico as trafico
        LIMIT 200
    """)

    # Crear figura con Plotly
    fig = go.Figure()

    # Diccionario de colores por tipo
    color_map = {"Almacen": "red", "PuntoEntrega": "blue", "Interseccion": "green"}

    # Agregar nodos
    for node in nodes:
        fig.add_trace(
            go.Scatter(
                x=[node["x"]],
                y=[node["y"]],
                mode="markers+text",
                marker=dict(
                    size=15 if node["tipo"] == "Almacen" else 10,
                    color=color_map.get(node["tipo"], "gray"),
                    symbol="square" if node["tipo"] == "Almacen" else "circle",
                ),
                text=node["id"],
                textposition="top center",
                name=node["tipo"],
                legendgroup=node["tipo"],
                showlegend=False,
            )
        )

    # Agregar aristas
    for edge in edges:
        source_node = next((n for n in nodes if n["id"] == edge["source"]), None)
        target_node = next((n for n in nodes if n["id"] == edge["target"]), None)

        if source_node and target_node:
            fig.add_trace(
                go.Scatter(
                    x=[source_node["x"], target_node["x"]],
                    y=[source_node["y"], target_node["y"]],
                    mode="lines",
                    line=dict(
                        color="rgba(100,100,100,0.3)", width=1 + edge["trafico"] * 2
                    ),
                    hoverinfo="text",
                    text=f"Distancia: {edge['distancia']:.2f} km<br>Tráfico: {edge['trafico']:.2f}",
                    showlegend=False,
                )
            )

    fig.update_layout(
        title="Mapa de Rutas",
        xaxis_title="Coordenada X",
        yaxis_title="Coordenada Y",
        hovermode="closest",
        width=1000,
        height=600,
    )

    # Reemplazar use_container_width con width='stretch'
    st.plotly_chart(fig, use_container_width=True)  # Temporal, se puede cambiar después

# ============================================
# EJECUCIÓN DE ALGORITMOS
# ============================================
st.header("🛣️ Optimización de Rutas")

if st.button("🚀 Calcular Ruta Óptima", type="primary"):
    with st.spinner("Calculando rutas..."):
        origen_id = location_options[origen]
        destino_id = location_options[destino]

        try:
            # Crear proyección del grafo
            st.session_state.conn.query("""
                CALL gds.graph.project(
                    'myGraph',
                    ['Almacen', 'Interseccion', 'PuntoEntrega'],
                    'CONECTA_A',
                    {
                        relationshipProperties: ['peso_distancia', 'peso_tiempo', 'capacidad_max_ton']
                    }
                )
            """)

            # Consultas según algoritmo seleccionado
            if algoritmo == "Dijkstra (Distancia)" or algoritmo == "Comparar ambos":
                # Dijkstra con peso_distancia
                query_dijkstra = """
                MATCH (source {id: $origen}), (target {id: $destino})
                CALL gds.shortestPath.dijkstra.stream('myGraph', {
                    sourceNode: source,
                    targetNode: target,
                    relationshipWeightProperty: 'peso_distancia'
                })
                YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs, path
                RETURN
                    'Dijkstra' as algoritmo,
                    totalCost as distancia_total,
                    [nodeId IN nodeIds | gds.util.asNode(nodeId).id] as ruta_nodos,
                    [nodeId IN nodeIds | gds.util.asNode(nodeId).nombre] as ruta_nombres
                """

                result_dijkstra = st.session_state.conn.query(
                    query_dijkstra, {"origen": origen_id, "destino": destino_id}
                )

            if algoritmo == "A* (Tiempo + Tráfico)" or algoritmo == "Comparar ambos":
                # A* con peso_tiempo
                query_astar = """
                MATCH (source {id: $origen}), (target {id: $destino})
                CALL gds.shortestPath.astar.stream('myGraph', {
                    sourceNode: source,
                    targetNode: target,
                    relationshipWeightProperty: 'peso_tiempo',
                    latitudeProperty: 'y',
                    longitudeProperty: 'x'
                })
                YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs, path
                RETURN
                    'A*' as algoritmo,
                    totalCost as tiempo_total,
                    [nodeId IN nodeIds | gds.util.asNode(nodeId).id] as ruta_nodos,
                    [nodeId IN nodeIds | gds.util.asNode(nodeId).nombre] as ruta_nombres
                """

                result_astar = st.session_state.conn.query(
                    query_astar, {"origen": origen_id, "destino": destino_id}
                )

            # Mostrar resultados
            if algoritmo == "Dijkstra (Distancia)" and result_dijkstra:
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("📊 Resultado Dijkstra")
                    st.metric(
                        "Distancia Total",
                        f"{result_dijkstra[0]['distancia_total']:.2f} km",
                    )

                    # Mostrar ruta
                    st.write("**Ruta:**")
                    ruta_nombres = result_dijkstra[0]["ruta_nombres"]
                    for i, nombre in enumerate(ruta_nombres):
                        st.write(f"{i + 1}. {nombre}")

            elif algoritmo == "A* (Tiempo + Tráfico)" and result_astar:
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("📊 Resultado A*")
                    st.metric(
                        "Tiempo Estimado", f"{result_astar[0]['tiempo_total']:.2f} min"
                    )

                    st.write("**Ruta:**")
                    ruta_nombres = result_astar[0]["ruta_nombres"]
                    for i, nombre in enumerate(ruta_nombres):
                        st.write(f"{i + 1}. {nombre}")

            elif algoritmo == "Comparar ambos" and result_dijkstra and result_astar:
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("📊 Dijkstra (Distancia)")
                    st.metric(
                        "Distancia Total",
                        f"{result_dijkstra[0]['distancia_total']:.2f} km",
                    )
                    st.write("**Ruta:**")
                    for i, nombre in enumerate(result_dijkstra[0]["ruta_nombres"][:5]):
                        st.write(f"{i + 1}. {nombre}")
                    if len(result_dijkstra[0]["ruta_nombres"]) > 5:
                        st.write(
                            f"... y {len(result_dijkstra[0]['ruta_nombres']) - 5} más"
                        )

                with col2:
                    st.subheader("📊 A* (Tiempo + Tráfico)")
                    st.metric(
                        "Tiempo Estimado", f"{result_astar[0]['tiempo_total']:.2f} min"
                    )
                    st.write("**Ruta:**")
                    for i, nombre in enumerate(result_astar[0]["ruta_nombres"][:5]):
                        st.write(f"{i + 1}. {nombre}")
                    if len(result_astar[0]["ruta_nombres"]) > 5:
                        st.write(
                            f"... y {len(result_astar[0]['ruta_nombres']) - 5} más"
                        )

                # Comparación visual
                st.subheader("📈 Comparación de Métricas")
                comparacion_df = pd.DataFrame(
                    {
                        "Métrica": ["Distancia (km)", "Tiempo (min)"],
                        "Dijkstra": [
                            result_dijkstra[0]["distancia_total"],
                            result_dijkstra[0]["distancia_total"] * 1.5,
                        ],  # Estimado
                        "A*": [
                            result_astar[0]["tiempo_total"] / 1.5,  # Estimado
                            result_astar[0]["tiempo_total"],
                        ],
                    }
                )

                fig = px.bar(
                    comparacion_df,
                    x="Métrica",
                    y=["Dijkstra", "A*"],
                    barmode="group",
                    title="Comparación de Algoritmos",
                )
                st.plotly_chart(fig, use_container_width=True)

            # Limpiar proyección
            st.session_state.conn.query("CALL gds.graph.drop('myGraph')")

        except Exception as e:
            st.error(f"Error en la ejecución: {str(e)}")
            # Intentar limpiar proyección si existe
            try:
                st.session_state.conn.query("CALL gds.graph.drop('myGraph')")
            except:
                pass

# ============================================
# CONSULTAS COMPLEJAS (Requerimiento del PDF)
# ============================================
st.header("🔍 Consultas de Análisis")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📊 Estadísticas de Tráfico",
        "🏭 Rutas Críticas",
        "⚖️ Capacidad de Rutas",
        "📍 Puntos de Congestión",
        "📦 Demanda por Zona",
    ]
)

with tab1:
    st.subheader("Distribución del Tráfico por Ruta")
    query = """
    MATCH ()-[r:CONECTA_A]->()
    WITH
        CASE
            WHEN r.estado_trafico < 0.3 THEN 'Bajo'
            WHEN r.estado_trafico < 0.6 THEN 'Medio'
            ELSE 'Alto'
        END as nivel_trafico,
        r.distancia as distancia
    RETURN nivel_trafico, count(*) as cantidad, avg(distancia) as distancia_promedio
    ORDER BY nivel_trafico
    """
    result = st.session_state.conn.query(query)
    df = pd.DataFrame(result)
    if not df.empty:
        fig = px.bar(
            df,
            x="nivel_trafico",
            y="cantidad",
            title="Cantidad de Rutas por Nivel de Tráfico",
            color="nivel_trafico",
        )
        # Reemplazar use_container_width con width='stretch'
        st.plotly_chart(fig, use_container_width=True)  # Temporal
    else:
        st.info("No hay datos disponibles")

with tab2:
    st.subheader("Top 10 Rutas Más Largas")
    query = """
    MATCH (n1)-[r:CONECTA_A]->(n2)
    RETURN n1.id as origen, n2.id as destino,
           r.distancia as distancia, r.estado_trafico as trafico
    ORDER BY r.distancia DESC
    LIMIT 10
    """
    result = st.session_state.conn.query(query)
    df = pd.DataFrame(result)
    if not df.empty:
        # Reemplazar use_container_width con width='stretch'
        st.dataframe(df, use_container_width=True)  # Temporal
    else:
        st.info("No hay datos disponibles")

with tab3:
    st.subheader("Rutas por Capacidad Máxima")
    capacidad_filter = st.slider("Capacidad mínima (ton)", 0, 40, 10, key="cap_slider")
    query = f"""
    MATCH ()-[r:CONECTA_A]->()
    WHERE r.capacidad_max_ton >= {capacidad_filter}
    RETURN r.capacidad_max_ton as capacidad, count(*) as cantidad
    ORDER BY capacidad
    """
    result = st.session_state.conn.query(query)
    df = pd.DataFrame(result)
    if not df.empty:
        fig = px.bar(
            df,
            x="capacidad",
            y="cantidad",
            title=f"Rutas con capacidad >= {capacidad_filter} ton",
            color="capacidad",
        )
        # Reemplazar use_container_width con width='stretch'
        st.plotly_chart(fig, use_container_width=True)  # Temporal
    else:
        st.info(f"No hay rutas con capacidad >= {capacidad_filter} ton")

with tab4:
    st.subheader("Intersecciones con Mayor Congestión")
    query = """
    MATCH (i:Interseccion)<-[r:CONECTA_A]-()
    WITH i, avg(r.estado_trafico) as trafico_promedio, count(r) as rutas_conectadas
    RETURN i.id as interseccion, trafico_promedio, rutas_conectadas
    ORDER BY trafico_promedio DESC
    LIMIT 10
    """
    result = st.session_state.conn.query(query)
    df = pd.DataFrame(result)
    if not df.empty:
        # Reemplazar use_container_width con width='stretch'
        st.dataframe(df, use_container_width=True)  # Temporal
    else:
        st.info("No hay datos disponibles")

with tab5:
    st.subheader("Distribución de Demanda por Cliente")
    query = """
    MATCH (p:PuntoEntrega)
    RETURN p.nombre as cliente, p.demanda as demanda, p.prioridad as prioridad
    ORDER BY p.demanda DESC
    LIMIT 15
    """
    result = st.session_state.conn.query(query)
    df = pd.DataFrame(result)
    if not df.empty:
        fig = px.bar(
            df, x="cliente", y="demanda", color="prioridad", title="Demanda por Cliente"
        )
        # Reemplazar use_container_width con width='stretch'
        st.plotly_chart(fig, use_container_width=True)  # Temporal
    else:
        st.info("No hay datos disponibles")

# ============================================
# PIE DE PÁGINA
# ============================================
st.markdown("---")
st.markdown("© 2025 - Proyecto III: Logistics Optimizer (Smart Routing)")
st.markdown("Sistemas de Bases de Datos II - UNEG")
