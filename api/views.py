from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
import math
from collections import defaultdict

from .graph import k_rutas_optimas

from .models import (
    Linea, LineaPunto, Punto, PuntoTrasbordo,
    Conductor, Microbus, Recorrido, PosicionGPS,
)
from .serializers import (
    LineaSerializer, ConductorSerializer,
    MicrobusSerializer, PosicionGPSSerializer,
)

# ── UTILS ─────────────────────────────────────────────────────────────────────


def _haversine_km(lat1, lng1, lat2, lng2):
    R = 6_371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _metros(lat1, lng1, lat2, lng2):
    return _haversine_km(lat1, lng1, lat2, lng2) * 1000


def _stop_mas_cercano(lat, lng):
    stops = list(Punto.objects.filter(stop='S'))
    if not stops:
        return None
    return min(stops, key=lambda p: _metros(lat, lng, float(p.latitud), float(p.longitud)))


# ── LÍNEAS ────────────────────────────────────────────────────────────────────


@api_view(['GET'])
def lista_lineas(request):
    return Response(LineaSerializer(Linea.objects.all(), many=True).data)


@api_view(['GET'])
def lista_paradas(request):
    """Stops que pertenecen a al menos una ruta real (LineaPunto)."""
    lp_qs = list(
        LineaPunto.objects.all()
        .only('punto_id', 'punto_dest_id')
    )
    en_ruta = set()
    for lp in lp_qs:
        en_ruta.add(lp.punto_id)
        en_ruta.add(lp.punto_dest_id)

    paradas = list(
        Punto.objects.filter(stop='S', id__in=en_ruta)
        .values('id', 'latitud', 'longitud', 'descripcion')
    )
    return Response(paradas)


@api_view(['GET'])
def puntos_ruta(request, linea_ruta_id):
    lp_qs = list(
        LineaPunto.objects.filter(linea_ruta_id=linea_ruta_id)
        .select_related('punto', 'punto_dest')
        .order_by('orden')
    )
    if not lp_qs:
        return Response([])

    resultado = []
    for lp in lp_qs:
        resultado.append({
            'id': lp.punto.id,
            'latitud': str(lp.punto.latitud),
            'longitud': str(lp.punto.longitud),
            'descripcion': lp.punto.descripcion,
            'orden': lp.orden,
            'stop': lp.punto.stop,
        })
    ultimo = lp_qs[-1]
    resultado.append({
        'id': ultimo.punto_dest.id,
        'latitud': str(ultimo.punto_dest.latitud),
        'longitud': str(ultimo.punto_dest.longitud),
        'descripcion': ultimo.punto_dest.descripcion,
        'orden': ultimo.orden + 1,
        'stop': ultimo.punto_dest.stop,
    })
    return Response(resultado)


@api_view(['GET'])
def lineas_cercanas(request):
    try:
        lat = float(request.GET.get('lat'))
        lng = float(request.GET.get('lng'))
        radio = float(request.GET.get('radio', 300))
    except (TypeError, ValueError):
        return Response({'error': 'Parámetros inválidos'}, status=400)

    puntos_cercanos = [
        p.id for p in Punto.objects.all()
        if _metros(lat, lng, float(p.latitud), float(p.longitud)) <= radio
    ]
    lineas_ids = set(
        LineaPunto.objects.filter(punto_id__in=puntos_cercanos)
        .values_list('linea_ruta__linea_id', flat=True)
    )
    return Response(LineaSerializer(Linea.objects.filter(id__in=lineas_ids), many=True).data)


# ── BUSCAR RUTA — DIJKSTRA ────────────────────────────────────────────────────


