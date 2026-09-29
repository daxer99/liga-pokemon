from collections import defaultdict

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ImportarTDFForm
from .models import Jugador, Participacion, Partida, Temporada, Torneo
from .servicios import (
    TorneoYaImportado,
    destacados,
    importar_tdf,
    minimo_partidas,
    tabla_temporada,
)
from .tdf_parser import TDFError


def _contexto_tabla(temporada):
    tabla = tabla_temporada(temporada) if temporada else []
    return {
        "temporada": temporada,
        "tabla": tabla,
        "destacados": destacados(tabla),
        "minimo_partidas": minimo_partidas(tabla) if tabla else 0,
    }


def inicio(request):
    temporada = Temporada.objects.filter(activa=True).first()
    contexto = _contexto_tabla(temporada)
    contexto["torneos"] = Torneo.objects.all()[:8]
    return render(request, "torneos/inicio.html", contexto)


def temporada_detalle(request, pk):
    temporada = get_object_or_404(Temporada, pk=pk)
    contexto = _contexto_tabla(temporada)
    contexto["torneos"] = temporada.torneos.all()
    return render(request, "torneos/temporada.html", contexto)


def torneos_lista(request):
    return render(
        request,
        "torneos/torneos.html",
        {"torneos": Torneo.objects.select_related("temporada"), "temporadas": Temporada.objects.all()},
    )


def torneo_detalle(request, tom_id):
    torneo = get_object_or_404(Torneo, tom_id=tom_id)
    participaciones = torneo.participaciones.select_related("jugador").order_by("division", "puesto")

    divisiones = defaultdict(list)
    for p in participaciones:
        divisiones[p.get_division_display()].append(p)

    rondas = defaultdict(list)
    for partida in torneo.partidas.select_related("jugador1", "jugador2"):
        rondas[partida.ronda].append(partida)

    return render(
        request,
        "torneos/torneo.html",
        {
            "torneo": torneo,
            "divisiones": dict(divisiones),
            "rondas": sorted(rondas.items()),
        },
    )


def jugador_detalle(request, pop_id):
    jugador = get_object_or_404(Jugador, pop_id=pop_id)
    participaciones = (
        Participacion.objects.filter(jugador=jugador)
        .select_related("torneo")
        .order_by("-torneo__fecha")
    )

    # Récord (V-D-E) del jugador en cada torneo
    R = Partida.Resultado
    record = defaultdict(lambda: {"v": 0, "d": 0, "e": 0})
    partidas = Partida.objects.filter(jugador1=jugador) | Partida.objects.filter(jugador2=jugador)
    for p in partidas:
        r = record[p.torneo_id]
        es_j1 = p.jugador1_id == jugador.id
        if p.resultado == R.EMPATE:
            r["e"] += 1
        elif p.resultado == R.BYE:
            r["v"] += 1
        elif p.resultado == R.DERROTA_ASIGNADA:
            r["d"] += 1
        elif (p.resultado == R.GANA_J1) == es_j1:
            r["v"] += 1
        else:
            r["d"] += 1

    filas = [(p, record[p.torneo_id]) for p in participaciones]
    return render(request, "torneos/jugador.html", {"jugador": jugador, "filas": filas})


@staff_member_required
def importar(request):
    if request.method == "POST":
        form = ImportarTDFForm(request.POST, request.FILES)
        if form.is_valid():
            datos = form.cleaned_data
            try:
                torneo = importar_tdf(
                    datos["archivo"].read(),
                    temporada=datos["temporada"],
                    tipo=datos["tipo"],
                    reemplazar=datos["reemplazar"],
                )
            except TDFError as e:
                form.add_error("archivo", str(e))
            except TorneoYaImportado as e:
                form.add_error(
                    "reemplazar",
                    f"«{e.torneo.nombre}» ya está cargado. Marcá esta opción para reemplazarlo.",
                )
            else:
                messages.success(
                    request,
                    f"Se importó «{torneo.nombre}»: {torneo.participaciones.count()} jugadores, "
                    f"{torneo.cantidad_rondas} rondas.",
                )
                return redirect("torneo", tom_id=torneo.tom_id)
    else:
        form = ImportarTDFForm()
    return render(request, "torneos/importar.html", {"form": form})
