import plotly.graph_objects as go
import streamlit as st


def render_grafo(conn, ruta_destacada=None, titulo="Mapa de Rutas"):
    """Renderiza la visualización del grafo con opción de resaltar una ruta"""

    with st.expander("🗺️ Ver mapa completo de rutas", expanded=True):
        nodes = get_nodes(conn)
        edges = get_edges(conn)

        if not nodes:
            st.warning("No hay nodos para visualizar")
            return

        # Crear figura con la ruta destacada si existe
        fig = crear_figura_grafo(nodes, edges, ruta_destacada)

        # Agregar título dinámico
        if ruta_destacada:
            fig.update_layout(
                title=f"🗺️ {titulo} - Ruta Óptima Resaltada",
                title_font=dict(color="#2E86AB", size=16),
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


def get_edges(conn):
    """Obtiene relaciones del grafo"""
    try:
        return conn.query("""
            MATCH (n1)-[r:CONECTA_A]->(n2)
            RETURN n1.id as source,
                   n2.id as target,
                   r.distancia as distancia,
                   r.estado_trafico as trafico,
                   r.tiempo_estimado as tiempo
            LIMIT 200
        """)
    except Exception as e:
        st.error(f"Error cargando relaciones: {e}")
        return []


def crear_figura_grafo(nodes, edges, ruta_destacada=None):
    """Crea la figura de Plotly para el grafo con opción de resaltar ruta"""
    fig = go.Figure()

    color_map = {"Almacen": "red", "PuntoEntrega": "blue", "Interseccion": "green"}

    # Crear un diccionario para acceso rápido a nodos
    nodes_dict = {node["id"]: node for node in nodes}

    # Identificar nodos en la ruta destacada
    nodos_en_ruta = set()
    aristas_en_ruta = set()

    if ruta_destacada and "ruta_nodos" in ruta_destacada:
        nodos_en_ruta = set(ruta_destacada["ruta_nodos"])
        # Crear pares de aristas consecutivas
        for i in range(len(ruta_destacada["ruta_nodos"]) - 1):
            aristas_en_ruta.add(
                (ruta_destacada["ruta_nodos"][i], ruta_destacada["ruta_nodos"][i + 1])
            )

    # Primero dibujar todas las aristas (en segundo plano)
    for edge in edges:
        source_node = nodes_dict.get(edge["source"])
        target_node = nodes_dict.get(edge["target"])

        if source_node and target_node:
            # Determinar si esta arista está en la ruta
            es_ruta_destacada = (edge["source"], edge["target"]) in aristas_en_ruta or (
                edge["target"],
                edge["source"],
            ) in aristas_en_ruta

            # Configurar estilo según si es ruta destacada o no
            if es_ruta_destacada:
                line_color = "#FF4B4B"  # Rojo brillante
                line_width = 4
                opacity = 1.0
                hover_text = f"🚚 **RUTA ÓPTIMA**<br>Distancia: {edge['distancia']:.2f} km<br>Tráfico: {edge['trafico']:.2f}<br>Tiempo: {edge.get('tiempo', 0):.0f} min"
            else:
                line_color = "rgba(150,150,150,0.3)"
                line_width = 1 + (edge["trafico"] * 2)
                opacity = 0.4
                hover_text = f"Distancia: {edge['distancia']:.2f} km<br>Tráfico: {edge['trafico']:.2f}<br>Tiempo: {edge.get('tiempo', 0):.0f} min"

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

    # Luego dibujar todos los nodos (encima de las aristas)
    for node in nodes:
        # Determinar si este nodo está en la ruta
        es_nodo_ruta = node["id"] in nodos_en_ruta

        # Configurar estilo según si es nodo de ruta
        if es_nodo_ruta:
            marker_size = 20 if node["tipo"] == "Almacen" else 15
            marker_color = "#FF4B4B"  # Rojo brillante
            marker_symbol = "square" if node["tipo"] == "Almacen" else "circle"
            border_color = "white"
            border_width = 2
            opacity = 1.0
            font_color = "white"
            font_size = 12
            font_family = "Arial Black"  # Para simular negrita
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

    # Agregar leyenda personalizada para la ruta óptima
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

        # Agregar origen y destino a la leyenda
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
        title="Mapa de Rutas",
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
            font=dict(size=12),
        ),
    )

    fig.update_xaxes(range=[0, 100])  # Fijar rango X
    fig.update_yaxes(range=[0, 100])  # Fijar rango Y
    fig.update_layout(
        autosize=True,
        margin=dict(l=20, r=20, t=40, b=20),
    )

    return fig
