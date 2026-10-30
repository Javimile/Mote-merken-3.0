import json
from datetime import timedelta
from django.db import connection , transaction
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .permissions import (
    obtener_roles_usuario,
    requiere_rol,
    usuario_tiene_rol,
)

def expirar_reservas_vencidas():
    """
    Expira reservas pendientes de gestión después de 24 horas.
    La fecha de creación se almacena en UTC sin zona horaria
    en la columna res_fec_res.
    """
    limite = timezone.now().replace(tzinfo=None) - timedelta(hours=24)

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE public.res
                SET res_est_res = 'expirada'
                WHERE res_est_res IN (
                    'pendiente',
                    'esperando_aprobacion'
                )
                  AND res_fec_res <= %s
                RETURNING res_id_res
                """,
                [limite],
            )
            reservas_expiradas = cursor.fetchall()

    return len(reservas_expiradas)

@require_GET
@ensure_csrf_cookie
def csrf_token(request):
    return JsonResponse({
        "csrfToken": get_token(request)
    })


@require_POST
def login_view(request):
    try:
        datos = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "El cuerpo de la solicitud no es JSON válido."},
            status=400,
        )

    if not isinstance(datos, dict):
        return JsonResponse(
            {"error": "El cuerpo debe ser un objeto JSON."},
            status=400,
        )

    correo = datos.get("correo", "")
    password = datos.get("password", "")

    if not isinstance(correo, str) or not isinstance(password, str):
        return JsonResponse(
            {"error": "Correo o contraseña inválidos."},
            status=400,
        )

    correo = correo.strip()

    if not correo or not password:
        return JsonResponse(
            {"error": "Debes ingresar correo y contraseña."},
            status=400,
        )

    usuario = authenticate(
        request,
        username=correo,
        password=password,
    )

    if usuario is None:
        return JsonResponse(
            {"error": "Correo o contraseña incorrectos."},
            status=401,
        )

    login(request, usuario)

    return JsonResponse({
        "mensaje": "Inicio de sesión correcto.",
        "usuario": {
            "id": usuario.usr_id_usr,
            "username": usuario.usr_nom_usr,
            "nombre": usuario.nombre_persona,
            "correo": usuario.correo,
        },
    })


@require_POST
def logout_view(request):
    logout(request)

    return JsonResponse({
        "mensaje": "Sesión cerrada correctamente."
    })


@require_GET
@requiere_rol("Admin")
def admin_test(request):
    return JsonResponse({
        "mensaje": "Tienes permisos de administrador.",
        "usuario": request.user.usr_nom_usr,
    })

@require_GET
def me_view(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "autenticado": False,
                "usuario": None,
            },
            status=401,
        )

    roles = obtener_roles_usuario(request.user)

    return JsonResponse({
        "autenticado": True,
        "usuario": {
            "id": request.user.usr_id_usr,
            "username": request.user.usr_nom_usr,
            "nombre": request.user.nombre_persona,
            "correo": request.user.correo,
            "roles": roles,
        },
    })

@require_POST
@requiere_rol("Admin")
def gestionar_rol(request):
    try:
        datos = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "El cuerpo de la solicitud no es JSON válido."},
            status=400,
        )

    if not isinstance(datos, dict):
        return JsonResponse(
            {"error": "El cuerpo debe ser un objeto JSON."},
            status=400,
        )

    accion = datos.get("accion")
    usuario_id = datos.get("usuario")
    rol_id = datos.get("rol")

    if accion not in ("asignar", "revocar"):
        return JsonResponse(
            {"error": "Acción inválida."},
            status=400,
        )

    try:
        usuario_id = int(usuario_id)
        rol_id = int(rol_id)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "Usuario o rol inválido."},
            status=400,
        )

    with connection.cursor() as cursor:

        # Verificar usuario
        cursor.execute(
            """
            SELECT usr_id_usr
            FROM public.usr
            WHERE usr_id_usr = %s
            """,
            [usuario_id],
        )

        if cursor.fetchone() is None:
            return JsonResponse(
                {"error": "El usuario no existe."},
                status=404,
            )

        # Verificar rol
        cursor.execute(
            """
            SELECT rol_id_rol, rol_nom_rol
            FROM public.rol
            WHERE rol_id_rol = %s
              AND rol_est_rol = TRUE
            """,
            [rol_id],
        )

        rol = cursor.fetchone()

        if rol is None:
            return JsonResponse(
                {"error": "El rol no existe o está inactivo."},
                status=404,
            )

        if accion == "asignar":
            cursor.execute(
                """
                SELECT 1
                FROM public.usr_rol
                WHERE uro_id_usr = %s
                  AND uro_id_rol = %s
                """,
                [usuario_id, rol_id],
            )

            if cursor.fetchone():
                return JsonResponse(
                    {
                        "error": "El usuario ya tiene este rol."
                    },
                    status=409,
                )

            cursor.execute(
                """
                INSERT INTO public.usr_rol (
                    uro_id_usr,
                    uro_id_rol
                )
                VALUES (%s, %s)
                """,
                [usuario_id, rol_id],
            )

            return JsonResponse({
                "mensaje": "Rol asignado correctamente.",
                "usuario": usuario_id,
                "rol": {
                    "id": rol[0],
                    "nombre": rol[1],
                },
            })

        # Revocar
        cursor.execute(
            """
            DELETE FROM public.usr_rol
            WHERE uro_id_usr = %s
              AND uro_id_rol = %s
            """,
            [usuario_id, rol_id],
        )

        if cursor.rowcount == 0:
            return JsonResponse(
                {"error": "El usuario no tiene ese rol."},
                status=404,
            )

        return JsonResponse({
            "mensaje": "Rol revocado correctamente.",
            "usuario": usuario_id,
            "rol": {
                "id": rol[0],
                "nombre": rol[1],
            },
        })



@require_GET
@requiere_rol("Admin")
def usuario_roles_view(request):
    usuario_id = request.GET.get("usuario")

    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "Usuario inválido."},
            status=400,
        )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                r.rol_id_rol,
                r.rol_nom_rol
            FROM public.usr_rol ur
            INNER JOIN public.rol r
                ON r.rol_id_rol = ur.uro_id_rol
            WHERE ur.uro_id_usr = %s
              AND r.rol_est_rol = TRUE
            ORDER BY r.rol_id_rol
            """,
            [usuario_id],
        )

        roles = [
            {
                "rol_id_rol": fila[0],
                "rol_nom_rol": fila[1],
            }
            for fila in cursor.fetchall()
        ]

    return JsonResponse(roles, safe=False)