@api_view(['POST'])
def buscar_ruta(request):
    """
    Body: { origen_lat, origen_lng, destino_lat, destino_lng }
    Construye el grafo desde LineaPunto + PuntoTrasbordo oficial.
    Ejecuta Yen's K-shortest paths (k=7) sobre nodo = (punto_id, linea_ruta_id).
    Devuelve hasta 6 rutas reales ordenadas por tiempo_total_min.
    """
    try:
        origen_lat  = float(request.data.get('origen_lat'))
        origen_lng  = float(request.data.get('origen_lng'))
        destino_lat = float(request.data.get('destino_lat'))
        destino_lng = float(request.data.get('destino_lng'))
    except (TypeError, ValueError):
        return Response({'error': 'Parámetros inválidos'}, status=400)

    # Cargar grafo primero para saber qué paradas están conectadas
    edges_ruta = list(
        LineaPunto.objects
        .select_related('linea_ruta__linea')
        .only('punto_id', 'punto_dest_id', 'linea_ruta_id', 'tiempo',
              'orden', 'linea_ruta__id', 'linea_ruta__linea__codigo',
              'linea_ruta__linea__color_linea')
    )
    if not edges_ruta:
        return Response({'error': 'No hay rutas configuradas'}, status=404)

    edges_tr = list(
        PuntoTrasbordo.objects
        .only('punto_id', 'linea_ruta_origen_id', 'linea_ruta_destino_id',
              'penalizacion_min')
    )

    linea_info = {}
    for lp in edges_ruta:
        if lp.linea_ruta_id not in linea_info:
            linea_info[lp.linea_ruta_id] = {
                'nombre': lp.linea_ruta.linea.codigo.strip(),
                'color':  lp.linea_ruta.linea.color_linea,
                'id_ruta': lp.linea_ruta.id_ruta,
            }

    _puntos_all  = list(Punto.objects.only('id', 'latitud', 'longitud', 'descripcion', 'stop'))
    punto_desc   = {p.id: (p.descripcion or f'Punto {p.id}') for p in _puntos_all}
    punto_coords = {p.id: (float(p.latitud), float(p.longitud)) for p in _puntos_all}

    # Secuencia completa de puntos por linea_ruta (incluye intermedios no-stop)
    # Para reconstruir polylines ricas sin depender del path de Dijkstra
    _lr_segs = defaultdict(list)
    for lp in edges_ruta:
        _lr_segs[lp.linea_ruta_id].append((lp.orden, lp.punto_id, lp.punto_dest_id))

    lr_route_pts = {}  # lr_id → [punto_id, ...] en orden de recorrido
    lr_pid_idx   = {}  # (lr_id, punto_id) → índice en lr_route_pts[lr_id]

    for lr_id, segs in _lr_segs.items():
        segs.sort(key=lambda x: x[0])
        seen, pts = set(), []
        for (_ord, pid, _pdid) in segs:
            if pid not in seen:
                seen.add(pid)
                pts.append(pid)
        last_pdid = segs[-1][2]
        if last_pdid not in seen:
            pts.append(last_pdid)
        lr_route_pts[lr_id] = pts
        for idx, pid in enumerate(pts):
            lr_pid_idx[(lr_id, pid)] = idx

    # Paradas que tienen aristas salientes (fuentes) vs cualquier stop en el grafo
    source_ids = {lp.punto_id for lp in edges_ruta}
    graph_ids  = source_ids | {lp.punto_dest_id for lp in edges_ruta}

    stops_source = [p for p in _puntos_all if p.id in source_ids and p.stop == 'S']
    stops_graph  = [p for p in _puntos_all if p.id in graph_ids  and p.stop == 'S']

    def _snap(lat, lng, candidates):
        if not candidates:
            return None
        return min(candidates, key=lambda p: _metros(lat, lng, float(p.latitud), float(p.longitud)))

    # Origen debe ser fuente (tiene aristas salientes); destino puede ser terminus
    origen_stop  = _snap(origen_lat,  origen_lng,  stops_source)
    destino_stop = _snap(destino_lat, destino_lng, stops_graph)

    if not origen_stop or not destino_stop:
        return Response({'error': 'No hay paradas disponibles'}, status=404)
    if origen_stop.id == destino_stop.id:
        return Response({'error': 'Origen y destino son la misma parada'}, status=400)

    # Construir grafo: nodo = (punto_id, linea_ruta_id)
    graph = defaultdict(list)
    edge_cost_map = {}

    # stop_lr[punto_id] = {linea_ruta_id, ...}  — para start_nodes y trasbordos geo
    stop_lr = defaultdict(set)
    for lp in edges_ruta:
        src  = (lp.punto_id, lp.linea_ruta_id)
        dst  = (lp.punto_dest_id, lp.linea_ruta_id)
        cost = float(lp.tiempo)
        graph[src].append((dst, cost))
        edge_cost_map[(src, dst)] = cost
        stop_lr[lp.punto_id].add(lp.linea_ruta_id)

    for tr in edges_tr:
        src  = (tr.punto_id, tr.linea_ruta_origen_id)
        dst  = (tr.punto_id, tr.linea_ruta_destino_id)
        cost = float(tr.penalizacion_min)
        graph[src].append((dst, cost))
        edge_cost_map[(src, dst)] = cost

    # Trasbordos solo por PuntoTrasbordo oficial del Excel (sin geo-transfers)

    origin_id = origen_stop.id
    dest_id   = destino_stop.id

    start_nodes = {(origin_id, lr_id) for lr_id in stop_lr.get(origin_id, set())}
    goal_lr_ids = {lp.linea_ruta_id for lp in edges_ruta
                   if lp.punto_id == dest_id or lp.punto_dest_id == dest_id}
    goal_nodes = {(dest_id, lr_id) for lr_id in goal_lr_ids}

    if not start_nodes or not goal_nodes:
        return Response([])

    # ── Reconstruir pasos desde el path ───────────────────────────────────────
    def _path_to_ruta(total_cost, path):
        pasos = []
        lineas_usadas = []
        trasbordos = 0
        i = 0
        while i < len(path):
            punto_id, lr_id = path[i]
            j = i + 1
            while j < len(path) and path[j][1] == lr_id:
                j += 1
            last_pid = path[j - 1][0]
            linea    = linea_info.get(lr_id, {'nombre': '?', 'color': '#000000'})
            seg_cost = sum(edge_cost_map.get((path[k], path[k + 1]), 0.0) for k in range(i, j - 1))
            if linea['nombre'] not in lineas_usadas:
                lineas_usadas.append(linea['nombre'])
            # Usar la secuencia completa de la ruta (incluye puntos intermedios)
            start_pid = path[i][0]
            s_idx = lr_pid_idx.get((lr_id, start_pid))
            e_idx = lr_pid_idx.get((lr_id, last_pid))
            if s_idx is not None and e_idx is not None and s_idx <= e_idx:
                seg_puntos = [
                    {'lat': punto_coords[pid][0], 'lng': punto_coords[pid][1]}
                    for pid in lr_route_pts[lr_id][s_idx:e_idx + 1]
                    if pid in punto_coords
                ]
            else:
                seg_puntos = [
                    {'lat': punto_coords[path[k][0]][0], 'lng': punto_coords[path[k][0]][1]}
                    for k in range(i, j)
                    if path[k][0] in punto_coords
                ]
            pasos.append({
                'tipo':       'ruta',
                'linea':      linea['nombre'],
                'color':      linea['color'],
                'id_ruta':    linea['id_ruta'],
                'desde_desc': punto_desc.get(punto_id, str(punto_id)),
                'hasta_desc': punto_desc.get(last_pid,  str(last_pid)),
                'tiempo_min': round(seg_cost, 1),
                'puntos':     seg_puntos,
            })
            if j < len(path) and path[j][1] != lr_id:
                next_lr   = path[j][1]
                next_pid  = path[j][0]
                next_info = linea_info.get(next_lr, {'nombre': '?', 'color': '#000000'})
                tr_cost   = edge_cost_map.get((path[j - 1], path[j]), 5.0)
                en_desc   = punto_desc.get(last_pid, str(last_pid))
                if next_pid != last_pid:
                    en_desc += f' → {punto_desc.get(next_pid, str(next_pid))}'
                pasos.append({
                    'tipo':            'transbordo',
                    'en_desc':         en_desc,
                    'de_linea':        linea['nombre'],
                    'a_linea':         next_info['nombre'],
                    'penalizacion_min': tr_cost,
                })
                trasbordos += 1
            i = j
        return {
            'tiempo_total_min': round(total_cost, 1),
            'trasbordos':       trasbordos,
            'lineas':           lineas_usadas,
            'origen_desc':      punto_desc.get(origin_id, str(origin_id)),
            'destino_desc':     punto_desc.get(dest_id,   str(dest_id)),
            'pasos':            pasos,
        }

    raw_rutas = k_rutas_optimas(graph, start_nodes, goal_nodes, k=7)
    rutas = [_path_to_ruta(cost, path) for cost, path in raw_rutas]
    rutas.sort(key=lambda r: r['tiempo_total_min'])
    return Response(rutas[:6])


