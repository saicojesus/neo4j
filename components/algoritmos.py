import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# --- MODIFICADO: La función ahora no muestra nada, solo calcula y devuelve los datos ---
def ejecutar_algoritmos(conn, origen_id, destino_id, algoritmo, capacidad):
    """Ejecuta los algoritmos de ruteo seleccionados y devuelve los resultados."""

    if not crear_proyeccion(conn):
        st.error("No se pudo crear la proyección del grafo")
        return None, None

    ruta_para_mapa = None
    resultados_para_display = {}

    try:
        if algoritmo == "Dijkstra (Distancia)":
            res_dijkstra = ejecutar_dijkstra(conn, origen_id, destino_id)
            resultados_para_display["dijkstra"] = res_dijkstra
            ruta_para_mapa = res_dijkstra

        elif algoritmo == "A* (Tiempo + Tráfico)":
            res_astar = ejecutar_astar(conn, origen_id, destino_id)
            resultados_para_display["astar"] = res_astar
            ruta_para_mapa = res_astar

        else:  # Comparar ambos
            res_dijkstra = ejecutar_dijkstra(conn, origen_id, destino_id)
            res_astar = ejecutar_astar(conn, origen_id, destino_id)
            resultados_para_display["dijkstra"] = res_dijkstra
            resultados_para_display["astar"] = res_astar

            # Lógica para decidir qué ruta resaltar en el mapa (sin cambios)
            if res_dijkstra and res_astar:
                if (
                    res_dijkstra["distancia_total"]
                    < res_astar.get("tiempo_total", float("inf")) / 1.2
                ):
                    ruta_para_mapa = res_dijkstra
                else:
                    ruta_para_mapa = res_astar
            elif res_dijkstra:
                ruta_para_mapa = res_dijkstra
            elif res_astar:
                ruta_para_mapa = res_astar

    finally:
        # Limpiar proyección
        limpiar_proyeccion(conn)

    # Devuelve la ruta para pintar en el mapa y todos los datos para mostrar en la UI
    return ruta_para_mapa, resultados_para_display


