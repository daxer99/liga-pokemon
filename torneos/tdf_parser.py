"""
Lectura de archivos .tdf exportados por TOM (Tournament Operations Manager).

El .tdf es un XML. Este módulo NO depende de Django: devuelve estructuras de
Python puras, así se puede probar y reutilizar por separado.

Estructura relevante del XML:

<tournament>
  <data> <n>NOMBRE</n> <id>26-08-023932</id> <city>..</city> <startdate>MM/DD/YYYY</startdate> </data>
  <players>
    <player userid="POP_ID"> <firstname/> <lastname/> <dropped><round>4</round></dropped>? </player>
  </players>
  <pods>
    <pod category="2">                      (0 Junior, 1 Senior, 2 Master)
      <rounds> <round number="1"> <matches>
        <match outcome="1"> <player1 userid=".."/> <player2 userid=".."/> <tablenumber/> </match>
        <match outcome="5"> <player userid=".."/> </match>     (partida de un solo jugador)
      </matches> </round> </rounds>
    </pod>
  </pods>
  <standings> <pod category="2" type="finished"> <player id=".." place="1"/> </pod> </standings>
</tournament>
"""
from dataclasses import dataclass, field
from datetime import date, datetime
import xml.etree.ElementTree as ET


class TDFError(ValueError):
    """El archivo no tiene el formato esperado."""


@dataclass
class JugadorTDF:
    pop_id: str
    nombre: str
    apellido: str
    drop_ronda: int | None = None
    division: int = 2
    puesto: int | None = None


@dataclass
class PartidaTDF:
    ronda: int
    mesa: int
    resultado: int
    jugador1: str
    jugador2: str | None = None


@dataclass
class TorneoTDF:
    tom_id: str
    nombre: str
    fecha: date
    ciudad: str
    jugadores: dict[str, JugadorTDF] = field(default_factory=dict)
    partidas: list[PartidaTDF] = field(default_factory=list)

    @property
    def cantidad_rondas(self) -> int:
        return max((p.ronda for p in self.partidas), default=0)


def _texto(elem, tag, defecto=""):
    valor = elem.findtext(tag)
    return valor.strip() if valor else defecto


def _nombre_propio(texto: str) -> str:
    """'DE LA FUENTE' -> 'De La Fuente' (TOM guarda todo en mayúsculas)."""
    return " ".join(p.capitalize() for p in texto.split())


def leer_tdf(contenido: bytes | str) -> TorneoTDF:
    try:
        raiz = ET.fromstring(contenido)
    except ET.ParseError as e:
        raise TDFError(f"El archivo no es un XML válido: {e}") from e

    if raiz.tag != "tournament" or raiz.find("data") is None:
        raise TDFError("El archivo no parece ser un .tdf de TOM (falta <tournament><data>).")

    data = raiz.find("data")
    tom_id = _texto(data, "id")
    if not tom_id:
        raise TDFError("El torneo no tiene ID de TOM.")
    try:
        fecha = datetime.strptime(_texto(data, "startdate"), "%m/%d/%Y").date()
    except ValueError as e:
        raise TDFError("No se pudo leer la fecha del torneo (<startdate>).") from e

    torneo = TorneoTDF(
        tom_id=tom_id,
        nombre=" ".join((_texto(data, "n") or _texto(data, "name")).split()),
        fecha=fecha,
        ciudad=_nombre_propio(_texto(data, "city")),
    )

    # Jugadores (no se lee la fecha de nacimiento a propósito: no la necesitamos)
    for p in raiz.findall("./players/player"):
        drop = p.find("dropped")
        drop_ronda = int(_texto(drop, "round", "0") or 0) if drop is not None else 0
        torneo.jugadores[p.get("userid")] = JugadorTDF(
            pop_id=p.get("userid"),
            nombre=_nombre_propio(_texto(p, "firstname")),
            apellido=_nombre_propio(_texto(p, "lastname")),
            drop_ronda=drop_ronda or None,
        )

    # Partidas de cada división
    for pod in raiz.findall("./pods/pod"):
        for ronda in pod.findall("./rounds/round"):
            numero = int(ronda.get("number"))
            for m in ronda.findall("./matches/match"):
                resultado = int(m.get("outcome"))
                mesa = int(_texto(m, "tablenumber", "0") or 0)
                solo = m.find("player")
                if solo is not None:
                    torneo.partidas.append(
                        PartidaTDF(numero, mesa, resultado, jugador1=solo.get("userid"))
                    )
                else:
                    torneo.partidas.append(
                        PartidaTDF(
                            numero,
                            mesa,
                            resultado,
                            jugador1=m.find("player1").get("userid"),
                            jugador2=m.find("player2").get("userid"),
                        )
                    )

    # Puestos finales y división de cada jugador
    for pod in raiz.findall("./standings/pod"):
        division = int(pod.get("category", 2))
        for p in pod.findall("player"):
            j = torneo.jugadores.get(p.get("id"))
            if j:
                j.division = division
                j.puesto = int(p.get("place"))

    return torneo