# ── MICROBUSES ACTIVOS ────────────────────────────────────────────────────────


@api_view(['GET'])
def microbuses_activos(request):
    linea_id   = request.GET.get('linea')
    recorridos = Recorrido.objects.filter(estado='activo')
    if linea_id:
        recorridos = recorridos.filter(linea_ruta__linea_id=linea_id)

    resultado = []
    for rec in recorridos:
        ultima = rec.posiciones.filter(activo=True).first()
        if ultima:
            resultado.append({
                'recorrido_id': rec.id,
                'placa':        rec.microbus.placa,
                'latitud':      float(ultima.latitud),
                'longitud':     float(ultima.longitud),
                'velocidad':    ultima.velocidad,
                'timestamp':    ultima.timestamp,
            })
    return Response(resultado)


# ── CONDUCTORES ───────────────────────────────────────────────────────────────


@api_view(['POST'])
def registrar_conductor(request):
    s = ConductorSerializer(data=request.data)
    if s.is_valid():
        s.save()
        return Response(s.data, status=201)
    return Response(s.errors, status=400)


@api_view(['POST'])
def login_conductor(request):
    email    = request.data.get('email')
    password = request.data.get('password')
    try:
        c = Conductor.objects.get(email=email, password=password)
        return Response({'conductor_id': c.id, 'nombre': c.nombre, 'ci': c.ci})
    except Conductor.DoesNotExist:
        return Response({'error': 'Credenciales incorrectas'}, status=401)


