"""
Uso:
    python manage.py importar_tdf archivos/*.tdf --liga "Cuarta Liga Paraná"
"""
from django.core.management.base import BaseCommand, CommandError

from torneos.models import Temporada, Torneo
from torneos.servicios import TorneoYaImportado, importar_tdf
from torneos.tdf_parser import TDFError


class Command(BaseCommand):
    help = "Importa uno o más archivos .tdf de TOM."

    def add_arguments(self, parser):
        parser.add_argument("archivos", nargs="+")
        parser.add_argument("--liga", help="Nombre de la temporada (se crea si no existe).")
        parser.add_argument("--tipo", default=Torneo.Tipo.FECHA_LIGA, choices=Torneo.Tipo.values)
        parser.add_argument("--reemplazar", action="store_true")

    def handle(self, *args, **opts):
        temporada = None
        if opts["liga"]:
            temporada, creada = Temporada.objects.get_or_create(nombre=opts["liga"])
            if creada:
                self.stdout.write(f"Liga creada: {temporada}")

        for ruta in opts["archivos"]:
            try:
                with open(ruta, "rb") as f:
                    torneo = importar_tdf(
                        f.read(), temporada=temporada, tipo=opts["tipo"], reemplazar=opts["reemplazar"]
                    )
            except TorneoYaImportado as e:
                self.stdout.write(self.style.WARNING(f"Omitido (ya cargado): {e.torneo}"))
            except (TDFError, OSError) as e:
                raise CommandError(f"{ruta}: {e}")
            else:
                self.stdout.write(self.style.SUCCESS(f"Importado: {torneo}"))
