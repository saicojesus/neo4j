import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def ejecutar_algoritmos(conn, origen_id, destino_id, algoritmo, capacidad):
    """Ejecuta los algoritmos de ruteo seleccionados"""

    # Crear proyección del grafo con todas las propiedades necesarias
    if not crear_proyeccion(conn):
        st.error("No se pudo crear la proyección del grafo")
        return None

    resultado = None

    try:
        if algoritmo == "Dijkstra (Distancia)":
            resultado = ejecutar_dijkstra(conn, origen_id, destino_id)
            mostrar_resultado_dijkstra(resultado)

        elif algoritmo == "A* (Tiempo + Tráfico)":
            resultado = ejecutar_astar(conn, origen_id, destino_id)
            mostrar_resultado_astar(resultado)

        else:  # Comparar ambos
            resultado_dijkstra = ejecutar_dijkstra(conn, origen_id, destino_id)
            resultado_astar = ejecutar_astar(conn, origen_id, destino_id)
            mostrar_comparacion(resultado_dijkstra, resultado_astar)

            # Para comparación, mostramos el que tenga mejor métrica
            if resultado_dijkstra and resultado_astar:
                # Elegir el mejor según distancia (podrías cambiar criterio)
                if (
                    resultado_dijkstra["distancia_total"]
                    < resultado_astar.get("tiempo_total", float("inf")) / 1.2
                ):
                    resultado = resultado_dijkstra
                else:
                    resultado = resultado_astar
            elif resultado_dijkstra:
                resultado = resultado_dijkstra
            elif resultado_astar:
                resultado = resultado_astar

    finally:
        # Limpiar proyección
        limpiar_proyeccion(conn)

    return resultado


def crear_proyeccion(conn):
    """Crea la proyección del grafo en memoria con todas las propiedades necesarias"""
    try:
        # Primero intentamos eliminar la proyección si existe
        try:
            conn.query("CALL gds.graph.drop('myGraph')")
        except:
            pass  # Ignorar si no existe

        # Crear nueva proyección con todas las propiedades de nodos y relaciones
        conn.query("""
            CALL gds.graph.project(
                'myGraph',
                {
                    Almacen: {
                        label: 'Almacen',
                        properties: ['x', 'y']
                    },
                    Interseccion: {
                        label: 'Interseccion',
                        properties: ['x', 'y']
                    },
                    PuntoEntrega: {
                        label: 'PuntoEntrega',
                        properties: ['x', 'y']
                    }
                },
                {
                    CONECTA_A: {
                        orientation: 'NATURAL',
                        properties: ['peso_distancia', 'peso_tiempo', 'capacidad_max_ton', 'distancia', 'estado_trafico']
                    }
                }
            )
        """)
        return True
    except Exception as e:
        st.error(f"Error creando proyección: {e}")
        return False


def ejecutar_dijkstra(conn, origen_id, destino_id):
    """Ejecuta algoritmo de Dijkstra"""
    query = """
    MATCH (source {id: $origen}), (target {id: $destino})
    CALL gds.shortestPath.dijkstra.stream('myGraph', {
        sourceNode: source,
        targetNode: target,
        relationshipWeightProperty: 'peso_distancia'
    })
    YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs, path
    RETURN
        totalCost as distancia_total,
        [nodeId IN nodeIds | gds.util.asNode(nodeId).id] as ruta_nodos,
        [nodeId IN nodeIds | gds.util.asNode(nodeId).nombre] as ruta_nombres,
        [nodeId IN nodeIds | gds.util.asNode(nodeId).x] as coordenadas_x,
        [nodeId IN nodeIds | gds.util.asNode(nodeId).y] as coordenadas_y
    """

    try:
        result = conn.query(query, {"origen": origen_id, "destino": destino_id})
        return result[0] if result else None
    except Exception as e:
        st.error(f"Error en Dijkstra: {e}")
        return None


def ejecutar_astar(conn, origen_id, destino_id):
    """Ejecuta algoritmo A*"""
    # Primero verificamos que los nodos tengan coordenadas
    check_query = """
    MATCH (source {id: $origen}), (target {id: $destino})
    RETURN source.x IS NOT NULL AND source.y IS NOT NULL AS source_ok,
           target.x IS NOT NULL AND target.y IS NOT NULL AS target_ok
    """

    try:
        check = conn.query(check_query, {"origen": origen_id, "destino": destino_id})
        if check and check[0]:
            if not check[0]["source_ok"]:
                st.error("El nodo origen no tiene coordenadas válidas")
                return None
            if not check[0]["target_ok"]:
                st.error("El nodo destino no tiene coordenadas válidas")
                return None
    except Exception as e:
        st.warning(f"Verificación de coordenadas: {e}")

    query = """
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
        totalCost as tiempo_total,
        [nodeId IN nodeIds | gds.util.asNode(nodeId).id] as ruta_nodos,
        [nodeId IN nodeIds | gds.util.asNode(nodeId).nombre] as ruta_nombres
    """

    try:
        result = conn.query(query, {"origen": origen_id, "destino": destino_id})
        return result[0] if result else None
    except Exception as e:
        st.error(f"Error en A*: {e}")
        return None


