from django.db import models
from datetime import date


class Linea(models.Model):
    codigo          = models.CharField(max_length=10, unique=True)   # IdLinea del Excel
    nombre_linea    = models.CharField(max_length=100)               # NombreLinea
    color_linea     = models.CharField(max_length=7, default='#1565C0')  # ColorLinea hex
    imagen_microbus = models.ImageField(upload_to='lineas/', null=True, blank=True)
    fecha_creacion  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre_linea


class LineaRuta(models.Model):
    linea       = models.ForeignKey(
        Linea, on_delete=models.CASCADE, related_name='rutas')
    id_ruta     = models.IntegerField()
    descripcion = models.CharField(max_length=255, blank=True)
    distancia   = models.FloatField(default=0)
    tiempo      = models.FloatField(default=0)   # en horas

    class Meta:
        unique_together = ('linea', 'id_ruta')

    def __str__(self):
        sentido = 'Salida' if self.id_ruta == 1 else 'Retorno'
        return f"{self.linea.nombre_linea} - {sentido}"


class Punto(models.Model):
    """Punto geográfico independiente. Se reutiliza entre rutas vía LineaPunto."""
    STOP_CHOICES = [('S', 'Parada'), ('N', 'Normal')]

    latitud     = models.DecimalField(max_digits=9, decimal_places=6)
    longitud    = models.DecimalField(max_digits=9, decimal_places=6)
    descripcion = models.CharField(max_length=255, null=True, blank=True)
    stop        = models.CharField(max_length=1, choices=STOP_CHOICES, default='N')

    def __str__(self):
        return f"Punto {self.id} ({self.latitud}, {self.longitud})"


class LineaPunto(models.Model):
    """Arista del recorrido: segmento ordenado de punto origen a punto destino."""
    linea_ruta  = models.ForeignKey(
        LineaRuta, on_delete=models.CASCADE, related_name='linea_puntos')
    punto       = models.ForeignKey(
        Punto, on_delete=models.CASCADE, related_name='salidas')
    punto_dest  = models.ForeignKey(
        Punto, on_delete=models.CASCADE, related_name='llegadas')
    orden       = models.PositiveIntegerField()
    distancia   = models.FloatField(default=0)
    tiempo      = models.FloatField(default=0)  # minutos

    class Meta:
        ordering = ['orden']

    def __str__(self):
        return f"Arista {self.orden} de {self.linea_ruta}"


class PuntoTrasbordo(models.Model):
    """
    Trasbordo posible en una parada (Stop='S').
    IdLineaOrigen/IdLineaDestino del Excel son IdLineaRuta (1-20), NO IdLinea.
    """
    punto              = models.ForeignKey(
        Punto, on_delete=models.CASCADE, related_name='trasbordos')
    linea_ruta_origen  = models.ForeignKey(
        LineaRuta, on_delete=models.CASCADE, related_name='trasbordos_salida')
    linea_ruta_destino = models.ForeignKey(
        LineaRuta, on_delete=models.CASCADE, related_name='trasbordos_llegada')
    penalizacion_min   = models.FloatField(default=5.0)

    class Meta:
        unique_together = ('punto', 'linea_ruta_origen', 'linea_ruta_destino')

    def __str__(self):
        return f"Trasbordo en {self.punto_id}: {self.linea_ruta_origen_id}→{self.linea_ruta_destino_id}"


# ── Entidades operativas ───────────────────────────────────────────────────────

class Conductor(models.Model):
    SEXO_CHOICES    = [('M', 'Masculino'), ('F', 'Femenino')]
    LICENCIA_CHOICES = [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]

    ci                 = models.CharField(max_length=15, unique=True)
    nombre             = models.CharField(max_length=100)
    fecha_nacimiento   = models.DateField()
    sexo               = models.CharField(max_length=1, choices=SEXO_CHOICES)
    telefono           = models.CharField(max_length=15)
    email              = models.EmailField(unique=True)
    password           = models.CharField(max_length=128)
    categoria_licencia = models.CharField(max_length=1, choices=LICENCIA_CHOICES, default='B')
    foto               = models.ImageField(upload_to='conductores/', null=True, blank=True)
    fecha_registro     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class Microbus(models.Model):
    placa             = models.CharField(max_length=10, unique=True)
    modelo            = models.CharField(max_length=50)
    cantidad_asientos = models.PositiveIntegerField()
    numero_interno    = models.CharField(max_length=20, blank=True)
    conductor         = models.ForeignKey(
        Conductor, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='microbuses')
    linea             = models.ForeignKey(
        Linea, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_asignacion  = models.DateField(default=date.today)
    fecha_baja        = models.DateField(null=True, blank=True)
    foto              = models.ImageField(upload_to='microbuses/', null=True, blank=True)

    def __str__(self):
        return self.placa


class Recorrido(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('finalizado', 'Finalizado'),
        ('fuerza_mayor', 'Fuerza Mayor'),
    ]

    microbus     = models.ForeignKey(Microbus, on_delete=models.CASCADE)
    linea_ruta   = models.ForeignKey(LineaRuta, on_delete=models.CASCADE)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin    = models.DateTimeField(null=True, blank=True)
    estado       = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')
    motivo_salida = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Recorrido {self.id} - {self.microbus.placa}"


class PosicionGPS(models.Model):
    recorrido  = models.ForeignKey(
        Recorrido, on_delete=models.CASCADE, related_name='posiciones')
    latitud    = models.DecimalField(max_digits=9, decimal_places=6)
    longitud   = models.DecimalField(max_digits=9, decimal_places=6)
    velocidad  = models.FloatField(default=0)
    distancia  = models.FloatField(default=0)
    tiempo_seg = models.IntegerField(default=0)
    activo     = models.BooleanField(default=True)
    timestamp  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"GPS {self.recorrido_id} @ {self.timestamp}"
