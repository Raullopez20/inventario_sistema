from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse, FileResponse, HttpResponse
from django.core.exceptions import ValidationError, PermissionDenied
from .models import AsignacionHistorial, MovimientoStock
from productos.models import Producto
from core.models import Departamento, EmpleadoReceptor
from core.error_handling import handle_errors, validate_data, BusinessLogicError, log_user_action, safe_int_conversion
from datetime import datetime
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from django.template.loader import render_to_string
from django.core.mail import send_mail
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


@login_required
@handle_errors(redirect_on_error='asignaciones:lista_asignaciones')
def agregar_asignacion(request):
    """Vista para agregar una nueva asignación con manejo de errores robusto"""
    try:
        if request.method == 'POST':
            # Validar datos básicos de entrada
            form_data = {
                'producto': request.POST.get('producto'),
                'departamento': request.POST.get('departamento'),
                'empleado': request.POST.get('empleado'),
                'tipo_asignacion': request.POST.get('tipo_asignacion'),
                'fecha_entrega': request.POST.get('fecha_entrega')
            }

            required_fields = ['producto', 'departamento', 'empleado', 'tipo_asignacion', 'fecha_entrega']

            try:
                validate_data(form_data, required_fields)

                # Validaciones específicas
                if form_data['tipo_asignacion'] not in [choice[0] for choice in AsignacionHistorial.TIPOS_ASIGNACION]:
                    raise ValidationError("Tipo de asignación inválido")

                # Validar fecha
                try:
                    # Convertir a datetime aware
                    fecha_entrega_naive = datetime.strptime(form_data['fecha_entrega'], '%Y-%m-%d')
                    fecha_entrega = timezone.make_aware(fecha_entrega_naive)
                    if fecha_entrega.date() > timezone.now().date():
                        raise ValidationError("La fecha de entrega no puede ser futura")
                except ValueError:
                    raise ValidationError("Formato de fecha inválido")

            except ValidationError as e:
                messages.error(request, str(e))
                return render(request, 'asignaciones/agregar_asignacion.html', {
                    'title': 'Nueva Asignación',
                    'productos': Producto.objects.filter(activo=True, estado='DISPONIBLE'),
                    'departamentos': Departamento.objects.filter(activo=True),
                    'empleados': EmpleadoReceptor.objects.filter(activo=True),
                    'tipos_asignacion': AsignacionHistorial.TIPOS_ASIGNACION,
                })

            # Obtener objetos de forma segura
            try:
                producto_id = safe_int_conversion(form_data['producto'])
                departamento_id = safe_int_conversion(form_data['departamento'])
                empleado_id = safe_int_conversion(form_data['empleado'])

                producto = get_object_or_404(Producto, id=producto_id, activo=True)
                departamento = get_object_or_404(Departamento, id=departamento_id, activo=True)
                empleado = get_object_or_404(EmpleadoReceptor, id=empleado_id, activo=True)

            except Exception as e:
                raise BusinessLogicError("Error al obtener los datos requeridos")

            # Validaciones de negocio
            if producto.estado != 'DISPONIBLE':
                raise BusinessLogicError(f"El producto '{producto.numero_serie}' no está disponible para asignación")

            # Verificar que el empleado pertenezca al departamento
            if empleado.departamento != departamento:
                raise BusinessLogicError("El empleado no pertenece al departamento seleccionado")

            # Verificar asignaciones activas del producto
            asignaciones_activas = AsignacionHistorial.objects.filter(
                producto=producto,
                fecha_devolucion__isnull=True,
                activo=True
            ).exists()

            if asignaciones_activas:
                raise BusinessLogicError("El producto ya tiene una asignación activa")

            observaciones = request.POST.get('observaciones', '').strip()

            try:
                # Crear la asignación
                asignacion = AsignacionHistorial.objects.create(
                    producto=producto,
                    departamento=departamento,
                    empleado_receptor=empleado,
                    tipo_asignacion=form_data['tipo_asignacion'],
                    fecha_entrega=fecha_entrega,
                    observaciones_entrega=observaciones,
                    usuario_entrega=request.user,
                    estado_producto_entrega=producto.condicion or 'BUENO'
                )

                # Actualizar el estado del producto
                if form_data['tipo_asignacion'] in ['ENTREGA', 'PRESTAMO']:
                    producto.estado = 'ENTREGADO'
                    producto.save()

                log_user_action(request.user, "ASIGNACION_CREATED",
                               f"Producto: {producto.numero_serie} -> Empleado: {empleado.nombre}")
                messages.success(request, f'Asignación de "{producto.numero_serie}" creada exitosamente.')
                return redirect('asignaciones:detalle_asignacion', asignacion_id=asignacion.id)

            except Exception as e:
                raise BusinessLogicError(f"Error al crear la asignación: {str(e)}")

        # GET request - cargar formulario
        try:
            productos_disponibles = Producto.objects.filter(activo=True, estado='DISPONIBLE')
            departamentos = Departamento.objects.filter(activo=True)
            empleados = EmpleadoReceptor.objects.filter(activo=True)
        except Exception as e:
            messages.error(request, "Error al cargar datos para el formulario")
            return redirect('asignaciones:lista_asignaciones')

        context = {
            'title': 'Nueva Asignación',
            'productos': productos_disponibles,
            'departamentos': departamentos,
            'empleados': empleados,
            'tipos_asignacion': AsignacionHistorial.TIPOS_ASIGNACION,
        }
        return render(request, 'asignaciones/agregar_asignacion.html', context)

    except Exception as e:
        # El decorador manejará la excepción
        raise