def limpiar_proyeccion(conn):
    """Elimina la proyección del grafo"""
    try:
        conn.query("CALL gds.graph.drop('myGraph')")
    except:
        pass


def mostrar_resultado_dijkstra(resultado):
    """Muestra resultado de Dijkstra"""
    if not resultado:
        st.warning("No se encontró una ruta con Dijkstra")
        return

    with st.container():
        st.subheader("📊 Resultado Dijkstra (Basado en Distancia)")

        col1, col2 = st.columns([1, 2])

        with col1:
            st.metric("Distancia Total", f"{resultado['distancia_total']:.2f} km")

        with col2:
            st.metric("Cantidad de Paradas", len(resultado["ruta_nodos"]))

        st.write("**Secuencia de la Ruta:**")
        for i, (nombre, nodo_id) in enumerate(
            zip(resultado["ruta_nombres"], resultado["ruta_nodos"])
        ):
            st.write(f"{i + 1}. **{nombre}** ({nodo_id})")


def mostrar_resultado_astar(resultado):
    """Muestra resultado de A*"""
    if not resultado:
        st.warning("No se encontró una ruta con A*")
        return

    with st.container():
        st.subheader("📊 Resultado A* (Basado en Tiempo + Tráfico)")

        col1, col2 = st.columns([1, 2])

        with col1:
            st.metric("Tiempo Estimado", f"{resultado['tiempo_total']:.2f} min")

        with col2:
            st.metric("Cantidad de Paradas", len(resultado["ruta_nodos"]))

        st.write("**Secuencia de la Ruta:**")
        for i, (nombre, nodo_id) in enumerate(
            zip(resultado["ruta_nombres"], resultado["ruta_nodos"])
        ):
            st.write(f"{i + 1}. **{nombre}** ({nodo_id})")


