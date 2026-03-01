import os

import streamlit as st
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]


@st.cache_resource
def init_connection():
    """Inicializa la conexión a Neo4j (cacheada)"""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password123")
    return Neo4jConnection(uri, user, password)


def test_connection(conn):
    """Prueba la conexión a Neo4j"""
    try:
        result = conn.query("RETURN 'Conexión exitosa' as mensaje")
        return True, result[0]["mensaje"]
    except Exception as e:
        return False, str(e)