@require_GET
@requiere_rol("Admin")
def buscar_usuarios_view(request):
    buscar = request.GET.get("buscar", "").strip()

    if len(buscar) < 2:
        return JsonResponse([], safe=False)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                u.usr_id_usr,
                u.usr_nom_usr,
                p.per_cor_per
            FROM public.usr u
            INNER JOIN public.per p
                ON p.per_id_per = u.usr_id_per
            WHERE
                LOWER(u.usr_nom_usr) LIKE LOWER(%s)
                OR LOWER(p.per_cor_per) LIKE LOWER(%s)
            ORDER BY u.usr_nom_usr
            LIMIT 10
            """,
            [
                f"%{buscar}%",
                f"%{buscar}%",
            ],
        )

        usuarios = [
            {
                "usr_id_usr": fila[0],
                "usr_nom_usr": fila[1],
                "per_cor_per": fila[2],
            }
            for fila in cursor.fetchall()
        ]

    return JsonResponse(usuarios, safe=False)

@require_GET
@requiere_rol("Admin")
def roles_view(request):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT rol_id_rol, rol_nom_rol
            FROM public.rol
            WHERE rol_est_rol = TRUE
            ORDER BY rol_id_rol
            """
        )

        roles = [
            {
                "rol_id_rol": fila[0],
                "rol_nom_rol": fila[1],
            }
            for fila in cursor.fetchall()
        ]

    return JsonResponse(roles, safe=False)

#itinerarios

