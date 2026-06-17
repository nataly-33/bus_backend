"""
Carga los datos del Excel DatosLineas.xls (5 hojas) a la base de datos.

Cambios respecto a versión anterior:
  - Lineas.IdLinea ahora es entero (1-10); linea_map usa clave int
  - Colores ignorados del Excel (todos #FF0000); asignados por NombreLinea
  - LineasPuntos.Distancia/Tiempo calculados con haversine + 20 km/h
  - Nueva hoja PuntosTrasbordos: IdLineaOrigen/IdLineaDestino = IdLineaRuta (1-20)

Ejecutar desde bus_backend/:
    python manage.py shell < scripts/seed_from_excel.py
"""
import os
import sys
import math

# Agrega bus_backend/ al path para que 'config' sea importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Linea, LineaRuta, Punto, LineaPunto, PuntoTrasbordo  # noqa: E402

# ── Localizar el Excel ────────────────────────────────────────────────────────
_CWD = os.getcwd()
CANDIDATOS = [
    os.path.join(_CWD, '..', 'DatosLineas.xls'),
    os.path.join(_CWD, 'datos', 'DatosLineas.xls'),
]
EXCEL_PATH = next((p for p in CANDIDATOS if os.path.exists(p)), None)

if EXCEL_PATH is None:
    raise FileNotFoundError(
        "No se encontró DatosLineas.xls.\nBuscado en:\n"
        + "\n".join(f"  {os.path.abspath(p)}" for p in CANDIDATOS)
    )
print(f"Excel encontrado: {os.path.abspath(EXCEL_PATH)}")

# ── Colores únicos por línea (Excel tiene todos #FF0000) ──────────────────────
COLORES_LINEA = {
    'L001': '#E53935',  # rojo
    'L002': '#8E24AA',  # violeta
    'L005': '#1E88E5',  # azul
    'L008': '#43A047',  # verde
    'L009': '#FB8C00',  # naranja
    'L010': '#00ACC1',  # celeste
    'L011': '#F9A825',  # ámbar
    'L016': '#E91E63',  # rosa fuerte
    'L017': '#6D4C41',  # marrón
    'L018': '#546E7A',  # gris azulado
}


