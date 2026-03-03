import plotly.graph_objects as go
import streamlit as st


# 1. Modificamos la firma para recibir "capacidad"
def render_grafo(conn, ruta_destacada=None, titulo="Mapa de Rutas", capacidad=0):
    """Renderiza la visualización del grafo con opción de resaltar una ruta y filtrar por carga"""

    with st.expander("🗺️ Ver mapa completo de rutas", expanded=True):
        nodes = get_nodes(conn)
        # 2. Pasamos la capacidad a la consulta de aristas
        edges = get_edges(conn, capacidad)

        if not nodes:
            st.warning("No hay nodos para visualizar")
            return

        if not edges:
            st.warning(
                f"No hay rutas disponibles que soporten una carga de {capacidad} toneladas."
            )

        # Crear figura con la ruta destacada si existe
        fig = crear_figura_grafo(nodes, edges, ruta_destacada)

        # Agregar título dinámico
        if ruta_destacada:
            fig.update_layout(
                title=f"🗺️ {titulo} - Ruta Óptima Resaltada",
                title_font=dict(color="#2E86AB", size=16),
            )
        else:
            fig.update_layout(
                title=f"🗺️ {titulo} (Filtro: ≥ {capacidad} ton)",
            )

        st.plotly_chart(fig, use_container_width=True)

        # Mostrar leyenda personalizada si hay ruta destacada
        if ruta_destacada:
            st.markdown(
                """
            <style>
            .leyenda-ruta {
                background: linear-gradient(90deg, #FF4B4B 0%, #FF8C8C 100%);
                color: white;
                padding: 10px;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                margin: 10px 0;
            }
            </style>
            <div class="leyenda-ruta">
                🔴 La ruta resaltada en rojo muestra el camino óptimo encontrado
            </div>
            """,
                unsafe_allow_html=True,
            )


def get_nodes(conn):
    """Obtiene nodos del grafo"""
    try:
        return conn.query("""
            MATCH (n)
            RETURN n.id as id,
                   n.x as x,
                   n.y as y,
                   labels(n)[0] as tipo,
                   n.nombre as nombre
        """)
    except Exception as e:
        st.error(f"Error cargando nodos: {e}")
        return []


# 3. Aplicamos el FILTRADO DE ARISTAS EN TIEMPO REAL
def get_edges(conn, capacidad):
    """Obtiene relaciones del grafo filtradas por la capacidad máxima permitida"""
    try:
        # Usamos f-string para inyectar la capacidad en la consulta Cypher
        # Si tienes manejo de parámetros en tu wrapper (conn.query), es mejor usar $capacidad
        query = f"""
            MATCH (n1)-[r:CONECTA_A]->(n2)
            WHERE r.capacidad_max_ton >= {capacidad}
            RETURN n1.id as source,
                   n2.id as target,
                   r.distancia as distancia,
                   r.estado_trafico as trafico,
                   r.tiempo_estimado as tiempo,
                   r.capacidad_max_ton as capacidad_max
        """
        return conn.query(query)
    except Exception as e:
        st.error(f"Error cargando relaciones: {e}")
        return []


