
from django.core.management.base import BaseCommand

from authentication.views import expirar_reservas_vencidas


class Command(BaseCommand):
    help = "Expira reservas pendientes de gestión con más de 24 horas."

    def handle(self, *args, **options):
        cantidad = expirar_reservas_vencidas()

        self.stdout.write(
            self.style.SUCCESS(
                f"Proceso finalizado. Reservas expiradas: {cantidad}"
            )
        )