@require_GET
def itinerario_por_tour_view(request, tour_id):
    try:
        tour_id = int(tour_id)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "Tour inválido."},
            status=400,
        )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                iti_id_iti,
                iti_id_tou,
                iti_tit_iti,
                iti_des_gen
            FROM public.iti
            WHERE iti_id_tou = %s
            """,
            [tour_id],
        )

        itinerario = cursor.fetchone()

    if itinerario is None:
        return JsonResponse(
            {"error": "El tour no tiene un itinerario."},
            status=404,
        )

    return JsonResponse({
        "iti_id_iti": itinerario[0],
        "iti_id_tou": itinerario[1],
        "iti_tit_iti": itinerario[2],
        "iti_des_gen": itinerario[3],
    })


@require_POST
def crear_itinerario_view(request):
    try:
        datos = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "El cuerpo de la solicitud no es JSON válido."},
            status=400,
        )

    if not isinstance(datos, dict):
        return JsonResponse(
            {"error": "El cuerpo debe ser un objeto JSON."},
            status=400,
        )

    tour_id = datos.get("iti_id_tou")
    titulo = datos.get("iti_tit_iti")
    descripcion = datos.get("iti_des_gen")

    try:
        tour_id = int(tour_id)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "Tour inválido."},
            status=400,
        )

    if titulo is not None and not isinstance(titulo, str):
        return JsonResponse(
            {"error": "El título debe ser texto."},
            status=400,
        )

    if descripcion is not None and not isinstance(descripcion, str):
        return JsonResponse(
            {"error": "La descripción debe ser texto."},
            status=400,
        )

    with connection.cursor() as cursor:

        # Verificar que el tour exista
        cursor.execute(
            """
            SELECT tou_id_tou
            FROM public.tou
            WHERE tou_id_tou = %s
            """,
            [tour_id],
        )

        if cursor.fetchone() is None:
            return JsonResponse(
                {"error": "El tour no existe."},
                status=404,
            )

        # Verificar que el tour no tenga ya un itinerario
        cursor.execute(
            """
            SELECT iti_id_iti
            FROM public.iti
            WHERE iti_id_tou = %s
            """,
            [tour_id],
        )

        if cursor.fetchone() is not None:
            return JsonResponse(
                {"error": "El tour ya tiene un itinerario."},
                status=409,
            )

        # Crear itinerario
        cursor.execute(
            """
            INSERT INTO public.iti (
                iti_id_tou,
                iti_tit_iti,
                iti_des_gen
            )
            VALUES (%s, %s, %s)
            RETURNING
                iti_id_iti,
                iti_id_tou,
                iti_tit_iti,
                iti_des_gen
            """,
            [
                tour_id,
                titulo,
                descripcion,
            ],
        )

        itinerario = cursor.fetchone()

    return JsonResponse(
        {
            "mensaje": "Itinerario creado correctamente.",
            "itinerario": {
                "iti_id_iti": itinerario[0],
                "iti_id_tou": itinerario[1],
                "iti_tit_iti": itinerario[2],
                "iti_des_gen": itinerario[3],
            },
        },
        status=201,
    )


@require_GET
def actividades_itinerario_view(request, itinerario_id):
    try:
        itinerario_id = int(itinerario_id)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "Itinerario inválido."},
            status=400,
        )

    with connection.cursor() as cursor:
        # Verificar que el itinerario exista
        cursor.execute(
            """
            SELECT iti_id_iti
            FROM public.iti
            WHERE iti_id_iti = %s
            """,
            [itinerario_id],
        )

        if cursor.fetchone() is None:
            return JsonResponse(
                {"error": "El itinerario no existe."},
                status=404,
            )

        # Obtener actividades ordenadas por día y orden
        cursor.execute(
            """
            SELECT
                itd_id_itd,
                itd_id_iti,
                itd_dia_num,
                itd_ord_itd,
                itd_tit_itd,
                itd_des_itd,
                itd_hor_ref
            FROM public.iti_det
            WHERE itd_id_iti = %s
            ORDER BY itd_dia_num, itd_ord_itd
            """,
            [itinerario_id],
        )

        actividades = [
            {
                "itd_id_itd": fila[0],
                "itd_id_iti": fila[1],
                "itd_dia_num": fila[2],
                "itd_ord_itd": fila[3],
                "itd_tit_itd": fila[4],
                "itd_des_itd": fila[5],
                "itd_hor_ref": fila[6].strftime("%H:%M:%S") if fila[6] else None,
            }
            for fila in cursor.fetchall()
        ]

    return JsonResponse(actividades, safe=False)


@require_POST
def crear_actividad_view(request, itinerario_id):
    try:
        itinerario_id = int(itinerario_id)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "Itinerario inválido."},
            status=400,
        )

    try:
        datos = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "El cuerpo de la solicitud no es JSON válido."},
            status=400,
        )

    if not isinstance(datos, dict):
        return JsonResponse(
            {"error": "El cuerpo debe ser un objeto JSON."},
            status=400,
        )

    dia_num = datos.get("itd_dia_num")
    orden = datos.get("itd_ord_itd")
    titulo = datos.get("itd_tit_itd")
    descripcion = datos.get("itd_des_itd")
    hora = datos.get("itd_hor_ref")

    # Validar día
    try:
        dia_num = int(dia_num)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "El número de día es inválido."},
            status=400,
        )

    if dia_num < 1:
        return JsonResponse(
            {"error": "El número de día debe ser mayor o igual a 1."},
            status=400,
        )

    # Validar orden
    try:
        orden = int(orden)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "El orden de la actividad es inválido."},
            status=400,
        )

    if orden < 1:
        return JsonResponse(
            {"error": "El orden debe ser mayor o igual a 1."},
            status=400,
        )

    # Validar título
    if not isinstance(titulo, str) or not titulo.strip():
        return JsonResponse(
            {"error": "El título de la actividad es obligatorio."},
            status=400,
        )

    titulo = titulo.strip()

    # Validar descripción
    if descripcion is not None and not isinstance(descripcion, str):
        return JsonResponse(
            {"error": "La descripción debe ser texto."},
            status=400,
        )

    # Validar hora
    if hora is not None and not isinstance(hora, str):
        return JsonResponse(
            {"error": "La hora debe tener formato HH:MM o HH:MM:SS."},
            status=400,
        )

    with connection.cursor() as cursor:

        # Verificar que el itinerario exista
        cursor.execute(
            """
            SELECT iti_id_iti
            FROM public.iti
            WHERE iti_id_iti = %s
            """,
            [itinerario_id],
        )

        if cursor.fetchone() is None:
            return JsonResponse(
                {"error": "El itinerario no existe."},
                status=404,
            )

        # Verificar que el orden no esté ocupado dentro del mismo día
        cursor.execute(
            """
            SELECT itd_id_itd
            FROM public.iti_det
            WHERE itd_id_iti = %s
              AND itd_dia_num = %s
              AND itd_ord_itd = %s
            """,
            [
                itinerario_id,
                dia_num,
                orden,
            ],
        )

        if cursor.fetchone() is not None:
            return JsonResponse(
                {
                    "error": (
                        "Ya existe una actividad con ese orden "
                        "para ese día del itinerario."
                    )
                },
                status=409,
            )

        # Insertar actividad
        cursor.execute(
            """
            INSERT INTO public.iti_det (
                itd_id_iti,
                itd_dia_num,
                itd_ord_itd,
                itd_tit_itd,
                itd_des_itd,
                itd_hor_ref
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING
                itd_id_itd,
                itd_id_iti,
                itd_dia_num,
                itd_ord_itd,
                itd_tit_itd,
                itd_des_itd,
                itd_hor_ref
            """,
            [
                itinerario_id,
                dia_num,
                orden,
                titulo,
                descripcion,
                hora,
            ],
        )

        actividad = cursor.fetchone()

    return JsonResponse(
        {
            "mensaje": "Actividad creada correctamente.",
            "actividad": {
                "itd_id_itd": actividad[0],
                "itd_id_iti": actividad[1],
                "itd_dia_num": actividad[2],
                "itd_ord_itd": actividad[3],
                "itd_tit_itd": actividad[4],
                "itd_des_itd": actividad[5],
                "itd_hor_ref": (
                    actividad[6].strftime("%H:%M:%S")
                    if actividad[6]
                    else None
                ),
            },
        },
        status=201,
    )
@require_http_methods(["PUT"])
def editar_actividad_view(request, itinerario_id, actividad_id):
    try:
        itinerario_id = int(itinerario_id)
        actividad_id = int(actividad_id)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "Itinerario o actividad inválidos."},
            status=400,
        )

    try:
        datos = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "El cuerpo de la solicitud no es JSON válido."},
            status=400,
        )

    if not isinstance(datos, dict):
        return JsonResponse(
            {"error": "El cuerpo debe ser un objeto JSON."},
            status=400,
        )

    dia_num = datos.get("itd_dia_num")
    orden = datos.get("itd_ord_itd")
    titulo = datos.get("itd_tit_itd")
    descripcion = datos.get("itd_des_itd")
    hora = datos.get("itd_hor_ref")

    try:
        dia_num = int(dia_num)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "El número de día es inválido."},
            status=400,
        )

    if dia_num < 1:
        return JsonResponse(
            {"error": "El número de día debe ser mayor o igual a 1."},
            status=400,
        )

    try:
        orden = int(orden)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "El orden de la actividad es inválido."},
            status=400,
        )

    if orden < 1:
        return JsonResponse(
            {"error": "El orden debe ser mayor o igual a 1."},
            status=400,
        )

    if not isinstance(titulo, str) or not titulo.strip():
        return JsonResponse(
            {"error": "El título de la actividad es obligatorio."},
            status=400,
        )

    titulo = titulo.strip()

    if descripcion is not None and not isinstance(descripcion, str):
        return JsonResponse(
            {"error": "La descripción debe ser texto."},
            status=400,
        )

    if hora is not None and not isinstance(hora, str):
        return JsonResponse(
            {"error": "La hora debe tener formato HH:MM o HH:MM:SS."},
            status=400,
        )

    with connection.cursor() as cursor:

        # Verificar que la actividad pertenezca al itinerario
        cursor.execute(
            """
            SELECT itd_id_itd
            FROM public.iti_det
            WHERE itd_id_itd = %s
              AND itd_id_iti = %s
            """,
            [actividad_id, itinerario_id],
        )

        if cursor.fetchone() is None:
            return JsonResponse(
                {"error": "La actividad no existe en este itinerario."},
                status=404,
            )

        # Evitar duplicar día + orden con otra actividad
        cursor.execute(
            """
            SELECT itd_id_itd
            FROM public.iti_det
            WHERE itd_id_iti = %s
              AND itd_dia_num = %s
              AND itd_ord_itd = %s
              AND itd_id_itd <> %s
            """,
            [
                itinerario_id,
                dia_num,
                orden,
                actividad_id,
            ],
        )

        if cursor.fetchone() is not None:
            return JsonResponse(
                {
                    "error": (
                        "Ya existe otra actividad con ese orden "
                        "para ese día del itinerario."
                    )
                },
                status=409,
            )

        # Actualizar actividad
        cursor.execute(
            """
            UPDATE public.iti_det
            SET
                itd_dia_num = %s,
                itd_ord_itd = %s,
                itd_tit_itd = %s,
                itd_des_itd = %s,
                itd_hor_ref = %s
            WHERE itd_id_itd = %s
              AND itd_id_iti = %s
            RETURNING
                itd_id_itd,
                itd_id_iti,
                itd_dia_num,
                itd_ord_itd,
                itd_tit_itd,
                itd_des_itd,
                itd_hor_ref
            """,
            [
                dia_num,
                orden,
                titulo,
                descripcion,
                hora,
                actividad_id,
                itinerario_id,
            ],
        )

        actividad = cursor.fetchone()

    return JsonResponse({
        "mensaje": "Actividad actualizada correctamente.",
        "actividad": {
            "itd_id_itd": actividad[0],
            "itd_id_iti": actividad[1],
            "itd_dia_num": actividad[2],
            "itd_ord_itd": actividad[3],
            "itd_tit_itd": actividad[4],
            "itd_des_itd": actividad[5],
            "itd_hor_ref": (
                actividad[6].strftime("%H:%M:%S")
                if actividad[6]
                else None
            ),
        },
        
    })
@require_http_methods(["DELETE"])
def eliminar_actividad_view(request, itinerario_id, actividad_id):
    try:
        itinerario_id = int(itinerario_id)
        actividad_id = int(actividad_id)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "Itinerario o actividad inválidos."},
            status=400,
        )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT itd_id_itd
            FROM public.iti_det
            WHERE itd_id_itd = %s
              AND itd_id_iti = %s
            """,
            [actividad_id, itinerario_id],
        )

        if cursor.fetchone() is None:
            return JsonResponse(
                {"error": "La actividad no existe en este itinerario."},
                status=404,
            )

        cursor.execute(
            """
            DELETE FROM public.iti_det
            WHERE itd_id_itd = %s
              AND itd_id_iti = %s
            """,
            [actividad_id, itinerario_id],
        )

    return JsonResponse({
        "mensaje": "Actividad eliminada correctamente."
    })