def _haversine_km(lat1, lng1, lat2, lng2):
    R = 6_371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def seed_from_excel(path=EXCEL_PATH):
    # ── Leer las 5 hojas ──────────────────────────────────────────────────────
    df_lineas  = pd.read_excel(path, sheet_name='Lineas',           engine='xlrd')
    df_puntos  = pd.read_excel(path, sheet_name='Puntos',           engine='xlrd')
    df_rutas   = pd.read_excel(path, sheet_name='LineaRuta',        engine='xlrd')
    df_lp      = pd.read_excel(path, sheet_name='LineasPuntos',     engine='xlrd')
    df_tr      = pd.read_excel(path, sheet_name='PuntosTrasbordos', engine='xlrd')

    print(f"Filas leídas → Lineas:{len(df_lineas)}  Puntos:{len(df_puntos)}"
          f"  LineaRuta:{len(df_rutas)}  LineasPuntos:{len(df_lp)}"
          f"  PuntosTrasbordos:{len(df_tr)}")

    # ── Limpiar en orden inverso de FKs ───────────────────────────────────────
    print("Limpiando datos anteriores...")
    PuntoTrasbordo.objects.all().delete()
    LineaPunto.objects.all().delete()
    LineaRuta.objects.all().delete()
    Punto.objects.all().delete()
    Linea.objects.all().delete()

    # ── 1. Puntos (498) ───────────────────────────────────────────────────────
    punto_map  = {}   # IdPunto(Excel int) → Punto.id(Django)
    coords_map = {}   # Punto.id(Django)   → (lat_float, lng_float)

    for _, row in df_puntos.iterrows():
        stop_val = str(row.get('Stop', 'N')).strip().upper()
        if stop_val not in ('S', 'N'):
            stop_val = 'N'
        desc = row.get('Descripcion')
        lat  = float(row['Latitud'])
        lng  = float(row['Longitud'])
        p = Punto.objects.create(
            latitud=lat, longitud=lng,
            descripcion=str(desc).strip() if pd.notna(desc) else None,
            stop=stop_val,
        )
        punto_map[int(row['IdPunto'])] = p.id
        coords_map[p.id] = (lat, lng)
    print(f"  Puntos insertados: {Punto.objects.count()}")

    # ── 2. Lineas (10) ────────────────────────────────────────────────────────
    # IdLinea es entero (1-10); NombreLinea tiene el código visible (con espacios)
    linea_map = {}   # IdLinea(Excel int) → Linea.id(Django)

    for _, row in df_lineas.iterrows():
        nombre = str(row['NombreLinea']).strip()
        color  = COLORES_LINEA.get(nombre, '#1565C0')
        l = Linea.objects.create(
            codigo=nombre,
            nombre_linea=nombre,
            color_linea=color,
        )
        linea_map[int(row['IdLinea'])] = l.id
    print(f"  Líneas insertadas: {Linea.objects.count()}")

    # ── 3. LineaRuta (20) ─────────────────────────────────────────────────────
    ruta_map = {}   # IdLineaRuta(Excel int) → LineaRuta.id(Django)

    for _, row in df_rutas.iterrows():
        id_linea = int(row['IdLinea'])
        linea_id = linea_map.get(id_linea)
        if linea_id is None:
            print(f"  ADVERTENCIA: IdLinea {id_linea} no encontrado — fila omitida")
            continue
        desc = row.get('Descripcion')
        r = LineaRuta.objects.create(
            linea_id=linea_id,
            id_ruta=int(row['IdRuta']),
            descripcion=str(desc).strip() if pd.notna(desc) else '',
            distancia=float(row['Distancia']) if pd.notna(row.get('Distancia')) else 0.0,
            tiempo=float(row['Tiempo'])    if pd.notna(row.get('Tiempo'))    else 0.0,
        )
        ruta_map[int(row['IdLineaRuta'])] = r.id
    print(f"  Rutas insertadas: {LineaRuta.objects.count()}")

    # ── 4. LineaPunto / aristas (1361) — calcular distancia y tiempo ──────────
    bulk    = []
    omitidas = 0

    for _, row in df_lp.iterrows():
        id_lr  = int(row['IdLineaRuta'])
        id_p   = int(row['IdPunto'])
        id_pd  = int(row['IdPuntoDest'])

        lr_id = ruta_map.get(id_lr)
        p_id  = punto_map.get(id_p)
        pd_id = punto_map.get(id_pd)

        if not all([lr_id, p_id, pd_id]):
            omitidas += 1
            continue

        lat1, lng1 = coords_map[p_id]
        lat2, lng2 = coords_map[pd_id]
        dist_km    = _haversine_km(lat1, lng1, lat2, lng2)
        tiempo_min = dist_km / 20.0 * 60.0   # velocidad 20 km/h → minutos

        bulk.append(LineaPunto(
            linea_ruta_id=lr_id,
            punto_id=p_id,
            punto_dest_id=pd_id,
            orden=int(row['Orden']),
            distancia=round(dist_km, 4),
            tiempo=round(tiempo_min, 4),
        ))

    LineaPunto.objects.bulk_create(bulk, batch_size=500)
    print(f"  Aristas insertadas: {LineaPunto.objects.count()}"
          + (f"  ({omitidas} omitidas por FK faltante)" if omitidas else ""))

    # ── 5. PuntosTrasbordos (534) ─────────────────────────────────────────────
    # IdLineaOrigen/IdLineaDestino son IdLineaRuta (1-20), NO IdLinea (1-10)
    bulk_tr  = []
    omit_tr  = 0

    for _, row in df_tr.iterrows():
        p_id = punto_map.get(int(row['IdPunto']))
        lr_o = ruta_map.get(int(row['IdLineaOrigen']))
        lr_d = ruta_map.get(int(row['IdLineaDestino']))

        if not all([p_id, lr_o, lr_d]):
            omit_tr += 1
            continue

        bulk_tr.append(PuntoTrasbordo(
            punto_id=p_id,
            linea_ruta_origen_id=lr_o,
            linea_ruta_destino_id=lr_d,
            penalizacion_min=float(row['PenalizacionMin']),
        ))

    PuntoTrasbordo.objects.bulk_create(bulk_tr, ignore_conflicts=True)
    print(f"  Trasbordos insertados: {PuntoTrasbordo.objects.count()}"
          + (f"  ({omit_tr} omitidos)" if omit_tr else ""))

    print("\nSeed completado:")
    print(f"  {Linea.objects.count()} líneas")
    print(f"  {Punto.objects.count()} puntos ({Punto.objects.filter(stop='S').count()} paradas)")
    print(f"  {LineaRuta.objects.count()} rutas (Salida + Retorno)")
    print(f"  {LineaPunto.objects.count()} aristas con distancia/tiempo calculados")
    print(f"  {PuntoTrasbordo.objects.count()} trasbordos posibles")


seed_from_excel()
