import heapq
from collections import defaultdict


def dijkstra(graph, start_nodes, goal_nodes, blocked_edges=None, blocked_nodes=None):
    """
    Multi-source, multi-target Dijkstra on a directed weighted graph.

    graph        : {node: [(neighbor, cost), ...]}
    start_nodes  : iterable of nodes — all initialised at cost 0
    goal_nodes   : set of acceptable destination nodes
    blocked_edges: set of (src, dst) pairs to skip
    blocked_nodes: set of nodes to skip (treated as absent)

    Returns (total_cost, path) or None.
    path is [first_node, ..., goal_node].
    """
    if blocked_edges is None:
        blocked_edges = frozenset()
    if blocked_nodes is None:
        blocked_nodes = frozenset()

    goal_nodes = frozenset(goal_nodes)
    dist = {}
    prev = {}
    pq = []

    for node in start_nodes:
        if node not in blocked_nodes:
            dist[node] = 0.0
            heapq.heappush(pq, (0.0, node))

    while pq:
        cost, node = heapq.heappop(pq)
        if cost > dist.get(node, float('inf')):
            continue
        if node in goal_nodes:
            path, cur = [], node
            while cur is not None:
                path.append(cur)
                cur = prev.get(cur)
            path.reverse()
            return cost, path
        for neighbor, ecost in graph.get(node, []):
            if neighbor in blocked_nodes:
                continue
            if (node, neighbor) in blocked_edges:
                continue
            new_cost = cost + ecost
            if new_cost < dist.get(neighbor, float('inf')):
                dist[neighbor] = new_cost
                prev[neighbor] = node
                heapq.heappush(pq, (new_cost, neighbor))
    return None


def k_rutas_optimas(graph, start_nodes, goal_nodes, k=7):
    """
    K-shortest paths: bloquea aristas de rutas previas para generar alternativas.

    Algoritmo:
    1. Encuentra la ruta óptima (Dijkstra sin bloqueos)
    2. Para cada ruta encontrada, bloquea sus aristas internas
    3. Ejecuta Dijkstra nuevamente sin esas aristas
    4. Repite hasta encontrar k rutas o agotarse las alternativas

    Retorna lista de (total_cost, path) ordenada por costo ascendente.
    """
    start_nodes = frozenset(start_nodes)
    goal_nodes  = frozenset(goal_nodes)

    rutas = []
    seen_paths = set()

    for iteration in range(k):
        # Bloquea aristas de todas las rutas previas
        blocked = frozenset()
        if iteration > 0:
            blocked = set()
            for prev_cost, prev_path in rutas:
                # Bloquea todas las aristas internas de la ruta previa
                for j in range(len(prev_path) - 1):
                    blocked.add((prev_path[j], prev_path[j + 1]))
            blocked = frozenset(blocked)

        result = dijkstra(graph, start_nodes, goal_nodes, blocked_edges=blocked)
        if result is None:
            break

        cost, path = result
        path_tuple = tuple(path)

        # Evita duplicados
        if path_tuple in seen_paths:
            break

        seen_paths.add(path_tuple)
        rutas.append((cost, path))

    return rutas