@require_GET
def tours_admin_view(request):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                tou_id_tou,
                tou_nom_tou,
                tou_des_tou,
                tou_dur_hor,
                tou_dur_dia,
                tou_cup_max,
                tou_est_tou,
                tou_fec_cre
            FROM public.tou
            ORDER BY tou_id_tou
            """
        )

        tours = [
            {
                "tou_id_tou": fila[0],
                "tou_nom_tou": fila[1],
                "tou_des_tou": fila[2],
                "tou_dur_hor": float(fila[3]) if fila[3] is not None else None,
                "tou_dur_dia": fila[4],
                "tou_cup_max": fila[5],
                "tou_est_tou": fila[6],
                "tou_fec_cre": fila[7].isoformat() if fila[7] else None,
            }
            for fila in cursor.fetchall()
        ]

    return JsonResponse(tours, safe=False)

    
@require_GET
def tours_publicos_view(request):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                tou_id_tou,
                tou_nom_tou,
                tou_des_tou,
                tou_dur_hor,
                tou_dur_dia,
                tou_cup_max
            FROM public.tou
            WHERE tou_est_tou = %s
            ORDER BY tou_id_tou
            """,
            ["activo"],
        )

        tours = [
            {
                "tou_id_tou": fila[0],
                "tou_nom_tou": fila[1],
                "tou_des_tou": fila[2],
                "tou_dur_hor": float(fila[3]) if fila[3] is not None else None,
                "tou_dur_dia": fila[4],
                "tou_cup_max": fila[5],
            }
            for fila in cursor.fetchall()
        ]

    return JsonResponse(tours, safe=False)