@login_required
def lista_asignaciones(request):
    """Vista para listar todas las asignaciones con manejo de errores mejorado"""
    try:
        # Contexto inicial con valores por defecto seguros
        context = {
            'asignaciones': [],
            'departamentos': [],
            'tipos_asignacion': AsignacionHistorial.TIPOS_ASIGNACION,
            'search': '',
            'departamento_selected': '',
            'tipo_selected': '',
            'estado_selected': '',
            'total_asignaciones': 0,
            'asignaciones_activas': 0,
            'asignaciones_devueltas': 0,
        }

        # Obtener departamentos de forma segura
        try:
            context['departamentos'] = Departamento.objects.filter(activo=True).order_by('nombre')
        except Exception as e:
            log_user_action(request.user, "ERROR_DEPARTAMENTOS", f"Error: {str(e)}")

        # Obtener asignaciones base de forma segura
        try:
            asignaciones = AsignacionHistorial.objects.filter(activo=True).select_related(
                'producto', 'departamento', 'empleado_receptor', 'usuario_entrega'
            ).order_by('-fecha_entrega')
        except Exception as e:
            log_user_action(request.user, "ERROR_ASIGNACIONES", f"Error al cargar asignaciones: {str(e)}")
            # En lugar de redirigir, mostrar el template con contexto vacío
            return render(request, 'asignaciones/lista_asignaciones.html', context)

        # Obtener parámetros de filtro de forma segura
        search = request.GET.get('search', '').strip()
        departamento_id = safe_int_conversion(request.GET.get('departamento'))
        tipo_asignacion = request.GET.get('tipo_asignacion', '').strip()
        estado = request.GET.get('estado', '').strip()

        # Aplicar filtros
        try:
            if search:
                asignaciones = asignaciones.filter(
                    Q(producto__id_interno__icontains=search) |
                    Q(producto__numero_serie__icontains=search) |
                    Q(producto__modelo__icontains=search) |
                    Q(empleado_receptor__nombre__icontains=search) |
                    Q(departamento__nombre__icontains=search)
                )

            if departamento_id:
                asignaciones = asignaciones.filter(departamento_id=departamento_id)

            if tipo_asignacion and tipo_asignacion in [choice[0] for choice in AsignacionHistorial.TIPOS_ASIGNACION]:
                asignaciones = asignaciones.filter(tipo_asignacion=tipo_asignacion)

            if estado == 'activas':
                asignaciones = asignaciones.filter(fecha_devolucion__isnull=True)
            elif estado == 'devueltas':
                asignaciones = asignaciones.filter(fecha_devolucion__isnull=False)

        except Exception as e:
            log_user_action(request.user, "ERROR_FILTROS", f"Error al aplicar filtros: {str(e)}")
            # Continuar con las asignaciones base sin filtros

        # Calcular estadísticas
        try:
            todas_asignaciones = AsignacionHistorial.objects.filter(activo=True)
            context.update({
                'total_asignaciones': todas_asignaciones.count(),
                'asignaciones_activas': todas_asignaciones.filter(fecha_devolucion__isnull=True).count(),
                'asignaciones_devueltas': todas_asignaciones.filter(fecha_devolucion__isnull=False).count(),
            })
        except Exception as e:
            log_user_action(request.user, "ERROR_ESTADISTICAS", f"Error en estadísticas: {str(e)}")

        # Actualizar contexto con resultados y filtros aplicados
        context.update({
            'asignaciones': asignaciones,
            'search': search,
            'departamento_selected': str(departamento_id) if departamento_id else '',
            'tipo_selected': tipo_asignacion,
            'estado_selected': estado,
        })

        log_user_action(request.user, "VIEW_ASIGNACIONES", f"Total encontradas: {asignaciones.count()}")
        return render(request, 'asignaciones/lista_asignaciones.html', context)

    except Exception as e:
        log_user_action(request.user, "ERROR_CRITICO_ASIGNACIONES", f"Error crítico: {str(e)}")
        # Crear contexto básico para mostrar página con error
        context = {
            'asignaciones': [],
            'departamentos': [],
            'tipos_asignacion': AsignacionHistorial.TIPOS_ASIGNACION,
            'search': '',
            'departamento_selected': '',
            'tipo_selected': '',
            'estado_selected': '',
            'total_asignaciones': 0,
            'asignaciones_activas': 0,
            'asignaciones_devueltas': 0,
        }
        return render(request, 'asignaciones/lista_asignaciones.html', context)


