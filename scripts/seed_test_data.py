"""
Seed completo — borra TODOS los datos y re-puebla desde cero.
  Paso 1: elimina PosicionGPS, Recorrido, Microbus, Conductor
  Paso 2: recarga datos geográficos del Excel (Linea, Punto, rutas, aristas, trasbordos)
  Paso 3: crea un conductor + microbus por cada línea que exista

Ejecutar desde bus_backend/:
    python manage.py shell < scripts/seed_test_data.py

Credenciales generadas (contraseña: pass1234):
    conductor1@gmail.com  →  1.ª línea (orden alfabético de código)
    conductor2@gmail.com  →  2.ª línea
    ...
    conductorN@gmail.com  →  N.ª línea
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import (                         # noqa: E402
    Conductor, Microbus, Linea, LineaRuta,
    Recorrido, PosicionGPS,
)
from scripts.seed_from_excel import seed_from_excel  # noqa: E402

# ── Posición inicial GPS (centro de SCZ) ──────────────────────────────────────
SCZ_LAT, SCZ_LNG = -17.7833, -63.1824

# ── Nombres bolivianos para los conductores (se repiten si hay más líneas) ────
_NOMBRES = [
    ('Carlos',    'Mendoza Suárez',    'M', date(1988,  3, 15)),
    ('Ana',       'Patricia Vaca',     'F', date(1990,  7, 22)),
    ('Jorge',     'Luis Pinto',        'M', date(1985, 11,  8)),
    ('María',     'Fernández Roca',    'F', date(1992,  5,  3)),
    ('Roberto',   'Quiroga Barba',     'M', date(1983,  9, 20)),
    ('Lucía',     'Torrico Arce',      'F', date(1995,  1, 14)),
    ('Diego',     'Quispe Mamani',     'M', date(1987,  6, 30)),
    ('Paola',     'Salvatierra Cruz',  'F', date(1993,  8, 17)),
    ('Marcos',    'Villena Suárez',    'M', date(1980,  4, 25)),
    ('Gabriela',  'Balderrama Oña',    'F', date(1991, 12,  5)),
]
_MODELOS = [
    'Toyota Hiace', 'Hyundai H100', 'Toyota Hiace', 'Nissan Urvan',
    'Toyota Hiace', 'Hyundai H100', 'Toyota Hiace', 'Nissan Urvan',
    'Toyota Hiace', 'Hyundai H100',
]

LINE = '─' * 55


def _limpiar_conductores():
    """Borra en orden inverso de FK para evitar errores de integridad."""
    PosicionGPS.objects.all().delete()
    Recorrido.objects.all().delete()
    Microbus.objects.all().delete()
    Conductor.objects.all().delete()
    print('  Eliminados: PosicionGPS, Recorrido, Microbus, Conductor')


def _crear_recorrido_activo(microbus, linea, offset):
    linea_ruta = LineaRuta.objects.filter(linea=linea, id_ruta=1).first()
    if not linea_ruta:
        return False
    recorrido = Recorrido.objects.create(microbus=microbus, linea_ruta=linea_ruta)
    PosicionGPS.objects.create(
        recorrido=recorrido,
        latitud=SCZ_LAT + offset * 0.005,
        longitud=SCZ_LNG + offset * 0.005,
        velocidad=20.0,
        activo=True,
    )
    return True


def seed_all():
    print(LINE)
    print('PASO 1 — Limpiando conductores y recorridos...')
    print(LINE)
    _limpiar_conductores()

    print()
    print(LINE)
    print('PASO 2 — Recargando datos geográficos del Excel...')
    print(LINE)
    seed_from_excel()   # ya borra y recarga Linea, Punto, LineaRuta, LineaPunto, PuntoTrasbordo

    print()
    print(LINE)
    print('PASO 3 — Creando un conductor por línea...')
    print(LINE)

    lineas = list(Linea.objects.all().order_by('codigo'))
    if not lineas:
        print('  ERROR: no hay líneas en la base de datos.')
        return

    credenciales = []
    for i, linea in enumerate(lineas):
        nombre_p, apellido, sexo, nacimiento = _NOMBRES[i % len(_NOMBRES)]
        modelo   = _MODELOS[i % len(_MODELOS)]
        email    = f'conductor{i + 1}@gmail.com'
        ci       = str(10000001 + i)
        placa    = f'SCZ{str(i + 1).zfill(3)}'
        telefono = f'700{str(i + 1).zfill(5)}'

        conductor = Conductor.objects.create(
            ci=ci,
            nombre=f'{nombre_p} {apellido}',
            fecha_nacimiento=nacimiento,
            sexo=sexo,
            telefono=telefono,
            email=email,
            password='pass1234',
            categoria_licencia='B',
        )
        microbus = Microbus.objects.create(
            placa=placa,
            modelo=modelo,
            cantidad_asientos=20,
            numero_interno=str(i + 1).zfill(3),
            conductor=conductor,
            linea=linea,
            fecha_asignacion=date.today(),
        )

        # Los primeros 3 conductores arrancan con un recorrido activo
        tiene_recorrido = False
        if i < 3:
            tiene_recorrido = _crear_recorrido_activo(microbus, linea, i)

        estado = '(recorrido activo)' if tiene_recorrido else ''
        print(f'  {email}  →  {placa}  [{linea.codigo}]  {estado}')
        credenciales.append((email, linea.codigo, linea.id))

    print()
    print(LINE)
    print('SEED COMPLETADO')
    print(LINE)
    print(f'  {Linea.objects.count()} líneas')
    print(f'  {Conductor.objects.count()} conductores (uno por línea)')
    print(f'  {Microbus.objects.count()} microbuses')
    print(f'  {Recorrido.objects.filter(estado="activo").count()} recorridos activos')
    print()
    print('Credenciales (contraseña: pass1234):')
    for email, codigo, linea_id in credenciales:
        print(f'  email={email}   linea_id={linea_id}  [{codigo}]')


seed_all()