@require_GET
def tour_publico_detalle_view(request, tour_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                tou_id_tou,
                tou_nom_tou,
                tou_des_tou,
                tou_dur_hor,
                tou_dur_dia,
                tou_cup_max
            FROM public.tou
            WHERE tou_id_tou = %s
              AND tou_est_tou = %s
            """,
            [tour_id, "activo"],
        )

        fila = cursor.fetchone()

    if fila is None:
        return JsonResponse(
            {"error": "Tour no encontrado o no disponible."},
            status=404,
        )

    tour = {
        "tou_id_tou": fila[0],
        "tou_nom_tou": fila[1],
        "tou_des_tou": fila[2],
        "tou_dur_hor": float(fila[3]) if fila[3] is not None else None,
        "tou_dur_dia": fila[4],
        "tou_cup_max": fila[5],
    }

    return JsonResponse(tour)




def _leer_datos_tour(request):
    try:
        datos = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse(
            {"error": "El cuerpo de la solicitud no es JSON válido."},
            status=400,
        )

    if not isinstance(datos, dict):
        return None, JsonResponse(
            {"error": "El cuerpo debe ser un objeto JSON."},
            status=400,
        )

    nombre = datos.get("tou_nom_tou")
    descripcion = datos.get("tou_des_tou")
    duracion_horas = datos.get("tou_dur_hor")
    duracion_dias = datos.get("tou_dur_dia")
    capacidad = datos.get("tou_cup_max")
    estado = datos.get("tou_est_tou", "borrador")

    if not isinstance(nombre, str) or not nombre.strip():
        return None, JsonResponse(
            {"error": "El nombre del tour es obligatorio."},
            status=400,
        )

    nombre = nombre.strip()
    if len(nombre) > 255:
        return None, JsonResponse(
            {"error": "El nombre del tour no puede superar 255 caracteres."},
            status=400,
        )

    if descripcion is not None and not isinstance(descripcion, str):
        return None, JsonResponse(
            {"error": "La descripción debe ser texto."},
            status=400,
        )

    if descripcion is not None:
        descripcion = descripcion.strip() or None

    if estado not in ("borrador", "activo", "inactivo"):
        return None, JsonResponse(
            {"error": "Estado inválido. Usa borrador, activo o inactivo."},
            status=400,
        )

    def entero_opcional(valor, campo, minimo, maximo):
        if valor is None or valor == "":
            return None
        if isinstance(valor, bool):
            raise ValueError(f"{campo} debe ser un número entero.")
        numero = int(valor)
        if str(valor).strip() != str(numero):
            raise ValueError(f"{campo} debe ser un número entero.")
        if numero < minimo or numero > maximo:
            raise ValueError(f"{campo} está fuera del rango permitido.")
        return numero

    try:
        if duracion_horas in (None, ""):
            duracion_horas = None
        else:
            if isinstance(duracion_horas, bool):
                raise ValueError("La duración en horas debe ser numérica.")
            duracion_horas = float(duracion_horas)
            if not 0 < duracion_horas <= 999999:
                raise ValueError("La duración en horas debe ser mayor que cero.")

        duracion_dias = entero_opcional(
            duracion_dias, "La duración en días", 1, 32767
        )
        capacidad = entero_opcional(
            capacidad, "La capacidad máxima", 1, 2147483647
        )
    except (ValueError, TypeError, OverflowError) as exc:
        return None, JsonResponse({"error": str(exc)}, status=400)

    return {
        "tou_nom_tou": nombre,
        "tou_des_tou": descripcion,
        "tou_dur_hor": duracion_horas,
        "tou_dur_dia": duracion_dias,
        "tou_cup_max": capacidad,
        "tou_est_tou": estado,
    }, None


@require_POST
@requiere_rol("Admin")
def crear_tour_view(request):
    datos, error = _leer_datos_tour(request)
    if error:
        return error

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO public.tou (
                tou_nom_tou, tou_des_tou, tou_dur_hor,
                tou_dur_dia, tou_cup_max, tou_est_tou
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING tou_id_tou, tou_fec_cre
            """,
            [
                datos["tou_nom_tou"],
                datos["tou_des_tou"],
                datos["tou_dur_hor"],
                datos["tou_dur_dia"],
                datos["tou_cup_max"],
                datos["tou_est_tou"],
            ],
        )
        tour_id, fecha = cursor.fetchone()

    return JsonResponse(
        {
            **datos,
            "tou_id_tou": tour_id,
            "tou_fec_cre": fecha.isoformat() if fecha else None,
            "mensaje": "Tour creado correctamente.",
        },
        status=201,
    )


