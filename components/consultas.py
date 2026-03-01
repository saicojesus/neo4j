import pandas as pd
import plotly.express as px
import streamlit as st


def render_consultas(conn):
    """Renderiza las pestañas de consultas complejas"""
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
        consulta_trafico(conn)

    with tab2:
        consulta_rutas_criticas(conn)

    with tab3:
        consulta_capacidad(conn)

    with tab4:
        consulta_congestion(conn)

    with tab5:
        consulta_demanda(conn)


def consulta_trafico(conn):
    st.subheader("Distribución del Tráfico por Ruta")

    query = """
    MATCH ()-[r:CONECTA_A]->()
    WITH r.estado_trafico as trafico, r.distancia as distancia
    WHERE trafico IS NOT NULL
    WITH
        CASE
            WHEN trafico < 0.3 THEN 'Bajo'
            WHEN trafico < 0.6 THEN 'Medio'
            ELSE 'Alto'
        END as nivel_trafico,
        distancia
    RETURN nivel_trafico,
           count(*) as cantidad,
           round(avg(distancia), 2) as distancia_promedio
    ORDER BY
        CASE nivel_trafico
            WHEN 'Bajo' THEN 1
            WHEN 'Medio' THEN 2
            WHEN 'Alto' THEN 3
        END
    """

    try:
        result = conn.query(query)
        df = pd.DataFrame(result)

        if not df.empty and df["cantidad"].sum() > 0:
            col1, col2 = st.columns(2)

            with col1:
                fig = px.pie(
                    df,
                    values="cantidad",
                    names="nivel_trafico",
                    title="Distribución por Nivel de Tráfico",
                    color_discrete_map={
                        "Bajo": "#2ECC71",
                        "Medio": "#F1C40F",
                        "Alto": "#E74C3C",
                    },
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.bar(
                    df,
                    x="nivel_trafico",
                    y="distancia_promedio",
                    title="Distancia Promedio por Nivel de Tráfico",
                    color="nivel_trafico",
                    color_discrete_map={
                        "Bajo": "#2ECC71",
                        "Medio": "#F1C40F",
                        "Alto": "#E74C3C",
                    },
                )
                st.plotly_chart(fig, use_container_width=True)

            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay datos de tráfico disponibles")
    except Exception as e:
        st.error(f"Error en consulta: {e}")


def consulta_rutas_criticas(conn):
    """Consulta 2: Top rutas más largas y congestionadas"""
    st.subheader("Top 10 Rutas Más Largas")

    query = """
    MATCH (n1)-[r:CONECTA_A]->(n2)
    RETURN n1.id as origen, n2.id as destino,
           r.distancia as distancia,
           r.estado_trafico as trafico,
           r.tiempo_estimado as tiempo
    ORDER BY r.distancia DESC
    LIMIT 10
    """

    try:
        result = conn.query(query)
        df = pd.DataFrame(result)

        if not df.empty:
            fig = px.bar(
                df,
                x="origen",
                y="distancia",
                color="trafico",
                hover_data=["destino", "tiempo"],
                title="Top 10 Rutas Más Largas",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay datos disponibles")
    except Exception as e:
        st.error(f"Error en consulta: {e}")


def consulta_capacidad(conn):
    """Consulta 3: Análisis de capacidad"""
    st.subheader("Rutas por Capacidad Máxima")

    capacidad_filter = st.slider(
        "Capacidad mínima (ton)", 0, 40, 10, key="capacidad_consulta"
    )

    query = f"""
    MATCH (n1)-[r:CONECTA_A]->(n2)
    WHERE r.capacidad_max_ton >= {capacidad_filter}
    RETURN r.capacidad_max_ton as capacidad,
           count(*) as cantidad,
           avg(r.distancia) as distancia_promedio
    ORDER BY capacidad
    """

    try:
        result = conn.query(query)
        df = pd.DataFrame(result)

        if not df.empty:
            col1, col2 = st.columns(2)

            with col1:
                fig = px.bar(
                    df,
                    x="capacidad",
                    y="cantidad",
                    title=f"Rutas por Capacidad (≥{capacidad_filter} ton)",
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.line(
                    df,
                    x="capacidad",
                    y="distancia_promedio",
                    title="Distancia Promedio por Capacidad",
                )
                st.plotly_chart(fig, use_container_width=True)

            st.dataframe(df, use_container_width=True)
        else:
            st.info(f"No hay rutas con capacidad ≥ {capacidad_filter} ton")
    except Exception as e:
        st.error(f"Error en consulta: {e}")


def consulta_congestion(conn):
    """Consulta 4: Puntos de congestión"""
    st.subheader("Intersecciones con Mayor Congestión")

    query = """
    MATCH (i:Interseccion)<-[r:CONECTA_A]-()
    WITH i,
         avg(r.estado_trafico) as trafico_promedio,
         count(r) as rutas_conectadas,
         avg(r.distancia) as distancia_promedio
    RETURN i.id as interseccion,
           trafico_promedio,
           rutas_conectadas,
           distancia_promedio
    ORDER BY trafico_promedio DESC
    LIMIT 10
    """

    try:
        result = conn.query(query)
        df = pd.DataFrame(result)

        if not df.empty:
            fig = px.bar(
                df,
                x="interseccion",
                y="trafico_promedio",
                color="rutas_conectadas",
                hover_data=["distancia_promedio"],
                title="Top 10 Intersecciones con Mayor Tráfico",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay datos disponibles")
    except Exception as e:
        st.error(f"Error en consulta: {e}")


def consulta_demanda(conn):
    """Consulta 5: Demanda por cliente"""
    st.subheader("Distribución de Demanda por Cliente")

    query = """
    MATCH (p:PuntoEntrega)
    RETURN p.nombre as cliente,
           p.demanda as demanda,
           p.prioridad as prioridad,
           p.x as x,
           p.y as y
    ORDER BY p.demanda DESC
    LIMIT 15
    """

    try:
        result = conn.query(query)
        df = pd.DataFrame(result)

        if not df.empty:
            col1, col2 = st.columns([2, 1])

            with col1:
                fig = px.bar(
                    df,
                    x="cliente",
                    y="demanda",
                    color="prioridad",
                    title="Demanda por Cliente",
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.scatter(
                    df,
                    x="x",
                    y="y",
                    size="demanda",
                    color="prioridad",
                    hover_name="cliente",
                    title="Ubicación de Clientes por Demanda",
                )
                st.plotly_chart(fig, use_container_width=True)

            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay datos disponibles")
    except Exception as e:
        st.error(f"Error en consulta: {e}")
