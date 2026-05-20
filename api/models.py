from django.db import models
from datetime import date


class Linea(models.Model):
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)
    color  = models.CharField(max_length=7, default='#1565C0')
    imagen_microbus = models.ImageField(
        upload_to='lineas/', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class LineaRuta(models.Model):
    SENTIDO = [('ida', 'Ida'), ('vuelta', 'Vuelta')]
    linea       = models.ForeignKey(
        Linea, on_delete=models.CASCADE, related_name='rutas')
    sentido     = models.CharField(max_length=10, choices=SENTIDO)
    descripcion = models.CharField(max_length=255)
    distancia   = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    tiempo      = models.DecimalField(
        max_digits=6, decimal_places=2, default=0)

    class Meta:
        unique_together = ('linea', 'sentido')

    def __str__(self):
        return f"{self.linea.nombre} - {self.sentido}"


class Punto(models.Model):
    linea_ruta  = models.ForeignKey(
        LineaRuta, on_delete=models.CASCADE, related_name='puntos')
    orden       = models.PositiveIntegerField()
    latitud     = models.DecimalField(max_digits=9, decimal_places=6)
    longitud    = models.DecimalField(max_digits=9, decimal_places=6)
    descripcion = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ['orden']
        unique_together = ('linea_ruta', 'orden')

    def __str__(self):
        return f"Punto {self.orden} de {self.linea_ruta}"


class Conductor(models.Model):
    SEXO = [('M', 'Masculino'), ('F', 'Femenino')]
    LICENCIA = [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]

    ci              = models.CharField(max_length=15, unique=True)
    nombre          = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    sexo            = models.CharField(max_length=1, choices=SEXO)
    telefono        = models.CharField(max_length=15)
    email           = models.EmailField(unique=True)
    password        = models.CharField(max_length=128)
    categoria_licencia = models.CharField(
        max_length=1, choices=LICENCIA, default='B')
    foto            = models.ImageField(
        upload_to='conductores/', null=True, blank=True)
    fecha_registro  = models.DateTimeField(auto_now_add=True)

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
    foto              = models.ImageField(
        upload_to='microbuses/', null=True, blank=True)

    def __str__(self):
        return self.placa


class Recorrido(models.Model):
    ESTADO = [
        ('activo', 'Activo'),
        ('finalizado', 'Finalizado'),
        ('fuerza_mayor', 'Fuerza Mayor'),
    ]

    microbus    = models.ForeignKey(
        Microbus, on_delete=models.CASCADE)
    linea_ruta  = models.ForeignKey(
        LineaRuta, on_delete=models.CASCADE)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin   = models.DateTimeField(null=True, blank=True)
    estado      = models.CharField(
        max_length=20, choices=ESTADO, default='activo')
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