@require_http_methods(["PUT"])
@requiere_rol("Admin")
def editar_tour_view(request, tour_id):
    datos, error = _leer_datos_tour(request)
    if error:
        return error

    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE public.tou
            SET tou_nom_tou = %s,
                tou_des_tou = %s,
                tou_dur_hor = %s,
                tou_dur_dia = %s,
                tou_cup_max = %s,
                tou_est_tou = %s
            WHERE tou_id_tou = %s
            RETURNING tou_id_tou, tou_fec_cre
            """,
            [
                datos["tou_nom_tou"],
                datos["tou_des_tou"],
                datos["tou_dur_hor"],
                datos["tou_dur_dia"],
                datos["tou_cup_max"],
                datos["tou_est_tou"],
                tour_id,
            ],
        )
        fila = cursor.fetchone()

    if fila is None:
        return JsonResponse({"error": "El tour no existe."}, status=404)

    return JsonResponse(
        {
            **datos,
            "tou_id_tou": fila[0],
            "tou_fec_cre": fila[1].isoformat() if fila[1] else None,
            "mensaje": "Tour actualizado correctamente.",
        }
    )


@require_http_methods(["DELETE"])
@requiere_rol("Admin")
def eliminar_tour_view(request, tour_id):
    with connection.cursor() as cursor:
        # Impide borrar si cualquier tabla tiene una FK hacia public.tou
        # con registros asociados. No elimina información en cascada.
        cursor.execute(
            """
            SELECT
                ns.nspname AS esquema,
                rel.relname AS tabla,
                att.attname AS columna
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace ns ON ns.oid = rel.relnamespace
            JOIN unnest(con.conkey) WITH ORDINALITY AS keys(attnum, ord)
                ON TRUE
            JOIN pg_attribute att
              ON att.attrelid = rel.oid
             AND att.attnum = keys.attnum
            WHERE con.contype = 'f'
              AND con.confrelid = 'public.tou'::regclass
              AND ns.nspname = 'public'
            """
        )
        referencias = cursor.fetchall()

        cursor.execute(
            "SELECT tou_id_tou FROM public.tou WHERE tou_id_tou = %s",
            [tour_id],
        )
        if cursor.fetchone() is None:
            return JsonResponse({"error": "El tour no existe."}, status=404)

        for esquema, tabla, columna in referencias:
            # Los nombres provienen del catálogo de PostgreSQL, no del usuario.
            cursor.execute(
                f'SELECT 1 FROM "{esquema}"."{tabla}" '
                f'WHERE "{columna}" = %s LIMIT 1',
                [tour_id],
            )
            if cursor.fetchone():
                return JsonResponse(
                    {
                        "error": (
                            "No se puede eliminar este tour porque tiene "
                            f"registros asociados en {tabla}. "
                            "Resuelve esas dependencias antes de eliminarlo."
                        ),
                        "tabla_relacionada": tabla,
                    },
                    status=409,
                )

        cursor.execute(
            "DELETE FROM public.tou WHERE tou_id_tou = %s",
            [tour_id],
        )

    return JsonResponse({"mensaje": "Tour eliminado correctamente."})

def _leer_datos_reserva(request, usuario_id=None):   
    
    from datetime import date, time

    try:
        datos = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse(
            {"error": "El cuerpo de la solicitud no es JSON válido."},
            status=400,
        )

    if not isinstance(datos, dict):
        return None, JsonResponse(
            {"error": "El cuerpo debe ser un objeto JSON."},
            status=400,
        )

    try:
        if usuario_id is None:
            usuario_id = int(datos.get("res_id_usr"))
        else:
            usuario_id = int(usuario_id)

        tour_id = int(datos.get("res_id_tou"))
        cantidad_pasajeros = int(datos.get("res_can_pas", 1))
    except (TypeError, ValueError, OverflowError):


        return None, JsonResponse(
            {"error": "Usuario, tour y cantidad de pasajeros deben ser válidos."},
            status=400,
        )

    if usuario_id <= 0 or tour_id <= 0:
        return None, JsonResponse(
            {"error": "El usuario y el tour deben ser válidos."},
            status=400,
        )

    if cantidad_pasajeros < 1:
        return None, JsonResponse(
            {"error": "La cantidad de pasajeros debe ser al menos 1."},
            status=400,
        )

    fecha = datos.get("res_fec_act")
    hora = datos.get("res_hor_act")
    comentario = datos.get("res_com_res", "")

    if not isinstance(fecha, str) or not fecha.strip():
        return None, JsonResponse(
            {"error": "La fecha de realización es obligatoria."},
            status=400,
        )

    try:
        fecha = date.fromisoformat(fecha.strip())
    except ValueError:
        return None, JsonResponse(
            {"error": "La fecha debe tener formato AAAA-MM-DD."},
            status=400,
        )

    if not isinstance(hora, str) or not hora.strip():
        return None, JsonResponse(
            {"error": "El horario es obligatorio."},
            status=400,
        )

    try:
        hora = time.fromisoformat(hora.strip())
    except ValueError:
        return None, JsonResponse(
            {"error": "El horario debe tener formato HH:MM."},
            status=400,
        )

    if not isinstance(comentario, str):
        return None, JsonResponse(
            {"error": "El comentario debe ser texto."},
            status=400,
        )

    estado = "pendiente"

    return {
        "res_id_usr": usuario_id,
        "res_id_tou": tour_id,
        "res_fec_act": fecha,
        "res_hor_act": hora,
        "res_com_res": comentario.strip() or None,
        "res_est_res": estado,
        "res_can_pas": cantidad_pasajeros,
    }, None


@require_GET
@requiere_rol("Admin")
def reservas_admin_view(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                r.res_id_res,
                r.res_id_usr,
                u.usr_nom_usr,
                p.per_cor_per,
                r.res_id_tou,
                t.tou_nom_tou,
                r.res_fec_res,
                r.res_fec_act,
                r.res_hor_act,
                r.res_com_res,
                r.res_est_res,
                r.res_can_pas AS cantidad_participantes
            FROM public.res r
            JOIN public.usr u ON u.usr_id_usr = r.res_id_usr
            JOIN public.per p ON p.per_id_per = u.usr_id_per
            JOIN public.tou t ON t.tou_id_tou = r.res_id_tou
            ORDER BY r.res_id_res DESC
        """)
        filas = cursor.fetchall()

    reservas = [{
        "res_id_res": f[0],
        "res_id_usr": f[1],
        "usr_nom_usr": f[2],
        "per_cor_per": f[3],
        "res_id_tou": f[4],
        "tou_nom_tou": f[5],
        "res_fec_res": f[6].isoformat() if f[6] else None,
        "res_fec_act": f[7].isoformat() if f[7] else None,
        "res_hor_act": f[8].isoformat() if f[8] else None,
        "res_com_res": f[9],
        "res_est_res": f[10],
        "cantidad_participantes": f[11],
    } for f in filas]

    return JsonResponse(reservas, safe=False)


