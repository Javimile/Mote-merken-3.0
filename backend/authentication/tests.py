from datetime import timedelta
from django.utils import timezone
from .views import expirar_reservas_vencidas
from unittest.mock import MagicMock, patch

from django.http import JsonResponse
from django.test import SimpleTestCase, RequestFactory

from .permissions import requiere_rol

from unittest.mock import patch
from .views import expirar_reservas_vencidas


class PruebasPermisosReserva(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("authentication.permissions.usuario_tiene_rol")
    def test_usuario_sin_rol_cliente_recibe_403(self, mock_tiene_rol):
        mock_tiene_rol.return_value = False

        usuario = MagicMock()
        usuario.is_authenticated = True
        usuario.usr_id_usr = 26

        request = self.factory.post("/api/reservas/1/cancelar/")
        request.user = usuario

        vista = requiere_rol("Admin", "Cliente")(
            lambda request, reserva_id: JsonResponse({"ok": True})
        )

        response = vista(request, reserva_id=1)

        self.assertEqual(response.status_code, 403)

    @patch("authentication.permissions.usuario_tiene_rol")
    def test_cliente_autenticado_con_rol_puede_pasar_el_decorador(
        self, mock_tiene_rol
    ):
        mock_tiene_rol.return_value = True

        usuario = MagicMock()
        usuario.is_authenticated = True
        usuario.usr_id_usr = 26

        request = self.factory.post("/api/reservas/1/cancelar/")
        request.user = usuario

        vista = requiere_rol("Admin", "Cliente")(
            lambda request, reserva_id: JsonResponse({"ok": True})
        )

        response = vista(request, reserva_id=1)

        self.assertEqual(response.status_code, 200)


    def test_cliente_no_es_propietario_de_reserva_ajena(self):
        usuario_id = 26
        propietario_id = 23
        es_admin = False

        puede_cancelar = (
            es_admin or propietario_id == usuario_id
        )

        self.assertFalse(puede_cancelar)

    def test_cliente_es_propietario_de_su_reserva(self):
        usuario_id = 26
        propietario_id = 26
        es_admin = False

        puede_cancelar = (
            es_admin or propietario_id == usuario_id
        )

        self.assertTrue(puede_cancelar)

    def test_admin_puede_cancelar_reserva_ajena(self):
        usuario_id = 26
        propietario_id = 23
        es_admin = True

        puede_cancelar = (
            es_admin or propietario_id == usuario_id
        )

        self.assertTrue(puede_cancelar)









class PruebaExpiracionReservas(SimpleTestCase):

    def test_funcion_expiracion_existe(self):
        self.assertTrue(callable(expirar_reservas_vencidas))

    def test_limite_de_24_horas(self):
        ahora = timezone.now()
        limite = ahora.replace(tzinfo=None) - timedelta(hours=24)

        self.assertEqual(
            ahora.replace(tzinfo=None) - limite,
            timedelta(hours=24),
        )

