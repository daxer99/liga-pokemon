from django.test import TestCase

from .models import Partida, Temporada
from .servicios import puntos_de_partida
from .tdf_parser import TDFError, leer_tdf

TDF_MINIMO = b"""<?xml version="1.0"?>
<tournament><data><n>PRUEBA</n><id>26-01-000001</id><city>PARANA</city><startdate>01/15/2026</startdate></data>
<players>
  <player userid="1"><firstname>ANA</firstname><lastname>PEREZ</lastname></player>
  <player userid="2"><firstname>LUIS</firstname><lastname>DE LA FUENTE</lastname></player>
</players>
<pods><pod category="2"><rounds><round number="1"><matches>
  <match outcome="1"><player1 userid="1"/><player2 userid="2"/><tablenumber>1</tablenumber></match>
</matches></round></rounds></pod></pods>
<standings><pod category="2" type="finished"><player id="1" place="1"/><player id="2" place="2"/></pod></standings>
</tournament>"""


class ParserTests(TestCase):
    def test_lee_torneo_minimo(self):
        t = leer_tdf(TDF_MINIMO)
        self.assertEqual(t.tom_id, "26-01-000001")
        self.assertEqual(t.jugadores["2"].apellido, "De La Fuente")
        self.assertEqual(t.jugadores["1"].puesto, 1)
        self.assertEqual(len(t.partidas), 1)

    def test_rechaza_archivo_invalido(self):
        with self.assertRaises(TDFError):
            leer_tdf(b"esto no es xml")


class PuntosTests(TestCase):
    def setUp(self):
        self.t = Temporada(puntos_participacion=1, puntos_victoria=3, puntos_empate=1)
        self.R = Partida.Resultado

    def test_victoria_empate_derrota(self):
        self.assertEqual(puntos_de_partida(self.t, self.R.GANA_J1, True), 4)
        self.assertEqual(puntos_de_partida(self.t, self.R.GANA_J1, False), 1)
        self.assertEqual(puntos_de_partida(self.t, self.R.EMPATE, False), 2)

    def test_bye_configurable(self):
        self.assertEqual(puntos_de_partida(self.t, self.R.BYE, True), 4)
        self.t.bye_suma_puntos = False
        self.assertEqual(puntos_de_partida(self.t, self.R.BYE, True), 0)


class FilaTablaTests(TestCase):
    def test_porcentajes(self):
        from .servicios import FilaTabla

        f = FilaTabla(jugador=None, victorias=3, empates=1, derrotas=0, puntos=14, fechas=1)
        self.assertEqual(f.pct_victorias, 75.0)
        self.assertEqual(f.rendimiento, 83.3)
        self.assertEqual(f.promedio_fecha, 14.0)
