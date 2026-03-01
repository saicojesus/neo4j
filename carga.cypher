// ==========================================
// PROYECTO III - LOGISTICS OPTIMIZER
// CARGA INICIAL DE DATOS (Versión mejorada)
// ==========================================

// 1. LIMPIEZA TOTAL
MATCH (n) DETACH DELETE n;

// ==========================================
// 2. CREACIÓN DE RESTRICCIONES E ÍNDICES
// ==========================================
CREATE CONSTRAINT IF NOT EXISTS FOR (a:Almacen) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (i:Interseccion) REQUIRE i.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (p:PuntoEntrega) REQUIRE p.id IS UNIQUE;

// ==========================================
// 3. GENERACIÓN DE NODOS CON COORDENADAS ORGANIZADAS
// ==========================================

// A. Crear 5 Almacenes (en posiciones estratégicas)
CREATE (:Almacen {id: 'A1', nombre: 'Centro Distribución Norte', x: 20, y: 80, tipo: 'HUB', capacidad_total: 300});
CREATE (:Almacen {id: 'A2', nombre: 'Centro Distribución Sur', x: 80, y: 20, tipo: 'HUB', capacidad_total: 300});
CREATE (:Almacen {id: 'A3', nombre: 'Centro Distribución Este', x: 80, y: 80, tipo: 'HUB', capacidad_total: 300});
CREATE (:Almacen {id: 'A4', nombre: 'Centro Distribución Oeste', x: 20, y: 20, tipo: 'HUB', capacidad_total: 300});
CREATE (:Almacen {id: 'A5', nombre: 'Centro Distribución Central', x: 50, y: 50, tipo: 'HUB', capacidad_total: 500});

// B. Crear 20 Intersecciones (en una cuadrícula)
UNWIND range(1, 4) AS i
UNWIND range(1, 5) AS j
CREATE (:Interseccion {
    id: 'I' + ((i-1)*5 + j),
    nombre: 'Cruce ' + ((i-1)*5 + j),
    x: 10 + i * 20,
    y: 10 + j * 15,
    tipo: 'CRUCE',
    semaforo: rand() > 0.3
});

// C. Crear 25 Puntos de Entrega (distribuidos en clusters)
// Cluster 1: Zona Norte
UNWIND range(1, 6) AS i
CREATE (:PuntoEntrega {
    id: 'P' + i,
    nombre: 'Cliente Norte ' + i,
    x: 15 + toInteger(rand() * 20),
    y: 70 + toInteger(rand() * 15),
    demanda: 1 + toInteger(rand() * 8),
    prioridad: ['Alta', 'Media', 'Baja'][toInteger(rand() * 3)]
});

// Cluster 2: Zona Sur
UNWIND range(7, 12) AS i
CREATE (:PuntoEntrega {
    id: 'P' + i,
    nombre: 'Cliente Sur ' + (i-6),
    x: 65 + toInteger(rand() * 20),
    y: 15 + toInteger(rand() * 15),
    demanda: 1 + toInteger(rand() * 8),
    prioridad: ['Alta', 'Media', 'Baja'][toInteger(rand() * 3)]
});

// Cluster 3: Zona Este
UNWIND range(13, 18) AS i
CREATE (:PuntoEntrega {
    id: 'P' + i,
    nombre: 'Cliente Este ' + (i-12),
    x: 70 + toInteger(rand() * 15),
    y: 60 + toInteger(rand() * 20),
    demanda: 1 + toInteger(rand() * 8),
    prioridad: ['Alta', 'Media', 'Baja'][toInteger(rand() * 3)]
});

// Cluster 4: Zona Oeste
UNWIND range(19, 25) AS i
CREATE (:PuntoEntrega {
    id: 'P' + i,
    nombre: 'Cliente Oeste ' + (i-18),
    x: 10 + toInteger(rand() * 15),
    y: 30 + toInteger(rand() * 20),
    demanda: 1 + toInteger(rand() * 8),
    prioridad: ['Alta', 'Media', 'Baja'][toInteger(rand() * 3)]
});