def mostrar_comparacion(dijkstra, astar):
    """Muestra comparación entre ambos algoritmos de forma ordenada"""

    if not dijkstra and not astar:
        st.warning("No se encontraron rutas con ninguno de los algoritmos")
        return

    # Título de la sección
    st.markdown("---")
    st.subheader("📊 Comparación de Algoritmos")

    # Crear dos columnas para los algoritmos
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🟢 **Dijkstra**")
        st.markdown("*Basado en distancia*")

        if dijkstra:
            # Métricas principales
            st.metric(
                label="📏 Distancia Total",
                value=f"{dijkstra['distancia_total']:.2f} km",
            )

            # Detalles de la ruta
            with st.expander("🛣️ Ver ruta completa"):
                for i, nombre in enumerate(dijkstra["ruta_nombres"], 1):
                    st.markdown(f"{i}. **{nombre}**")

            # Estadísticas adicionales
            st.markdown("**📊 Estadísticas:**")
            st.markdown(f"- 📍 **Paradas:** {len(dijkstra['ruta_nodos'])}")
            st.markdown(
                f"- ⚡ **Velocidad promedio:** {(dijkstra['distancia_total'] / len(dijkstra['ruta_nodos']) * 10):.1f} km/h"
            )
        else:
            st.error("No se encontró ruta con Dijkstra")

    with col2:
        st.markdown("### 🔵 **A***")
        st.markdown("*Basado en tiempo + tráfico*")

        if astar:
            # Métricas principales
            st.metric(
                label="⏱️ Tiempo Estimado", value=f"{astar['tiempo_total']:.2f} min"
            )

            # Detalles de la ruta
            with st.expander("🛣️ Ver ruta completa"):
                for i, nombre in enumerate(astar["ruta_nombres"], 1):
                    st.markdown(f"{i}. **{nombre}**")

            # Estadísticas adicionales
            st.markdown("**📊 Estadísticas:**")
            st.markdown(f"- 📍 **Paradas:** {len(astar['ruta_nodos'])}")
            st.markdown(
                f"- 🚦 **Tráfico promedio:** {(astar.get('tiempo_total', 0) / len(astar['ruta_nodos']) / 5):.2f}"
            )
        else:
            st.error("No se encontró ruta con A*")

    # Análisis comparativo (solo si ambos algoritmos tienen resultados)
    if dijkstra and astar:
        st.markdown("---")
        st.subheader("📈 Análisis Comparativo")

        # Calcular métricas comparativas
        distancia_dijkstra = dijkstra["distancia_total"]
        tiempo_astar = astar["tiempo_total"]

        # Estimaciones para comparación
        tiempo_estimado_dijkstra = distancia_dijkstra * 1.2  # 50 km/h = 1.2 min/km
        distancia_estimada_astar = tiempo_astar / 1.2

        # Tarjetas de comparación
        col1, col2, col3 = st.columns(3)

        with col1:
            diferencia_dist = abs(distancia_dijkstra - distancia_estimada_astar)
            st.metric(
                label="📏 Diferencia en Distancia",
                value=f"{diferencia_dist:.2f} km",
                delta=f"{((diferencia_dist / distancia_dijkstra) * 100):.1f}%",
            )

        with col2:
            diferencia_tiempo = abs(tiempo_astar - tiempo_estimado_dijkstra)
            st.metric(
                label="⏱️ Diferencia en Tiempo",
                value=f"{diferencia_tiempo:.2f} min",
                delta=f"{((diferencia_tiempo / tiempo_astar) * 100):.1f}%",
            )

        with col3:
            # Calcular eficiencia (km por minuto)
            eficiencia_dijkstra = distancia_dijkstra / tiempo_estimado_dijkstra * 60
            eficiencia_astar = distancia_estimada_astar / tiempo_astar * 60
            st.metric(
                label="⚡ Eficiencia Promedio",
                value=f"{((eficiencia_dijkstra + eficiencia_astar) / 2):.1f} km/h",
            )

        # Tabla comparativa detallada
        st.markdown("---")
        st.subheader("📋 Tabla Comparativa Detallada")

        # Crear DataFrame para la tabla
        comparacion_df = pd.DataFrame(
            {
                "Métrica": [
                    "Distancia (km)",
                    "Tiempo estimado (min)",
                    "Número de paradas",
                    "Velocidad promedio (km/h)",
                ],
                "Dijkstra": [
                    f"{distancia_dijkstra:.2f}",
                    f"{tiempo_estimado_dijkstra:.2f}",
                    f"{len(dijkstra['ruta_nodos'])}",
                    f"{distancia_dijkstra / tiempo_estimado_dijkstra * 60:.1f}",
                ],
                "A*": [
                    f"{distancia_estimada_astar:.2f}",
                    f"{tiempo_astar:.2f}",
                    f"{len(astar['ruta_nodos'])}",
                    f"{distancia_estimada_astar / tiempo_astar * 60:.1f}",
                ],
            }
        )

        # Mostrar tabla estilizada
        st.dataframe(
            comparacion_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Métrica": st.column_config.TextColumn("Métrica", width="medium"),
                "Dijkstra": st.column_config.TextColumn("Dijkstra", width="small"),
                "A*": st.column_config.TextColumn("A*", width="small"),
            },
        )

        # Gráfico de barras comparativo
        st.markdown("---")
        st.subheader("📊 Visualización Comparativa")

        # Preparar datos para el gráfico
        metricas = ["Distancia (km)", "Tiempo (min)"]
        valores_dijkstra = [distancia_dijkstra, tiempo_estimado_dijkstra]
        valores_astar = [distancia_estimada_astar, tiempo_astar]

        fig = go.Figure(
            data=[
                go.Bar(
                    name="Dijkstra",
                    x=metricas,
                    y=valores_dijkstra,
                    marker_color="#2ECC71",
                    text=valores_dijkstra,
                    textposition="auto",
                ),
                go.Bar(
                    name="A*",
                    x=metricas,
                    y=valores_astar,
                    marker_color="#3498DB",
                    text=valores_astar,
                    textposition="auto",
                ),
            ]
        )

        fig.update_layout(
            title="Comparación de Métricas por Algoritmo",
            xaxis_title="Métrica",
            yaxis_title="Valor",
            barmode="group",
            height=400,
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )

        st.plotly_chart(fig, use_container_width=True)

        # Recomendación basada en los resultados
        st.markdown("---")
        st.subheader("🎯 Recomendación")

        if (
            distancia_dijkstra < distancia_estimada_astar * 0.9
        ):  # Dijkstra es 10% mejor en distancia
            st.success("""
            ✅ **Dijkstra** ofrece la ruta más corta en términos de distancia.

            *Recomendado cuando:* El costo de combustible es la principal preocupación.
            """)
        elif tiempo_astar < tiempo_estimado_dijkstra * 0.9:  # A* es 10% mejor en tiempo
            st.success("""
            ✅ **A*** ofrece el mejor tiempo de viaje considerando tráfico.

            *Recomendado cuando:* La puntualidad en las entregas es prioritaria.
            """)
        else:
            st.info("""
            ⚖️ **Ambos algoritmos** ofrecen rutas similares.

            *Puede elegir cualquiera basado en preferencias operativas.*
            """)
