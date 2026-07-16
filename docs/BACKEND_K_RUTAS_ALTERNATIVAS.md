# BACKEND — De ruta única a K-rutas alternativas reales
> Impacta: `bus_backend`
> Problema actual: el endpoint `ruta-optima` devuelve solo 1 ruta (la óptima). Debe devolver la óptima + hasta 6 alternativas reales, todas existentes en el grafo construido desde la BD (Excel). Nada de rutas inventadas o sintéticas.

---

## DIAGNÓSTICO DEL PROBLEMA ACTUAL

Dijkstra estándar, por diseño, solo encuentra **un** camino mínimo por nodo destino. Para obtener varias rutas reales y distintas hace falta un algoritmo de K-caminos más cortos (K-shortest paths), no solo correr Dijkstra una vez.

El algoritmo correcto para esto es **Yen's Algorithm**, que se apoya en Dijkstra como subrutina pero genera variaciones reales del grafo (bloqueando aristas/nodos ya usados) para forzar caminos alternativos genuinos — no inventados, solo otras combinaciones de aristas que ya existen en `LineasPuntos` y `PuntosTrasbordos`.

---

## ARCHIVOS A MODIFICAR

### `api/graph.py`

**Qué debe cambiar:** la función `dijkstra()` actual debe renombrarse o conservarse como subrutina de un camino único, y agregar una función nueva que orqueste múltiples llamadas para obtener K rutas.

Firma a agregar:
```python
def k_rutas_optimas(grafo: dict, origen_id: int, destino_id: int, k: int = 7) -> list:
    """
    Implementa Yen's Algorithm sobre el grafo multimodal (id_punto, id_linea_ruta).
    Usa dijkstra() como subrutina para encontrar el camino más corto en cada iteración.
    Retorna hasta k rutas, ordenadas por tiempo_total_min ascendente.
    La primera ruta es la óptima global; las siguientes son desviaciones válidas
    que reutilizan tramos reales del grafo, nunca aristas que no existen en la BD.
    """
```

Puntos a cuidar en la implementación:
- Cada ruta candidata debe poder reconstruirse completamente desde aristas reales de `LineasPuntos` (segmentos de línea) y `PuntosTrasbordos` (cambios de línea). Si una ruta candidata no puede completarse con aristas existentes, se descarta — no se rellena con datos ficticios.
- Yen's algorithm funciona "bloqueando" temporalmente nodos/aristas ya usados por rutas previas y volviendo a correr Dijkstra sobre el grafo restringido. Esa restricción debe hacerse sobre una copia del grafo, nunca modificando el grafo original que se cachea.
- Deduplicar: si dos iteraciones devuelven la misma secuencia exacta de puntos, no contarla dos veces.
- Limitar el tiempo de cómputo: si no hay más rutas alternativas reales disponibles (el grafo se agota antes de llegar a k), devolver las que sí existan — no forzar a 7 si solo hay 3 caminos posibles.

---

### `api/views.py`

**Qué debe cambiar:** el endpoint `ruta_optima` debe llamar a `k_rutas_optimas()` en vez de `dijkstra()` directamente, y aceptar un parámetro opcional para el número de rutas.

Firma de referencia (ajustar a la firma real ya existente):
```python
@api_view(['GET'])
def ruta_optima(request):
    # parámetros: origen, destino, k (opcional, default 7, max 7)
    # llama a k_rutas_optimas(grafo, origen, destino, k)
    # responde: lista de rutas con tiempo_total_min, trasbordos, segmentos
    # la primera ruta del array siempre es la más rápida
```

---

## CUIDADO CRÍTICO: IDA vs VUELTA

Cada línea tiene dos `LineaRuta` distintas (`IdRuta=1` Salida, `IdRuta=2` Retorno) con secuencias de puntos **diferentes y no intercambiables**. Verificar en el agente:

1. El grafo NO debe mezclar aristas de la ruta de ida con las de vuelta de la misma línea como si fueran la misma `linea_ruta`. Cada nodo del grafo se identifica por `(id_punto, id_linea_ruta)` — `id_linea_ruta` ya distingue ida de vuelta, pero confirmar que ninguna función agrupe por `id_linea` en vez de `id_linea_ruta` en algún punto del cálculo (esto colapsaría ida y vuelta y generaría rutas que no existen en la realidad).
2. Un trasbordo entre ida y vuelta de la MISMA línea en el mismo punto no tiene sentido físico (sería bajarse y subirse al mismo bus en sentido contrario) — revisar si `PuntosTrasbordos` ya excluye este caso o si hay que filtrarlo explícitamente al construir las aristas de trasbordo.
3. Al reconstruir los `segmentos` de cada ruta para la respuesta, cada segmento debe indicar explícitamente si es ida o vuelta (usar `id_ruta` de `LineaRuta`, no asumir por el nombre).

---

## VALIDACIÓN ANTES DE ENTREGAR

Pedir al agente que, antes de dar por cerrado el cambio, pruebe el endpoint con un par origen-destino donde se sabe que pasan varias líneas (ej. dos puntos cercanos al centro) y confirme:
- Se devuelven más de 1 ruta cuando existen alternativas reales
- Las rutas no se repiten
- Ninguna ruta usa una combinación de ida/vuelta inexistente en la BD
- El orden es estrictamente ascendente por tiempo total
