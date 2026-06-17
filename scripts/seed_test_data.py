"""
Datos de prueba: 3 conductores + 3 microbuses + 2 recorridos activos.
Ejecutar DESPUÉS de seed_from_excel.py.

    python manage.py shell < scripts/seed_test_data.py

Conductores de prueba:
    conductor1@test.com / pass1234  → L001
    conductor2@test.com / pass1234  → L002
    conductor3@test.com / pass1234  → L005
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Conductor, Microbus, Linea, LineaRuta, Recorrido, PosicionGPS  # noqa: E402

# Centro de SCZ para posiciones GPS iniciales
SCZ_LAT, SCZ_LNG = -17.7833, -63.1824

CONDUCTORES = [
    {
        'email': 'conductor1@test.com',
        'nombre': 'Carlos Mendoza Suárez',
        'ci': '11111111',
        'telefono': '70011111',
        'fecha_nacimiento': date(1988, 3, 15),
        'sexo': 'M',
        'linea_codigo': 'L001',
        'placa': 'SCZ001',
        'modelo': 'Toyota Hiace',
        'crear_recorrido': True,
    },
    {
        'email': 'conductor2@test.com',
        'nombre': 'Ana Patricia Vaca',
        'ci': '22222222',
        'telefono': '70022222',
        'fecha_nacimiento': date(1990, 7, 22),
        'sexo': 'F',
        'linea_codigo': 'L002',
        'placa': 'SCZ002',
        'modelo': 'Hyundai H100',
        'crear_recorrido': True,
    },
    {
        'email': 'conductor3@test.com',
        'nombre': 'Jorge Luis Pinto',
        'ci': '33333333',
        'telefono': '70033333',
        'fecha_nacimiento': date(1985, 11, 8),
        'sexo': 'M',
        'linea_codigo': 'L005',
        'placa': 'SCZ003',
        'modelo': 'Toyota Hiace',
        'crear_recorrido': False,
    },
]


def _crear_conductor(data):
    return Conductor.objects.create(
        ci=data['ci'],
        nombre=data['nombre'],
        fecha_nacimiento=data['fecha_nacimiento'],
        sexo=data['sexo'],
        telefono=data['telefono'],
        email=data['email'],
        password='pass1234',
        categoria_licencia='B',
    )


def _crear_microbus(data, conductor, linea, numero):
    return Microbus.objects.create(
        placa=data['placa'],
        modelo=data['modelo'],
        cantidad_asientos=20,
        numero_interno=str(numero).zfill(3),
        conductor=conductor,
        linea=linea,
        fecha_asignacion=date.today(),
    )


def _crear_recorrido_activo(microbus, linea, offset_idx):
    linea_ruta = LineaRuta.objects.filter(linea=linea, id_ruta=1).first()
    if not linea_ruta:
        return
    recorrido = Recorrido.objects.create(microbus=microbus, linea_ruta=linea_ruta)
    PosicionGPS.objects.create(
        recorrido=recorrido,
        latitud=SCZ_LAT + offset_idx * 0.005,
        longitud=SCZ_LNG + offset_idx * 0.005,
        velocidad=20.0,
        activo=True,
    )
    print(f"    Recorrido activo: {microbus.placa} en {linea.codigo}")


def seed_test():
    # Limpiar datos de prueba anteriores sin tocar el Excel seed
    Conductor.objects.filter(email__contains='@test.com').delete()

    for i, data in enumerate(CONDUCTORES):
        try:
            linea = Linea.objects.get(codigo=data['linea_codigo'])
        except Linea.DoesNotExist:
            print(f"  ADVERTENCIA: línea {data['linea_codigo']} no encontrada. ¿Corriste el seed del Excel?")
            continue

        conductor = _crear_conductor(data)
        microbus  = _crear_microbus(data, conductor, linea, i + 1)
        print(f"  {conductor.email} → {microbus.placa} ({linea.codigo})")

        if data['crear_recorrido']:
            _crear_recorrido_activo(microbus, linea, i)

    print("\nTest seed completado:")
    print(f"  {Conductor.objects.filter(email__contains='@test.com').count()} conductores")
    print(f"  {Microbus.objects.filter(placa__startswith='SCZ').count()} microbuses")
    print(f"  {Recorrido.objects.filter(estado='activo').count()} recorridos activos")
    print("\nCredenciales:")
    for d in CONDUCTORES:
        print(f"  {d['email']} / pass1234")


seed_test()