@login_required
@handle_errors(redirect_on_error='asignaciones:lista_asignaciones')
def detalle_asignacion(request, asignacion_id):
    """Vista para mostrar detalles de una asignación con manejo de errores"""
    try:
        asignacion_id = safe_int_conversion(asignacion_id)
        if not asignacion_id:
            raise BusinessLogicError("ID de asignación inválido")

        asignacion = get_object_or_404(AsignacionHistorial, id=asignacion_id, activo=True)

        movimientos = MovimientoStock.objects.filter(
            producto=asignacion.producto
        ).order_by('-created_at')

        context = {
            'asignacion': asignacion,
            'movimientos': movimientos,
        }

        log_user_action(request.user, "ASIGNACION_DETAIL_ACCESSED", f"Asignación ID: {asignacion.id}")
        return render(request, 'asignaciones/detalle_asignacion.html', context)

    except Exception as e:
        raise


@login_required
def generar_reporte_asignacion(request, asignacion_id):
    """Genera y descarga un PDF profesional con los datos de la asignación"""
    asignacion = get_object_or_404(AsignacionHistorial, id=asignacion_id, activo=True)
    datos = asignacion.datos_reporte()
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, "REPORTE DE ASIGNACIÓN")
    y -= 40
    p.setFont("Helvetica", 12)
    for key, value in datos.items():
        p.drawString(50, y, f"{key}: {value}")
        y -= 22
        if y < 80:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 12)
    p.showPage()
    p.save()
    buffer.seek(0)
    filename = f"reporte_asignacion_{asignacion.id}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)


