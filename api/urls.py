from django.urls import path
from . import views

urlpatterns = [
    # Líneas y rutas
    path('lineas/', views.lista_lineas),
    path('lineas/cercanas/', views.lineas_cercanas),
    path('lineas-ruta/<int:linea_ruta_id>/puntos/', views.puntos_ruta),

    # Paradas (stops) — para mostrar en el mapa de búsqueda
    path('paradas/', views.lista_paradas),

    # Búsqueda de ruta óptima (Dijkstra)
    path('buscar-ruta/', views.buscar_ruta),

    # Microbuses activos
    path('posiciones/activos/', views.microbuses_activos),

    # Conductores
    path('conductores/', views.registrar_conductor),
    path('conductores/login/', views.login_conductor),

    # Microbuses
    path('microbuses/', views.registrar_microbus),

    # Recorridos y GPS
    path('recorridos/iniciar/', views.iniciar_recorrido),
    path('posiciones/', views.enviar_posicion),
    path('recorridos/<int:recorrido_id>/finalizar/', views.finalizar_recorrido),
]