# ── MICROBUSES ────────────────────────────────────────────────────────────────


@api_view(['POST'])
def registrar_microbus(request):
    s = MicrobusSerializer(data=request.data)
    if s.is_valid():
        s.save()
        return Response(s.data, status=201)
    return Response(s.errors, status=400)


# ── RECORRIDOS ────────────────────────────────────────────────────────────────


@api_view(['POST'])
def iniciar_recorrido(request):
    microbus_id   = request.data.get('microbus_id')
    linea_ruta_id = request.data.get('linea_ruta_id')
    if not microbus_id or not linea_ruta_id:
        return Response({'error': 'microbus_id y linea_ruta_id son requeridos'}, status=400)

    Recorrido.objects.filter(microbus_id=microbus_id, estado='activo').update(
        estado='finalizado', fecha_fin=timezone.now()
    )
    recorrido = Recorrido.objects.create(
        microbus_id=microbus_id, linea_ruta_id=linea_ruta_id
    )
    return Response({'recorrido_id': recorrido.id}, status=201)


@api_view(['POST'])
def enviar_posicion(request):
    s = PosicionGPSSerializer(data=request.data)
    if s.is_valid():
        s.save()
        return Response({'ok': True}, status=201)
    return Response(s.errors, status=400)


@api_view(['PATCH'])
def finalizar_recorrido(request, recorrido_id):
    try:
        rec = Recorrido.objects.get(id=recorrido_id)
    except Recorrido.DoesNotExist:
        return Response({'error': 'No encontrado'}, status=404)

    motivo       = request.data.get('motivo_salida')
    rec.estado   = 'fuerza_mayor' if motivo else 'finalizado'
    rec.motivo_salida = motivo
    rec.fecha_fin = timezone.now()
    rec.save()
    rec.posiciones.update(activo=False)
    return Response({'ok': True})