@login_required
@handle_errors(ajax_response=True)
def devolver_producto(request, asignacion_id):
    """Vista para procesar la devolución de un producto con manejo de errores y feedback mejorado"""
    asignacion_id = safe_int_conversion(asignacion_id)
    if not asignacion_id:
        messages.error(request, "ID de asignación inválido")
        return redirect('asignaciones:lista_asignaciones')

    asignacion = get_object_or_404(AsignacionHistorial, id=asignacion_id, activo=True)

    if request.method == 'GET':
        # Mostrar formulario de devolución
        context = {
            'title': 'Devolver Producto',
            'asignacion': asignacion,
        }
        return render(request, 'asignaciones/devolver_asignacion.html', context)

    if request.method == 'POST':
        if asignacion.fecha_devolucion:
            messages.warning(request, "Esta asignación ya fue devuelta previamente.")
            return redirect('asignaciones:detalle_asignacion', asignacion_id=asignacion.id)

        fecha_devolucion = request.POST.get('fecha_devolucion')
        estado_producto = request.POST.get('estado_producto')
        observaciones = request.POST.get('observaciones_devolucion', '').strip()
        motivo_devolucion = request.POST.get('motivo_devolucion', '').strip() or None

        if not fecha_devolucion or not estado_producto:
            messages.error(request, "Todos los campos obligatorios deben ser completados.")
            return redirect('asignaciones:devolver_producto', asignacion_id=asignacion.id)

        try:
            fecha_devolucion_dt = datetime.strptime(fecha_devolucion, '%Y-%m-%d')
            fecha_devolucion_dt = timezone.make_aware(fecha_devolucion_dt)
            if fecha_devolucion_dt < asignacion.fecha_entrega:
                messages.error(request, "La fecha de devolución no puede ser anterior a la fecha de entrega.")
                return redirect('asignaciones:devolver_producto', asignacion_id=asignacion.id)
        except Exception:
            messages.error(request, "Formato de fecha inválido.")
            return redirect('asignaciones:devolver_producto', asignacion_id=asignacion.id)

        # Usar método del modelo para marcar devolución
        asignacion.fecha_devolucion = fecha_devolucion_dt
        asignacion.marcar_devolucion(
            usuario=request.user,
            motivo=motivo_devolucion,
            observaciones=observaciones,
            estado_producto=estado_producto
        )

        # Registrar movimiento en historial
        MovimientoStock.objects.create(
            producto=asignacion.producto,
            tipo_movimiento='BAJA' if estado_producto == 'AVERIADO' else 'TRANSFERENCIA',
            usuario=request.user,
            ubicacion_origen=asignacion.departamento.nombre,
            ubicacion_destino='Almacén' if estado_producto == 'DISPONIBLE' else 'Taller',
            descripcion=f"Devolución de producto por {asignacion.empleado_receptor.nombre if asignacion.empleado_receptor else 'N/A'}",
            _valor_anterior='{}',
            _valor_nuevo='{}'
        )

        log_user_action(request.user, "ASIGNACION_DEVUELTA", f"Producto: {asignacion.producto.numero_serie} devuelto por {asignacion.empleado_receptor.nombre if asignacion.empleado_receptor else 'N/A'}")
        messages.success(request, f'Producto "{asignacion.producto}" devuelto correctamente. Estado actual: {asignacion.producto.estado}.')
        return redirect('asignaciones:detalle_asignacion', asignacion_id=asignacion.id)

    messages.error(request, "Método no permitido")
    return redirect('asignaciones:lista_asignaciones')


@login_required
@handle_errors(ajax_response=True)
def confirmar_asignacion(request, asignacion_id):
    """Vista para que el empleado confirme la recepción del producto"""
    try:
        if request.method != 'POST':
            raise BusinessLogicError("Método no permitido")

        # Validar ID de la asignación
        asignacion_id = safe_int_conversion(asignacion_id)
        if not asignacion_id:
            raise BusinessLogicError("ID de asignación inválido")

        try:
            asignacion = get_object_or_404(AsignacionHistorial, id=asignacion_id, activo=True)
        except Exception as e:
            raise BusinessLogicError("Asignación no encontrada")

        # Validar que no esté ya confirmada
        if asignacion.confirmado_empleado:
            raise BusinessLogicError("Esta asignación ya fue confirmada")

        # Validar que no esté devuelta
        if asignacion.fecha_devolucion:
            raise BusinessLogicError("No se puede confirmar una asignación devuelta")

        try:
            # Confirmar la asignación
            asignacion.confirmado_empleado = True
            asignacion.fecha_confirmacion_empleado = timezone.now()
            asignacion.save()

            log_user_action(request.user, "ASIGNACION_CONFIRMADA", f"Asignación ID: {asignacion.id}")

            if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Asignación confirmada correctamente'
                })
            else:
                messages.success(request, 'Asignación confirmada correctamente.')
                return redirect('asignaciones:detalle_asignacion', asignacion_id=asignacion.id)

        except Exception as e:
            raise BusinessLogicError(f"Error al confirmar la asignación: {str(e)}")

    except Exception as e:
        # El decorador manejará la excepción
        raise


