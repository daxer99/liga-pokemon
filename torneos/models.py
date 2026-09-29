"""
Modelo de datos de la liga.

Temporada 1 ── N Torneo 1 ── N Participacion N ── 1 Jugador
                       └──── N Partida (jugador1, jugador2) ──> Jugador
"""
from django.conf import settings
from django.db import models


class Temporada(models.Model):
    """Una liga completa (ej. 'Cuarta Liga Paraná'), con su propio reglamento de puntos."""

    nombre = models.CharField(max_length=120, unique=True)
    activa = models.BooleanField(
        default=True, help_text="La temporada activa es la que se muestra en la portada."
    )

    # Reglamento de puntos (editable por temporada desde el admin)
    puntos_participacion = models.PositiveSmallIntegerField(default=1)
    puntos_victoria = models.PositiveSmallIntegerField(default=3)
    puntos_empate = models.PositiveSmallIntegerField(default=1)
    bye_suma_puntos = models.BooleanField(
        default=True,
        help_text="Si está marcado, un bye cuenta como partida jugada y ganada.",
    )

    class Meta:
        ordering = ["-activa", "-id"]

    def __str__(self):
        return self.nombre


class Jugador(models.Model):
    """Jugador identificado por su Player ID de Pokémon (POP ID)."""

    pop_id = models.CharField("POP ID", max_length=20, unique=True)
    nombre = models.CharField(max_length=80)
    apellido = models.CharField(max_length=80)
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="jugador",
        help_text="Cuenta del sitio vinculada a este jugador (se usa más adelante).",
    )

    class Meta:
        ordering = ["apellido", "nombre"]
        verbose_name_plural = "jugadores"

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


class Torneo(models.Model):
    class Tipo(models.TextChoices):
        FECHA_LIGA = "liga", "Fecha de liga"
        CUP = "cup", "League Cup"
        CHALLENGE = "challenge", "League Challenge"
        ESPECIAL = "especial", "Evento especial"

    tom_id = models.CharField("ID de TOM", max_length=30, unique=True)
    nombre = models.CharField(max_length=200)
    fecha = models.DateField()
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.FECHA_LIGA)
    temporada = models.ForeignKey(
        Temporada,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="torneos",
        help_text="Vacío si el torneo no suma a ninguna liga.",
    )
    ciudad = models.CharField(max_length=80, blank=True)
    cantidad_rondas = models.PositiveSmallIntegerField(default=0)
    importado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.nombre} ({self.fecha:%d/%m/%Y})"


class Participacion(models.Model):
    """Un jugador inscripto en un torneo, con su puesto final."""

    class Division(models.IntegerChoices):
        JUNIOR = 0, "Junior"
        SENIOR = 1, "Senior"
        MASTER = 2, "Master"

    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name="participaciones")
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name="participaciones")
    division = models.PositiveSmallIntegerField(choices=Division.choices, default=Division.MASTER)
    puesto = models.PositiveSmallIntegerField(null=True, blank=True)
    drop_ronda = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Ronda en la que abandonó, si abandonó."
    )

    class Meta:
        ordering = ["torneo", "division", "puesto"]
        verbose_name_plural = "participaciones"
        constraints = [
            models.UniqueConstraint(fields=["torneo", "jugador"], name="participacion_unica")
        ]

    def __str__(self):
        return f"{self.jugador} en {self.torneo}"


class Partida(models.Model):
    """
    Una partida de una ronda. Los códigos de resultado son los que usa TOM
    en el atributo `outcome` del .tdf.
    """

    class Resultado(models.IntegerChoices):
        GANA_J1 = 1, "Gana jugador 1"
        GANA_J2 = 2, "Gana jugador 2"
        EMPATE = 3, "Empate"
        BYE = 5, "Bye"
        DERROTA_ASIGNADA = 8, "Derrota asignada"

    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name="partidas")
    ronda = models.PositiveSmallIntegerField()
    mesa = models.PositiveSmallIntegerField(default=0)
    jugador1 = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name="partidas_j1")
    jugador2 = models.ForeignKey(
        Jugador, null=True, blank=True, on_delete=models.CASCADE, related_name="partidas_j2"
    )
    resultado = models.PositiveSmallIntegerField(choices=Resultado.choices)

    class Meta:
        ordering = ["torneo", "ronda", "mesa"]

    def __str__(self):
        rival = self.jugador2 or "—"
        return f"R{self.ronda} {self.jugador1} vs {rival}: {self.get_resultado_display()}"

    @property
    def es_individual(self):
        """Bye o derrota asignada: partidas de un solo jugador."""
        return self.jugador2_id is None
