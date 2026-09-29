from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("torneos/", views.torneos_lista, name="torneos"),
    path("torneos/importar/", views.importar, name="importar"),
    path("torneos/<str:tom_id>/", views.torneo_detalle, name="torneo"),
    path("ligas/<int:pk>/", views.temporada_detalle, name="temporada"),
    path("jugadores/<str:pop_id>/", views.jugador_detalle, name="jugador"),
]