# Vista AJAX para obtener empleados por departamento
@login_required
@handle_errors(ajax_response=True)
def get_empleados_departamento(request, departamento_id):
    """Vista AJAX para obtener empleados de un departamento específico"""
    try:
        # Validar ID del departamento
        departamento_id = safe_int_conversion(departamento_id)
        if not departamento_id:
            raise BusinessLogicError("ID de departamento inválido")

        try:
            departamento = get_object_or_404(Departamento, id=departamento_id, activo=True)
        except Exception as e:
            raise BusinessLogicError("Departamento no encontrado")

        try:
            empleados = EmpleadoReceptor.objects.filter(
                departamento=departamento,
                activo=True
            ).values('id', 'nombre', 'dni', 'puesto')

            empleados_list = list(empleados)

            return JsonResponse({
                'success': True,
                'empleados': empleados_list
            })

        except Exception as e:
            raise BusinessLogicError(f"Error al obtener empleados: {str(e)}")

    except Exception as e:
        # El decorador manejará la excepción
        raise


@login_required
@handle_errors(redirect_on_error='core:dashboard')
def movimientos_stock(request):
    """Vista para mostrar el historial de movimientos de stock"""
    try:
        # Obtener movimientos base
        movimientos = MovimientoStock.objects.select_related(
            'producto', 'usuario'
        ).order_by('-created_at')

        # Aplicar filtros de búsqueda
        search = request.GET.get('search', '').strip()
        tipo_movimiento = request.GET.get('tipo_movimiento', '').strip()
        fecha_desde = request.GET.get('fecha_desde', '').strip()
        fecha_hasta = request.GET.get('fecha_hasta', '').strip()

        if search:
            movimientos = movimientos.filter(
                Q(producto__numero_serie__icontains=search) |
                Q(producto__modelo__icontains=search) |
                Q(descripcion__icontains=search) |
                Q(ubicacion_origen__icontains=search) |
                Q(ubicacion_destino__icontains=search)
            )

        if tipo_movimiento and tipo_movimiento in [choice[0] for choice in MovimientoStock.TIPOS_MOVIMIENTO]:
            movimientos = movimientos.filter(tipo_movimiento=tipo_movimiento)

        if fecha_desde:
            try:
                fecha_desde_obj = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                movimientos = movimientos.filter(created_at__date__gte=fecha_desde_obj)
            except ValueError:
                messages.warning(request, "Formato de fecha desde inválido")

        if fecha_hasta:
            try:
                fecha_hasta_obj = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
                movimientos = movimientos.filter(created_at__date__lte=fecha_hasta_obj)
            except ValueError:
                messages.warning(request, "Formato de fecha hasta inválido")

        # Calcular estadísticas
        total_movimientos = MovimientoStock.objects.count()
        movimientos_hoy = MovimientoStock.objects.filter(created_at__date=datetime.now().date()).count()

        context = {
            'title': 'Movimientos de Stock',
            'movimientos': movimientos[:100],  # Limitar a 100 resultados
            'tipos_movimiento': MovimientoStock.TIPOS_MOVIMIENTO,
            'search': search,
            'tipo_selected': tipo_movimiento,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'total_movimientos': total_movimientos,
            'movimientos_hoy': movimientos_hoy,
        }

        log_user_action(request.user, "MOVIMIENTOS_STOCK_ACCESSED")
        return render(request, 'asignaciones/movimientos_stock.html', context)

    except Exception as e:
        messages.error(request, f"Error al cargar movimientos de stock: {str(e)}")
        return redirect('core:dashboard')



@login_required
@require_POST
@handle_errors(ajax_response=True)
def enviar_recordatorio(request):
    """Envía un recordatorio real por email al empleado receptor de la asignación"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        asignacion_id = safe_int_conversion(data.get('asignacion_id'))
        if not asignacion_id:
            return JsonResponse({'success': False, 'error': 'ID inválido'})
        asignacion = get_object_or_404(AsignacionHistorial, id=asignacion_id, activo=True)
        if asignacion.fecha_devolucion:
            return JsonResponse({'success': False, 'error': 'La asignación ya fue devuelta'})
        empleado = asignacion.empleado_receptor
        if not empleado or not empleado.email:
            return JsonResponse({'success': False, 'error': 'El empleado no tiene email registrado'})
        # Enviar email real
        subject = "Recordatorio de Asignación de Producto"
        message = render_to_string("asignaciones/email_recordatorio.txt", {
            "asignacion": asignacion,
            "empleado": empleado,
        })
        send_mail(
            subject,
            message,
            None,  # Usa el DEFAULT_FROM_EMAIL
            [empleado.email],
            fail_silently=False,
        )
        log_user_action(request.user, "RECORDATORIO_ENVIADO", f"Asignación ID: {asignacion.id} a {empleado.nombre}")
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
