from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
import math

from .models import (
    Linea, LineaRuta, Punto, Conductor, Microbus, Recorrido, PosicionGPS
)
from .serializers import (
    LineaSerializer, PuntoSerializer, ConductorSerializer,
    MicrobusSerializer, PosicionGPSSerializer,
)

# ── LÍNEAS ────────────────────────────────────────────────────────────────────


@api_view(['GET'])
def lista_lineas(request):
    return Response(
        LineaSerializer(Linea.objects.all(), many=True).data
    )


@api_view(['GET'])
def puntos_ruta(request, linea_ruta_id):
    puntos = Punto.objects.filter(
        linea_ruta_id=linea_ruta_id).order_by('orden')
    return Response(PuntoSerializer(puntos, many=True).data)


@api_view(['GET'])
def lineas_cercanas(request):
    """Líneas cuya ruta pasa dentro de `radio` metros de (lat, lng)."""
    try:
        lat   = float(request.GET.get('lat'))
        lng   = float(request.GET.get('lng'))
        radio = float(request.GET.get('radio', 300))
    except (TypeError, ValueError):
        return Response({'error': 'Parámetros inválidos'}, status=400)

    def distancia_metros(lat1, lng1, lat2, lng2):
        R = 6371000
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat1))
             * math.cos(math.radians(lat2))
             * math.sin(dlng / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    lineas_ids = set()
    for punto in Punto.objects.select_related('linea_ruta__linea').all():
        d = distancia_metros(
            lat, lng, float(punto.latitud), float(punto.longitud))
        if d <= radio:
            lineas_ids.add(punto.linea_ruta.linea_id)

    lineas = Linea.objects.filter(id__in=lineas_ids)
    return Response(LineaSerializer(lineas, many=True).data)


# ── MICROBUSES ACTIVOS ────────────────────────────────────────────────────────


@api_view(['GET'])
def microbuses_activos(request):
    """Última posición GPS de cada recorrido activo para una línea."""
    linea_id = request.GET.get('linea')
    recorridos = Recorrido.objects.filter(estado='activo')
    if linea_id:
        recorridos = recorridos.filter(linea_ruta__linea_id=linea_id)

    resultado = []
    for rec in recorridos:
        ultima = rec.posiciones.filter(activo=True).first()
        if ultima:
            resultado.append({
                'recorrido_id': rec.id,
                'placa': rec.microbus.placa,
                'latitud': float(ultima.latitud),
                'longitud': float(ultima.longitud),
                'velocidad': ultima.velocidad,
                'timestamp': ultima.timestamp,
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
        conductor = Conductor.objects.get(email=email, password=password)
        return Response({
            'conductor_id': conductor.id,
            'nombre': conductor.nombre,
            'ci': conductor.ci,
        })
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
    """Body: { microbus_id, linea_ruta_id }"""
    microbus_id   = request.data.get('microbus_id')
    linea_ruta_id = request.data.get('linea_ruta_id')

    if not microbus_id or not linea_ruta_id:
        return Response(
            {'error': 'microbus_id y linea_ruta_id son requeridos'},
            status=400)

    Recorrido.objects.filter(
        microbus_id=microbus_id, estado='activo'
    ).update(estado='finalizado', fecha_fin=timezone.now())

    recorrido = Recorrido.objects.create(
        microbus_id=microbus_id,
        linea_ruta_id=linea_ruta_id,
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

    motivo = request.data.get('motivo_salida')
    rec.estado = 'fuerza_mayor' if motivo else 'finalizado'
    rec.motivo_salida = motivo
    rec.fecha_fin = timezone.now()
    rec.save()

    rec.posiciones.update(activo=False)
    return Response({'ok': True})