def crear_proyeccion(conn):
    """Crea la proyección del grafo en memoria con todas las propiedades necesarias"""
    try:
        # Primero intentamos eliminar la proyección si existe
        try:
            conn.query("CALL gds.graph.drop('myGraph')")
        except:
            pass  # Ignorar si no existe

        # Crear nueva proyección
        conn.query("""
            CALL gds.graph.project(
                'myGraph',
                {
                    Almacen: { label: 'Almacen', properties: ['x', 'y'] },
                    Interseccion: { label: 'Interseccion', properties: ['x', 'y'] },
                    PuntoEntrega: { label: 'PuntoEntrega', properties: ['x', 'y'] }
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
    """
    Ejecuta Dijkstra para encontrar la ruta más CORTA en distancia
    y ADEMÁS calcula el tiempo REAL de esa ruta.
    """
    query = """
    MATCH (source {id: $origen}), (target {id: $destino})
    CALL gds.shortestPath.dijkstra.stream('myGraph', {
        sourceNode: source,
        targetNode: target,
        relationshipWeightProperty: 'peso_distancia'
    })
    YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs, path
    RETURN
        // 1. La distancia total (basada en 'peso_distancia')
        totalCost as distancia_total,

        // 2. <-- NUEVA LÍNEA: Calculamos el tiempo real de la ruta encontrada
        // Usamos REDUCE para sumar el 'peso_tiempo' de cada relación en el camino
        REDUCE(tiempoTotal = 0.0, rel IN relationships(path) | tiempoTotal + rel.peso_tiempo) AS tiempo_real_total,

        // 3. El resto de los datos que ya tenías
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
    """Muestra resultado de Dijkstra usando el tiempo real calculado."""
    if not resultado:
        st.warning("No se encontró una ruta con Dijkstra")
        return

    st.subheader("📊 Resultado Dijkstra (Ruta más corta por Distancia)")

    cols = st.columns(4)

    with cols[0]:
        st.metric("📏 Distancia Total", f"{resultado['distancia_total']:.2f} km")

    with cols[1]:
        st.metric("📍 Paradas", len(resultado["ruta_nodos"]))

    # --- MODIFICADO: Usar el tiempo real para calcular la velocidad promedio ---
    # Esto dará una velocidad mucho más realista
    with cols[2]:
        tiempo_en_horas = resultado["tiempo_real_total"] / 60
        velocidad = (
            resultado["distancia_total"]
            / max(tiempo_en_horas, 0.01)  # Evitar división por cero
        )
        st.metric("⚡ Velocidad Promedio", f"{velocidad:.1f} km/h")

    # --- MODIFICADO: Mostrar el tiempo real en lugar del estimado ---
    with cols[3]:
        # Ya no hacemos: tiempo_est = resultado["distancia_total"] * 1.2
        # Ahora usamos el valor real de la consulta:
        st.metric(
            "⏱️ Tiempo Real (Ruta Corta)", f"{resultado['tiempo_real_total']:.1f} min"
        )

    st.divider()

    # (El resto de la función para mostrar la tabla de la ruta no necesita cambios)
    st.markdown("### 🛣️ Secuencia de la Ruta")
    ruta_data = []
    for i, (nombre, nodo_id) in enumerate(
        zip(resultado["ruta_nombres"], resultado["ruta_nodos"])
    ):
        tipo = (
            "🏁 Origen"
            if i == 0
            else "🎯 Destino"
            if i == len(resultado["ruta_nombres"]) - 1
            else "⏺️ Intermedio"
        )
        ruta_data.append({"Paso": i + 1, "Tipo": tipo, "Nombre": nombre, "ID": nodo_id})
    st.dataframe(pd.DataFrame(ruta_data), use_container_width=True, hide_index=True)


def mostrar_resultado_astar(resultado):
    """Muestra resultado de A*"""
    if not resultado:
        st.warning("No se encontró una ruta con A*")
        return
    st.subheader("📊 Resultado A* (Basado en Tiempo + Tráfico)")
    cols = st.columns(4)
    with cols[0]:
        st.metric("⏱️ Tiempo Estimado", f"{resultado['tiempo_total']:.2f} min")
    with cols[1]:
        st.metric("📍 Paradas", len(resultado["ruta_nodos"]))
    with cols[2]:
        tiempo_por_parada = resultado["tiempo_total"] / max(
            len(resultado["ruta_nodos"]), 1
        )
        st.metric("⏱️ Tiempo/Parada", f"{tiempo_por_parada:.1f} min")
    with cols[3]:
        dist_est = resultado["tiempo_total"] / 1.2
        st.metric("📏 Distancia Estimada", f"{dist_est:.1f} km")
    st.divider()
    st.markdown("### 🛣️ Secuencia de la Ruta")
    ruta_data = []
    for i, (nombre, nodo_id) in enumerate(
        zip(resultado["ruta_nombres"], resultado["ruta_nodos"])
    ):
        tipo = (
            "🏁 Origen"
            if i == 0
            else "🎯 Destino"
            if i == len(resultado["ruta_nombres"]) - 1
            else "⏺️ Intermedio"
        )
        ruta_data.append({"Paso": i + 1, "Tipo": tipo, "Nombre": nombre, "ID": nodo_id})
    st.dataframe(pd.DataFrame(ruta_data), use_container_width=True, hide_index=True)


def mostrar_comparacion(dijkstra, astar):
    """Muestra comparación entre ambos algoritmos"""
    if not dijkstra and not astar:
        st.warning("No se encontraron rutas con ninguno de los algoritmos")
        return
    st.divider()
    st.subheader("📊 Comparación de Algoritmos")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if dijkstra:
            st.metric("📏 Dijkstra Distancia", f"{dijkstra['distancia_total']:.1f} km")
    with col2:
        if dijkstra:
            st.metric("📍 Dijkstra Paradas", len(dijkstra["ruta_nodos"]))
    with col3:
        if astar:
            st.metric("⏱️ A* Tiempo", f"{astar['tiempo_total']:.1f} min")
    with col4:
        if astar:
            st.metric("📍 A* Paradas", len(astar["ruta_nodos"]))
    st.divider()
    if dijkstra or astar:
        col_ruta1, col_ruta2 = st.columns(2)
        with col_ruta1:
            if dijkstra:
                st.markdown("### 🟢 Ruta Dijkstra")
                for i, nombre in enumerate(dijkstra["ruta_nombres"], 1):
                    emoji = (
                        "🏁"
                        if i == 1
                        else "🎯"
                        if i == len(dijkstra["ruta_nombres"])
                        else "⏺️"
                    )
                    st.markdown(f"{emoji} **{i}. {nombre}**")
        with col_ruta2:
            if astar:
                st.markdown("### 🔵 Ruta A*")
                for i, nombre in enumerate(astar["ruta_nombres"], 1):
                    emoji = (
                        "🏁"
                        if i == 1
                        else "🎯"
                        if i == len(astar["ruta_nombres"])
                        else "⏺️"
                    )
                    st.markdown(f"{emoji} **{i}. {nombre}**")
    if dijkstra and astar:
        st.divider()
        st.subheader("📈 Análisis Comparativo")
        distancia_dijkstra = dijkstra["distancia_total"]
        tiempo_astar = astar["tiempo_total"]
        tiempo_estimado_dijkstra = distancia_dijkstra * 1.2
        distancia_estimada_astar = tiempo_astar / 1.2
        df_comp = pd.DataFrame(
            {
                "Algoritmo": ["Dijkstra", "A*", "Dijkstra", "A*"],
                "Métrica": ["Distancia (km)"] * 2 + ["Tiempo (min)"] * 2,
                "Valor": [
                    distancia_dijkstra,
                    distancia_estimada_astar,
                    tiempo_estimado_dijkstra,
                    tiempo_astar,
                ],
            }
        )
        fig = px.bar(
            df_comp,
            x="Métrica",
            y="Valor",
            color="Algoritmo",
            barmode="group",
            color_discrete_map={"Dijkstra": "#2ECC71", "A*": "#3498DB"},
            text_auto=".1f",
        )
        fig.update_layout(
            height=400,
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5
            ),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.divider()
        st.subheader("🎯 Recomendación")
        diff_dist = abs(distancia_dijkstra - distancia_estimada_astar)
        diff_tiempo = abs(tiempo_estimado_dijkstra - tiempo_astar)
        if diff_dist < 1 and diff_tiempo < 1:
            st.info(
                f"**⚖️ Rutas equivalentes** | Diferencia: {diff_dist:.2f} km, {diff_tiempo:.2f} min"
            )
        elif distancia_dijkstra < distancia_estimada_astar:
            st.success(f"**✅ Dijkstra** | Ahorra {diff_dist:.2f} km en distancia")
        else:
            st.success(f"**✅ A*** | Ahorra {diff_tiempo:.2f} min en tiempo")
