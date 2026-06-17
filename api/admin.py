from django.contrib import admin
from .models import (
    Linea, LineaRuta, Punto, LineaPunto, PuntoTrasbordo,
    Conductor, Microbus, Recorrido, PosicionGPS,
)

admin.site.register(Linea)
admin.site.register(LineaRuta)
admin.site.register(Punto)
admin.site.register(LineaPunto)
admin.site.register(PuntoTrasbordo)
admin.site.register(Conductor)
admin.site.register(Microbus)
admin.site.register(Recorrido)
admin.site.register(PosicionGPS)