@require_POST
@requiere_rol("Admin")
def crear_reserva_view(request):
    datos, error = _leer_datos_reserva(request)
    if error:
        return error

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT usr_id_usr FROM public.usr "
            "WHERE usr_id_usr = %s AND usr_est_usr = TRUE",
            [datos["res_id_usr"]],
        )
        if cursor.fetchone() is None:
            return JsonResponse(
                {"error": "El usuario no existe o está inactivo."},
                status=400,
            )

        cursor.execute(
            "SELECT tou_cup_max FROM public.tou "
            "WHERE tou_id_tou = %s AND tou_est_tou = 'activo'",
            [datos["res_id_tou"]],
        )
        tour = cursor.fetchone()
        if tour is None:
            return JsonResponse(
                {"error": "El tour no existe o no está activo."},
                status=400,
            )

        

     
        cupo_maximo = tour[0]

        if datos["res_can_pas"] > cupo_maximo:
            return JsonResponse(
                {
                    "error": (
                        f"La cantidad de pasajeros no puede superar "
                        f"el cupo máximo de {cupo_maximo} personas."
                    )
                },
                status=400,
            )


        cursor.execute("""
            INSERT INTO public.res (
                res_id_usr,
                res_id_tou,
                res_com_res,
                res_fec_act,
                res_hor_act,
                res_est_res,
                res_can_pas
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING res_id_res, res_fec_res
        """, [
            datos["res_id_usr"],
            datos["res_id_tou"],
            datos["res_com_res"],
            datos["res_fec_act"],
            datos["res_hor_act"],
            datos["res_est_res"],
            datos["res_can_pas"],
        ])

        reserva_id, fecha_creacion = cursor.fetchone()

    return JsonResponse({
        "mensaje": "Reserva creada correctamente.",
        "res_id_res": reserva_id,
        "res_fec_res": fecha_creacion.isoformat(),
        **{
            k: v.isoformat() if hasattr(v, "isoformat") else v
            for k, v in datos.items()
        },
    }, status=201)

    
@require_POST
@requiere_rol("Cliente")
def solicitar_reserva_cliente_view(request):
    # La identidad se obtiene de la sesión de Django,
    # nunca del ID de usuario enviado por el navegador.
    usuario_id = request.user.usr_id_usr

    datos, error = _leer_datos_reserva(
    request,
    usuario_id=usuario_id,
)
    if error:
        return error

    # Sobrescribir cualquier ID de usuario enviado por el cliente.
    datos["res_id_usr"] = usuario_id

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT usr_id_usr
            FROM public.usr
            WHERE usr_id_usr = %s
              AND usr_est_usr = TRUE
            """,
            [usuario_id],
        )
        if cursor.fetchone() is None:
            return JsonResponse(
                {"error": "El usuario no existe o está inactivo."},
                status=403,
            )

        cursor.execute(
            """
            SELECT tou_cup_max
            FROM public.tou
            WHERE tou_id_tou = %s
              AND tou_est_tou = 'activo'
            """,
            [datos["res_id_tou"]],
        )
        tour = cursor.fetchone()

        if tour is None:
            return JsonResponse(
                {"error": "El tour no existe o no está activo."},
                status=400,
            )

        if datos["res_can_pas"] > tour[0]:
            return JsonResponse(
                {
                    "error": (
                        "La cantidad de pasajeros no puede superar "
                        f"el cupo máximo de {tour[0]} personas."
                    )
                },
                status=400,
            )

        cursor.execute(
            """
            INSERT INTO public.res (
                res_id_usr,
                res_id_tou,
                res_com_res,
                res_fec_act,
                res_hor_act,
                res_est_res,
                res_can_pas
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING res_id_res, res_fec_res
            """,
            [
                datos["res_id_usr"],
                datos["res_id_tou"],
                datos["res_com_res"],
                datos["res_fec_act"],
                datos["res_hor_act"],
                datos["res_est_res"],
                datos["res_can_pas"],
            ],
        )

        reserva_id, fecha_creacion = cursor.fetchone()

    return JsonResponse(
        {
            "mensaje": "Solicitud de reserva creada correctamente.",
            "res_id_res": reserva_id,
            "res_fec_res": fecha_creacion.isoformat(),
            "res_est_res": "pendiente",
            "res_id_tou": datos["res_id_tou"],
            "res_fec_act": datos["res_fec_act"].isoformat(),
            "res_hor_act": datos["res_hor_act"].isoformat(),
            "res_can_pas": datos["res_can_pas"],
        },
        status=201,
    )


@require_POST
@requiere_rol("Admin")
def editar_reserva_view(request, reserva_id):
    datos, error = _leer_datos_reserva(request)
    if error:
        return error

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT res_id_res, res_est_res
            FROM public.res
            WHERE res_id_res = %s
            """,
            [reserva_id],
        )
        reserva = cursor.fetchone()

        if reserva is None:
            return JsonResponse(
                {"error": "La reserva no existe."},
                status=404,
            )

        if reserva[1] in ("cancelada", "rechazada", "expirada", "completada"):
            return JsonResponse(
                {"error": "No se puede editar una reserva en estado terminal."},
                status=400,
            )

        cursor.execute(
            """
            SELECT usr_id_usr
            FROM public.usr
            WHERE usr_id_usr = %s AND usr_est_usr = TRUE
            """,
            [datos["res_id_usr"]],
        )
        if cursor.fetchone() is None:
            return JsonResponse(
                {"error": "El usuario no existe o está inactivo."},
                status=400,
            )

        cursor.execute(
            """
            SELECT tou_cup_max
            FROM public.tou
            WHERE tou_id_tou = %s AND tou_est_tou = 'activo'
            """,
            [datos["res_id_tou"]],
        )
        tour = cursor.fetchone()

        if tour is None:
            return JsonResponse(
                {"error": "El tour no existe o no está activo."},
                status=400,
            )

        if datos["res_can_pas"] > tour[0]:
            return JsonResponse(
                {
                    "error": (
                        f"La cantidad de pasajeros no puede superar "
                        f"el cupo máximo de {tour[0]} personas."
                    )
                },
                status=400,
            )

        cursor.execute(
            """
            UPDATE public.res
            SET res_id_usr = %s,
                res_id_tou = %s,
                res_com_res = %s,
                res_fec_act = %s,
                res_hor_act = %s,
                res_can_pas = %s
            WHERE res_id_res = %s
            """,
            [
                datos["res_id_usr"],
                datos["res_id_tou"],
                datos["res_com_res"],
                datos["res_fec_act"],
                datos["res_hor_act"],
                datos["res_can_pas"],
                reserva_id,
            ],
        )

    return JsonResponse({
        "mensaje": "Reserva actualizada correctamente.",
        "res_id_res": reserva_id,
    })
 

