
# 🚚 Logistics Optimizer - Smart Routing Dashboard

Este proyecto es una plataforma de optimización logística basada en **Grafos (Neo4j)** y **Streamlit**. Permite calcular rutas óptimas para vehículos de carga pesada, integrando restricciones físicas de las vías en tiempo real y comparando algoritmos de búsqueda de caminos.
## 🚀 Características Principales

- **Optimización de Rutas:** Implementación de algoritmos Dijkstra (Distancia mínima) y A* (Tiempo mínimo con tráfico).
- **Restricción de Carga:** Filtrado dinámico de aristas. Si un camión supera **X toneladas**, las rutas que no soportan ese peso quedan deshabilitadas para el cálculo y la visualización.
- **Visualización Interactiva:** Mapa dinámico basado en Plotly que resalta la ruta óptima encontrada.
- **Análisis Complejo:** Panel de estadísticas avanzadas sobre congestión, demanda y capacidad de la red vial.

## 🛠️ Tecnologías Utilizadas

- **Base de Datos:** Neo4j 5.15 (Community Edition).
- **Librerías de Grafos:** Graph Data Science (GDS) & APOC.
- **Frontend:** Streamlit (Python).
- **Visualización:** Plotly Graph Objects.
- **Infraestructura:** Podman / Docker.

## 📋 Requisitos Académicos Cumplidos

### 1. Modelo de Datos (Property Graph)
- **Nodos:** `Almacen` (Hubs), `PuntoEntrega` (Clientes), `Interseccion` (Cruces viales).
- **Relaciones:** `CONECTA_A` (Segmentos de vía con distancia, tiempo, tráfico y capacidad en toneladas).

### 2. Algoritmos de Caminos Mínimos
- **Dijkstra:** Optimizado para minimizar la distancia física total.
- **A*:** Optimizado para minimizar el tiempo real considerando el estado del tráfico, utilizando coordenadas cartesianas como heurística.

### 3. Consultas Complejas (Cypher)
Se integraron 5 consultas avanzadas que utilizan:
- **WITH & Agregaciones:** Cálculo de niveles de tráfico y promedios de distancia.
- **UNWIND:** Desglose de colecciones de clientes para análisis de demanda por prioridad.
- **GDS Cypher Projections:** Creación de grafos en memoria filtrados por peso en tiempo real.

## 🔧 Configuración y Ejecución

### Pre-requisitos
- Python 3.10+
- Podman o Docker

### Paso 1: Levantar Neo4j
El sistema requiere Neo4j con los plugins APOC y GDS activos.
```bash
podman-compose up -d
```

### Paso 2: Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### Paso 3: Ejecutar la Aplicación
```bash
streamlit run app.py
```

## 🔍 Detalles Técnicos de la Restricción de Carga
El sistema implementa un filtrado en tiempo real mediante **Proyecciones Cypher de GDS**. Al cambiar la carga en el Dashboard, se ejecuta la siguiente lógica:
1. Se destruye la proyección de grafo anterior.
2. Se crea una nueva proyección cargando únicamente las relaciones donde `r.capacidad_max_ton >= carga_seleccionada`.
3. Los algoritmos de enrutamiento solo consideran las vías legalmente transitables para ese vehículo.

## 📁 Estructura del Proyecto
- `/components`: Módulos de conexión, algoritmos, consultas y visualización.
- `app.py`: Punto de entrada de la interfaz Streamlit.
- `compose.yml`: Configuración de infraestructura contenerizada.
- `plugins/`: Carpeta para extensiones de Neo4j (.gitignore activo para evitar binarios pesados).
