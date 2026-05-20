from rest_framework import serializers
from .models import (
    Linea, LineaRuta, Punto, Conductor, Microbus, Recorrido, PosicionGPS
)


class LineaSerializer(serializers.ModelSerializer):
    ruta_ida_id    = serializers.SerializerMethodField()
    ruta_vuelta_id = serializers.SerializerMethodField()

    class Meta:
        model = Linea
        fields = ['id', 'codigo', 'nombre', 'color',
                  'ruta_ida_id', 'ruta_vuelta_id']

    def get_ruta_ida_id(self, obj):
        ruta = obj.rutas.filter(sentido='ida').first()
        return ruta.id if ruta else None

    def get_ruta_vuelta_id(self, obj):
        ruta = obj.rutas.filter(sentido='vuelta').first()
        return ruta.id if ruta else None


class PuntoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Punto
        fields = ['id', 'orden', 'latitud', 'longitud', 'descripcion']


class LineaRutaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaRuta
        fields = '__all__'


class ConductorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conductor
        fields = [
            'id', 'ci', 'nombre', 'fecha_nacimiento', 'sexo',
            'telefono', 'email', 'password', 'categoria_licencia',
        ]
        extra_kwargs = {'password': {'write_only': True}}


class MicrobusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Microbus
        fields = [
            'id', 'placa', 'modelo', 'cantidad_asientos',
            'numero_interno', 'conductor', 'linea', 'fecha_asignacion',
        ]
        extra_kwargs = {
            'conductor': {'required': False, 'allow_null': True},
            'linea': {'required': False, 'allow_null': True},
            'fecha_asignacion': {'required': False},
            'numero_interno': {'required': False},
        }


class RecorridoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recorrido
        fields = '__all__'


class PosicionGPSSerializer(serializers.ModelSerializer):
    class Meta:
        model = PosicionGPS
        fields = [
            'id', 'recorrido', 'latitud', 'longitud',
            'velocidad', 'distancia', 'tiempo_seg', 'activo',
        ]
