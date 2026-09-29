from django.contrib import admin

from .models import Jugador, Participacion, Partida, Temporada, Torneo


@admin.register(Temporada)
class TemporadaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activa", "puntos_participacion", "puntos_victoria", "puntos_empate", "bye_suma_puntos")
    list_editable = ("activa",)


@admin.register(Jugador)
class JugadorAdmin(admin.ModelAdmin):
    list_display = ("apellido", "nombre", "pop_id", "usuario")
    search_fields = ("nombre", "apellido", "pop_id")


class ParticipacionInline(admin.TabularInline):
    model = Participacion
    extra = 0
    autocomplete_fields = ("jugador",)


@admin.register(Torneo)
class TorneoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "fecha", "tipo", "temporada", "cantidad_rondas")
    list_filter = ("tipo", "temporada")
    search_fields = ("nombre", "tom_id")
    inlines = [ParticipacionInline]


@admin.register(Partida)
class PartidaAdmin(admin.ModelAdmin):
    list_display = ("torneo", "ronda", "mesa", "jugador1", "jugador2", "resultado")
    list_filter = ("torneo", "ronda", "resultado")
    autocomplete_fields = ("jugador1", "jugador2")