// ==========================================
// 4. GENERACIÓN DE RELACIONES CONECTA_A (más selectiva)
// ==========================================

// Conectar nodos cercanos con distancia controlada
MATCH (n1), (n2)
WHERE id(n1) < id(n2)
  AND abs(n1.x - n2.x) < 25
  AND abs(n1.y - n2.y) < 25
WITH n1, n2,
     sqrt((n1.x - n2.x)^2 + (n1.y - n2.y)^2) AS dist,
     rand() AS random_factor
WHERE dist < 30 AND dist > 5
CREATE (n1)-[:CONECTA_A {
    distancia: round(dist * 100) / 100.0,
    tiempo_estimado: 5 + toInteger(dist * 1.5),
    estado_trafico: round((0.2 + random_factor * 0.7) * 100) / 100.0,
    capacidad_max_ton: CASE
        WHEN dist < 10 THEN 40
        WHEN dist < 20 THEN 20
        ELSE 10
    END,
    tipo_via: CASE
        WHEN dist > 20 THEN 'Autopista'
        WHEN dist > 10 THEN 'Avenida'
        ELSE 'Calle'
    END,
    tiene_peaje: random_factor > 0.8,
    costo_peaje: CASE
        WHEN random_factor > 0.8 THEN round(50 + rand() * 100)
        ELSE 0
    END
}]->(n2);

// ==========================================
// 5. CONEXIONES ESTRATÉGICAS (para asegurar conectividad)
// ==========================================

// Conectar almacenes entre sí (rutas principales)
MATCH (a1:Almacen), (a2:Almacen)
WHERE a1 <> a2
WITH a1, a2, sqrt((a1.x - a2.x)^2 + (a1.y - a2.y)^2) AS dist
CREATE (a1)-[:CONECTA_A {
    distancia: round(dist * 100) / 100.0,
    tiempo_estimado: 10 + toInteger(dist * 1.0),
    estado_trafico: 0.3,
    capacidad_max_ton: 40,
    tipo_via: 'Autopista',
    ruta_principal: true,
    tiene_peaje: false
}]->(a2);

// Conectar cada almacén con intersecciones cercanas
MATCH (a:Almacen), (i:Interseccion)
WHERE abs(a.x - i.x) < 30 AND abs(a.y - i.y) < 30
WITH a, i, sqrt((a.x - i.x)^2 + (a.y - i.y)^2) AS dist
CREATE (a)-[:CONECTA_A {
    distancia: round(dist * 100) / 100.0,
    tiempo_estimado: 5 + toInteger(dist * 1.2),
    estado_trafico: 0.2,
    capacidad_max_ton: 30,
    tipo_via: 'Avenida',
    conexion_acceso: true
}]->(i);

// ==========================================
// 6. PRE-CÁLCULO DE PESOS
// ==========================================
MATCH ()-[r:CONECTA_A]->()
SET
    r.peso_distancia = r.distancia,
    r.peso_tiempo = r.distancia * (1 + r.estado_trafico),
    r.peso_costo = r.distancia * (1 + r.estado_trafico) + (r.costo_peaje / 100.0),
    r.peso_final = r.distancia * (1 + r.estado_trafico);

// ==========================================
// 7. VERIFICACIÓN
// ==========================================
MATCH (a:Almacen) WITH count(a) AS Almacenes
MATCH (i:Interseccion) WITH Almacenes, count(i) AS Intersecciones
MATCH (p:PuntoEntrega) WITH Almacenes, Intersecciones, count(p) AS PuntosEntrega
MATCH ()-[r:CONECTA_A]->() WITH Almacenes, Intersecciones, PuntosEntrega, count(r) AS Conexiones
RETURN '✅ Carga completada exitosamente' AS Mensaje,
       Almacenes,
       Intersecciones,
       PuntosEntrega,
       Conexiones;