def crear_figura_grafo(nodes, edges, ruta_destacada=None):
    """Crea la figura de Plotly para el grafo con opción de resaltar ruta"""
    fig = go.Figure()

    color_map = {"Almacen": "red", "PuntoEntrega": "blue", "Interseccion": "green"}
    nodes_dict = {node["id"]: node for node in nodes}

    nodos_en_ruta = set()
    aristas_en_ruta = set()

    if ruta_destacada and "ruta_nodos" in ruta_destacada:
        nodos_en_ruta = set(ruta_destacada["ruta_nodos"])
        for i in range(len(ruta_destacada["ruta_nodos"]) - 1):
            aristas_en_ruta.add(
                (ruta_destacada["ruta_nodos"][i], ruta_destacada["ruta_nodos"][i + 1])
            )

    # Dibujar aristas
    for edge in edges:
        source_node = nodes_dict.get(edge["source"])
        target_node = nodes_dict.get(edge["target"])

        if source_node and target_node:
            es_ruta_destacada = (edge["source"], edge["target"]) in aristas_en_ruta or (
                edge["target"],
                edge["source"],
            ) in aristas_en_ruta

            # 4. Actualizamos el texto flotante para mostrar la capacidad
            capacidad_arista = edge.get("capacidad_max", "N/A")

            if es_ruta_destacada:
                line_color = "#FF4B4B"
                line_width = 4
                opacity = 1.0
                hover_text = f"🚚 **RUTA ÓPTIMA**<br>Distancia: {edge['distancia']:.2f} km<br>Capacidad: {capacidad_arista} ton<br>Tráfico: {edge['trafico']:.2f}<br>Tiempo: {edge.get('tiempo', 0):.0f} min"
            else:
                line_color = "rgba(150,150,150,0.3)"
                line_width = 1 + (edge["trafico"] * 2)
                opacity = 0.4
                hover_text = f"Distancia: {edge['distancia']:.2f} km<br>Capacidad: {capacidad_arista} ton<br>Tráfico: {edge['trafico']:.2f}<br>Tiempo: {edge.get('tiempo', 0):.0f} min"

            fig.add_trace(
                go.Scatter(
                    x=[source_node["x"], target_node["x"]],
                    y=[source_node["y"], target_node["y"]],
                    mode="lines",
                    line=dict(color=line_color, width=line_width),
                    opacity=opacity,
                    hoverinfo="text",
                    text=hover_text,
                    showlegend=False,
                    name="Ruta Óptima" if es_ruta_destacada else None,
                )
            )

    # Dibujar nodos
    for node in nodes:
        es_nodo_ruta = node["id"] in nodos_en_ruta

        if es_nodo_ruta:
            marker_size = 20 if node["tipo"] == "Almacen" else 15
            marker_color = "#FF4B4B"
            marker_symbol = "square" if node["tipo"] == "Almacen" else "circle"
            border_color = "white"
            border_width = 2
            opacity = 1.0
            font_color = "white"
            font_size = 12
            font_family = "Arial Black"
        else:
            marker_size = 15 if node["tipo"] == "Almacen" else 10
            marker_color = color_map.get(node["tipo"], "gray")
            marker_symbol = "square" if node["tipo"] == "Almacen" else "circle"
            border_color = "rgba(0,0,0,0.3)"
            border_width = 1
            opacity = 0.8
            font_color = "black"
            font_size = 10
            font_family = "Arial"

        fig.add_trace(
            go.Scatter(
                x=[node["x"]],
                y=[node["y"]],
                mode="markers+text",
                marker=dict(
                    size=marker_size,
                    color=marker_color,
                    symbol=marker_symbol,
                    line=dict(color=border_color, width=border_width),
                ),
                text=node["id"],
                textposition="top center",
                textfont=dict(color=font_color, size=font_size, family=font_family),
                opacity=opacity,
                name=node["tipo"],
                legendgroup=node["tipo"],
                showlegend=False,
                hoverinfo="text",
                hovertext=f"<b>{node['nombre']}</b><br>Tipo: {node['tipo']}<br>ID: {node['id']}",
            )
        )

    # Leyenda...
    if ruta_destacada:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                line=dict(color="#FF4B4B", width=4),
                name="🚚 Ruta Óptima",
                showlegend=True,
            )
        )
        if len(nodos_en_ruta) >= 2:
            fig.add_trace(
                go.Scatter(
                    x=[None],
                    y=[None],
                    mode="markers",
                    marker=dict(
                        size=15,
                        color="#FF4B4B",
                        symbol="star",
                        line=dict(color="white", width=2),
                    ),
                    name="⭐ Origen/Destino",
                    showlegend=True,
                )
            )

    fig.update_layout(
        xaxis_title="Coordenada X",
        yaxis_title="Coordenada Y",
        hovermode="closest",
        height=700,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.2)",
            borderwidth=1,
        ),
    )
    fig.update_xaxes(range=[0, 100])
    fig.update_yaxes(range=[0, 100])
    fig.update_layout(autosize=True, margin=dict(l=20, r=20, t=40, b=20))

    return fig