@require_POST
@requiere_rol("Admin", "Cliente")
@transaction.atomic
def cancelar_reserva_view(request, reserva_id):
    # Identificar al usuario y sus permisos
    es_admin = usuario_tiene_rol(request.user, "Admin")
    usuario_id = request.user.usr_id_usr

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT res_est_res, res_id_usr
            FROM public.res
            WHERE res_id_res = %s
            FOR UPDATE
            """,
            [reserva_id],
        )
        reserva = cursor.fetchone()

        if reserva is None:
            return JsonResponse(
                {"error": "La reserva no existe."},
                status=404,
            )

        estado_actual, propietario_id = reserva

        # Un Cliente solo puede cancelar su propia reserva
        if not es_admin and propietario_id != usuario_id:
            return JsonResponse(
                {
                    "error": (
                        "Solo puedes cancelar tus propias reservas."
                    )
                },
                status=403,
            )

        if estado_actual == "cancelada":
            return JsonResponse(
                {"mensaje": "La reserva ya está cancelada."},
                status=200,
            )

        if estado_actual in (
            "rechazada",
            "expirada",
            "completada",
        ):
            return JsonResponse(
                {
                    "error": (
                        "No se puede cancelar una reserva "
                        "en estado terminal."
                    )
                },
                status=400,
            )

        cursor.execute(
            """
            UPDATE public.res
            SET res_est_res = 'cancelada'
            WHERE res_id_res = %s
            """,
            [reserva_id],
        )

    return JsonResponse({
        "mensaje": "Reserva cancelada correctamente.",
        "res_id_res": reserva_id,
        "estado_anterior": estado_actual,
        "res_est_res": "cancelada",
    })




@require_POST
@requiere_rol("Admin")
def cambiar_estado_reserva_view(request, reserva_id):
    """
    Cambia el estado de una reserva.
    Por ahora, solamente un usuario con rol Admin puede hacerlo.
    PostgreSQL también valida la transición mediante el trigger.
    """
    try:
        datos = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "El cuerpo de la solicitud no es JSON válido."},
            status=400,
        )

    if not isinstance(datos, dict):
        return JsonResponse(
            {"error": "El cuerpo debe ser un objeto JSON."},
            status=400,
        )

    nuevo_estado = datos.get("estado")

    estados_validos = {
        "pendiente",
        "esperando_aprobacion",
        "aprobada",
        "rechazada",
        "cancelada",
        "expirada",
        "completada",
    }

    if nuevo_estado not in estados_validos:
        return JsonResponse(
            {"error": "El estado solicitado no es válido."},
            status=400,
        )

    transiciones_permitidas = {
        "pendiente": {
            "esperando_aprobacion",
            "cancelada",
            "expirada",
        },
        "esperando_aprobacion": {
            "aprobada",
            "rechazada",
            "cancelada",
            "expirada",
        },
        "aprobada": {
            "completada",
            "cancelada",
        },
        "rechazada": set(),
        "cancelada": set(),
        "expirada": set(),
        "completada": set(),
    }

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT res_id_res, res_est_res
            FROM public.res
            WHERE res_id_res = %s
            FOR UPDATE
            """,
            [reserva_id],
        )

        reserva = cursor.fetchone()

        if reserva is None:
            return JsonResponse(
                {"error": "La reserva no existe."},
                status=404,
            )

        estado_actual = reserva[1]

        if nuevo_estado == estado_actual:
            return JsonResponse({
                "mensaje": "La reserva ya tiene ese estado.",
                "res_id_res": reserva_id,
                "res_est_res": estado_actual,
            })

        permitidos = transiciones_permitidas.get(estado_actual, set())

        if nuevo_estado not in permitidos:
            return JsonResponse(
                {
                    "error": (
                        f"No se permite cambiar la reserva "
                        f"de '{estado_actual}' a '{nuevo_estado}'."
                    ),
                    "estado_actual": estado_actual,
                    "estado_solicitado": nuevo_estado,
                },
                status=400,
            )

        try:
            cursor.execute(
                """
                UPDATE public.res
                SET res_est_res = %s
                WHERE res_id_res = %s
                """,
                [nuevo_estado, reserva_id],
            )
        except Exception:
            # Propaga el error para que Django deshaga
            # la transacción si PostgreSQL rechaza el cambio.
            raise

    return JsonResponse({
        "mensaje": "Estado de la reserva actualizado correctamente.",
        "res_id_res": reserva_id,
        "estado_anterior": estado_actual,
        "res_est_res": nuevo_estado,
    })
