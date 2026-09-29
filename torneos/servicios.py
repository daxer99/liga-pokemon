"""
Lógica de negocio: importar un .tdf a la base y calcular la tabla de una temporada.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass

from django.db import transaction

from .models import Jugador, Participacion, Partida, Temporada, Torneo
from .tdf_parser import leer_tdf


# Una división con menos jugadores que esto no cuenta para mejor puesto ni fechas ganadas
MINIMO_JUGADORES_DIVISION = 4


class TorneoYaImportado(Exception):
    def __init__(self, torneo):
        self.torneo = torneo
        super().__init__(f"El torneo {torneo.tom_id} ya estaba cargado.")


@transaction.atomic
def importar_tdf(contenido, *, temporada=None, tipo=Torneo.Tipo.FECHA_LIGA, reemplazar=False):
    """
    Carga (o recarga) un torneo desde el contenido de un .tdf.
    Todo ocurre en una transacción: si algo falla, no queda nada a medias.
    """
    datos = leer_tdf(contenido)

    existente = Torneo.objects.filter(tom_id=datos.tom_id).first()
    if existente and not reemplazar:
        raise TorneoYaImportado(existente)
    if existente:
        existente.delete()  # CASCADE borra participaciones y partidas

    torneo = Torneo.objects.create(
        tom_id=datos.tom_id,
        nombre=datos.nombre,
        fecha=datos.fecha,
        tipo=tipo,
        temporada=temporada,
        ciudad=datos.ciudad,
        cantidad_rondas=datos.cantidad_rondas,
    )

    # Jugadores: se crean si no existen; si existen se actualiza el nombre.
    jugadores = {}
    for j in datos.jugadores.values():
        jugador, _ = Jugador.objects.update_or_create(
            pop_id=j.pop_id, defaults={"nombre": j.nombre, "apellido": j.apellido}
        )
        jugadores[j.pop_id] = jugador
        Participacion.objects.create(
            torneo=torneo,
            jugador=jugador,
            division=j.division,
            puesto=j.puesto,
            drop_ronda=j.drop_ronda,
        )

    Partida.objects.bulk_create(
        Partida(
            torneo=torneo,
            ronda=p.ronda,
            mesa=p.mesa,
            resultado=p.resultado,
            jugador1=jugadores[p.jugador1],
            jugador2=jugadores[p.jugador2] if p.jugador2 else None,
        )
        for p in datos.partidas
    )
    return torneo


@dataclass
class FilaTabla:
    jugador: Jugador
    fechas: int = 0
    victorias: int = 0
    empates: int = 0
    derrotas: int = 0
    byes: int = 0
    puntos: int = 0
    posicion: int = 0
    mejor_puesto: int | None = None
    fechas_ganadas: int = 0
    racha_max: int = 0  # mayor cantidad de victorias seguidas (el bye cuenta como victoria)

    @property
    def jugadas(self):
        """Partidas jugadas, contando los byes como victorias (sin derrotas asignadas)."""
        return self.victorias + self.empates + self.derrotas

    @property
    def pct_victorias(self):
        """Porcentaje de partidas ganadas sobre las jugadas."""
        return round(100 * self.victorias / self.jugadas, 1) if self.jugadas else 0.0

    @property
    def rendimiento(self):
        """Puntos de partida obtenidos sobre los posibles (victoria 3, empate 1), en %."""
        if not self.jugadas:
            return 0.0
        return round(100 * (3 * self.victorias + self.empates) / (3 * self.jugadas), 1)

    @property
    def promedio_fecha(self):
        """Puntos de liga por fecha jugada."""
        return round(self.puntos / self.fechas, 1) if self.fechas else 0.0


@dataclass
class Destacado:
    titulo: str
    filas: list[FilaTabla]  # más de una si hay empate
    valor: str


def puntos_de_partida(temporada, resultado, es_jugador1):
    """Puntos que recibe un jugador por una partida, según el reglamento de la temporada."""
    R = Partida.Resultado
    part, vic, emp = (
        temporada.puntos_participacion,
        temporada.puntos_victoria,
        temporada.puntos_empate,
    )
    if resultado == R.BYE:
        return part + vic if temporada.bye_suma_puntos else 0
    if resultado == R.DERROTA_ASIGNADA:
        return 0
    if resultado == R.EMPATE:
        return part + emp
    gano = (resultado == R.GANA_J1) == es_jugador1
    return part + (vic if gano else 0)


def _letra(resultado, es_j1):
    R = Partida.Resultado
    if resultado == R.BYE:
        return "B"
    if resultado == R.EMPATE:
        return "E"
    if resultado == R.DERROTA_ASIGNADA:
        return "D"
    return "V" if (resultado == R.GANA_J1) == es_j1 else "D"


def tabla_temporada(temporada: Temporada) -> list[FilaTabla]:
    """Tabla acumulada de todas las fechas de liga de una temporada."""
    filas: dict[int, FilaTabla] = {}
    fechas_por_jugador = defaultdict(set)
    secuencias = defaultdict(list)  # resultados en orden cronológico, para la racha

    def fila(jugador):
        if jugador.id not in filas:
            filas[jugador.id] = FilaTabla(jugador)
        return filas[jugador.id]

    partidas = (
        Partida.objects.filter(torneo__temporada=temporada, torneo__tipo=Torneo.Tipo.FECHA_LIGA)
        .select_related("jugador1", "jugador2")
        .order_by("torneo__fecha", "ronda", "mesa")  # orden cronológico, para la racha
    )

    for p in partidas:
        lados = [(p.jugador1, True)] + ([(p.jugador2, False)] if p.jugador2 else [])
        for jugador, es_j1 in lados:
            f = fila(jugador)
            fechas_por_jugador[jugador.id].add(p.torneo_id)
            f.puntos += puntos_de_partida(temporada, p.resultado, es_j1)
            letra = _letra(p.resultado, es_j1)
            secuencias[jugador.id].append(letra)
            if letra == "B":
                f.byes += 1
                f.victorias += 1  # el bye cuenta como victoria en V-E-D
            elif letra == "E":
                f.empates += 1
            elif letra == "V":
                f.victorias += 1
            elif p.resultado != Partida.Resultado.DERROTA_ASIGNADA:
                f.derrotas += 1

    for jugador_id, torneos in fechas_por_jugador.items():
        f = filas[jugador_id]
        f.fechas = len(torneos)
        racha = 0
        for letra in secuencias[jugador_id]:
            if letra in ("V", "B"):
                racha += 1
                f.racha_max = max(f.racha_max, racha)
            else:
                racha = 0

    # Puestos finales en cada fecha. TOM ordena por división, así que un Junior solo
    # en su división sale 1º; esos puestos no cuentan para mejor puesto ni fechas ganadas.
    puestos = list(
        Participacion.objects.filter(
            torneo__temporada=temporada, torneo__tipo=Torneo.Tipo.FECHA_LIGA, puesto__isnull=False
        ).values_list("torneo_id", "division", "jugador_id", "puesto")
    )
    tamanio = Counter((torneo_id, division) for torneo_id, division, _, _ in puestos)
    for torneo_id, division, jugador_id, puesto in puestos:
        f = filas.get(jugador_id)
        if not f or tamanio[(torneo_id, division)] < MINIMO_JUGADORES_DIVISION:
            continue
        f.mejor_puesto = puesto if f.mejor_puesto is None else min(f.mejor_puesto, puesto)
        f.fechas_ganadas += puesto == 1

    tabla = sorted(
        filas.values(),
        key=lambda f: (-f.puntos, -f.victorias, f.jugador.apellido, f.jugador.nombre),
    )
    # Posiciones compartidas ante empate exacto de puntos y victorias
    for i, f in enumerate(tabla):
        previo = tabla[i - 1] if i else None
        if previo and (previo.puntos, previo.victorias) == (f.puntos, f.victorias):
            f.posicion = previo.posicion
        else:
            f.posicion = i + 1
    return tabla


def minimo_partidas(tabla: list[FilaTabla]) -> int:
    """Para los porcentajes se exige haber jugado al menos la mitad de las partidas del que más jugó."""
    maximo = max((f.jugadas for f in tabla), default=0)
    return max(1, -(-maximo // 2))


def destacados(tabla: list[FilaTabla]) -> list[Destacado]:
    """Líderes en distintas estadísticas de la temporada (con empates incluidos)."""
    if not tabla:
        return []
    minimo = minimo_partidas(tabla)
    regulares = [f for f in tabla if f.jugadas >= minimo] or tabla

    def lideres(filas, clave):
        mejor = max(clave(f) for f in filas)
        return mejor, [f for f in filas if clave(f) == mejor]

    candidatos = [
        ("Más fechas ganadas", tabla, lambda f: f.fechas_ganadas, "{} fecha{}"),
        ("Más victorias", tabla, lambda f: f.victorias, "{} partida{}"),
        ("Mejor % de victorias", regulares, lambda f: f.pct_victorias, "{:g} %"),
        ("Racha más larga", tabla, lambda f: f.racha_max, "{} victoria{} seguidas"),
    ]
    resultado = []
    for titulo, filas, clave, formato in candidatos:
        valor, ganadores = lideres(filas, clave)
        if not valor:
            continue
        plural = "" if valor == 1 else "s"
        texto = formato.format(valor, plural) if "{}" in formato[2:] else formato.format(valor)
        resultado.append(Destacado(titulo, ganadores, texto))
    return resultado
