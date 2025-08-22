from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from .models import Producto
from .models_pegatinas import TipoProducto, DatosPersonalizados, PegatinasIdentificativas
from core.models import Categoria, Marca, Ubicacion, Proveedor
from .forms import ProductoForm, DatosPersonalizadosForm
from core.error_handling import handle_errors, validate_data, BusinessLogicError, log_user_action, safe_int_conversion, validate_file_upload
import json


@login_required
@handle_errors(redirect_on_error='productos:lista_productos')
def agregar_producto(request):
    """Vista simplificada para agregar un nuevo producto"""
    try:
        if request.method == 'POST':
            form = ProductoForm(request.POST, request.FILES)

            if form.is_valid():
                try:
                    producto = form.save(commit=False)

                    # Generar número de serie automático si no se proporciona
                    if not producto.numero_serie:
                        producto.numero_serie = producto.generar_numero_serie_automatico()

                    # Generar ID interno si no existe
                    if not producto.id_interno:
                        producto.id_interno = producto.generar_id_interno()

                    # Guardar el producto
                    producto.save()

                    # Procesar campos personalizados de categoría si existen
                    categoria = producto.categoria
                    if categoria and hasattr(categoria, 'campos_especificos'):
                        campos_categoria = categoria.campos_especificos
                        if campos_categoria:
                            datos_personalizados = {}

                            # Buscar campos que empiecen con 'campo_categoria_'
                            for key, value in request.POST.items():
                                if key.startswith('campo_categoria_') and value.strip():
                                    campo_nombre = key.replace('campo_categoria_', '')
                                    datos_personalizados[campo_nombre] = value.strip()

                            # Guardar en especificaciones del producto
                            if datos_personalizados:
                                producto.especificaciones = datos_personalizados
                                producto.save()

                    log_user_action(request.user, "PRODUCTO_CREATED", f"Producto: {producto.numero_serie}")
                    messages.success(request, f'Producto "{producto.numero_serie}" agregado exitosamente.')
                    return redirect('productos:detalle_producto', producto_id=producto.id)

                except Exception as e:
                    # Si hay error en el guardado, intentar limpiar
                    if 'producto' in locals() and hasattr(producto, 'id') and producto.id:
                        try:
                            producto.delete()
                        except:
                            pass
                    messages.error(request, f"Error al crear el producto: {str(e)}")

            else:
                # Mostrar errores del formulario
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        else:
            form = ProductoForm()

        # Cargar datos para el contexto de forma segura
        context = {
            'form': form,
            'title': 'Agregar Nuevo Producto',
            'categorias': Categoria.objects.filter(activo=True).order_by('nombre'),
            'marcas': Marca.objects.filter(activo=True).order_by('nombre'),
            'ubicaciones': Ubicacion.objects.filter(activo=True).order_by('nombre'),
            'proveedores': Proveedor.objects.filter(activo=True).order_by('nombre'),
        }

        return render(request, 'productos/agregar_producto.html', context)

    except Exception as e:
        messages.error(request, f"Error inesperado: {str(e)}")
        return redirect('productos:lista_productos')


@login_required
@handle_errors(redirect_on_error='productos:lista_productos')
def lista_productos(request):
    """Vista para listar todos los productos con manejo de errores"""
    try:
        # Inicializar valores por defecto
        context = {
            'productos': [],
            'categorias': [],
            'marcas': [],
            'estados': Producto.ESTADOS,
            'search': '',
            'categoria_selected': '',
            'estado_selected': '',
            'productos_disponibles': 0,
            'productos_entregados': 0,
            'productos_averiados': 0,
            'total_productos': 0,
        }

        # Obtener productos base de forma segura
        try:
            productos = Producto.objects.filter(activo=True).select_related(
                'categoria', 'marca', 'ubicacion_actual', 'proveedor'
            ).order_by('-created_at')
        except Exception as e:
            messages.error(request, "Error al cargar la lista de productos")
            return render(request, 'productos/lista_productos_mejorada.html', context)

        # Aplicar filtros de forma segura
        search = request.GET.get('search', '').strip()
        categoria_id = safe_int_conversion(request.GET.get('categoria'))
        estado = request.GET.get('estado', '').strip()

        try:
            if search:
                productos = productos.filter(
                    Q(modelo__icontains=search) |
                    Q(numero_serie__icontains=search) |
                    Q(observaciones__icontains=search)
                )

            if categoria_id:
                productos = productos.filter(categoria_id=categoria_id)

            if estado and estado in [choice[0] for choice in Producto.ESTADOS]:
                productos = productos.filter(estado=estado)

        except Exception as e:
            messages.warning(request, "Error al aplicar filtros de búsqueda")

        # Calcular estadísticas de forma segura
        try:
            todos_productos = Producto.objects.filter(activo=True)
            context.update({
                'productos_disponibles': todos_productos.filter(estado='DISPONIBLE').count(),
                'productos_entregados': todos_productos.filter(estado='ENTREGADO').count(),
                'productos_averiados': todos_productos.filter(estado='AVERIADO').count(),
                'total_productos': todos_productos.count(),
            })
        except Exception as e:
            messages.warning(request, "Error al calcular estadísticas")

        # Cargar datos de referencia de forma segura
        try:
            context['categorias'] = Categoria.objects.filter(activo=True)
            context['marcas'] = Marca.objects.filter(activo=True)
        except Exception as e:
            messages.warning(request, "Error al cargar categorías y marcas")

        # Actualizar contexto final
        context.update({
            'productos': productos,
            'search': search,
            'categoria_selected': categoria_id,
            'estado_selected': estado,
        })

        log_user_action(request.user, "PRODUCTOS_LIST_ACCESSED")
        return render(request, 'productos/lista_productos_mejorada.html', context)

    except Exception as e:
        # El decorador manejará la excepción
        raise


@login_required
@handle_errors(redirect_on_error='productos:lista_productos')
def editar_producto(request, producto_id):
    """Vista para editar un producto existente con manejo de errores"""
    try:
        # Validar ID del producto
        producto_id = safe_int_conversion(producto_id)
        if not producto_id:
            raise BusinessLogicError("ID de producto inválido")

        try:
            producto = get_object_or_404(Producto, id=producto_id, activo=True)
        except Exception as e:
            raise BusinessLogicError("Producto no encontrado o no disponible")

        if request.method == 'POST':
            form = ProductoForm(request.POST, request.FILES, instance=producto)

            if form.is_valid():
                try:
                    producto_editado = form.save(commit=False)

                    # Manejar eliminación de imagen
                    if request.POST.get('remove_image') == 'true':
                        if producto_editado.imagen:
                            # Eliminar archivo físico
                            try:
                                producto_editado.imagen.delete(save=False)
                            except:
                                pass
                        producto_editado.imagen = None

                    # Procesar campos personalizados de categoría si existen
                    categoria = producto_editado.categoria
                    if categoria and hasattr(categoria, 'campos_especificos'):
                        campos_categoria = categoria.campos_especificos
                        if campos_categoria:
                            datos_personalizados = {}

                            # Buscar campos que empiecen con 'campo_categoria_'
                            for key, value in request.POST.items():
                                if key.startswith('campo_categoria_') and value.strip():
                                    campo_nombre = key.replace('campo_categoria_', '')
                                    datos_personalizados[campo_nombre] = value.strip()

                            # Guardar en especificaciones del producto
                            if datos_personalizados:
                                producto_editado.especificaciones = datos_personalizados

                    # Guardar el producto
                    producto_editado.save()

                    log_user_action(request.user, "PRODUCTO_UPDATED", f"Producto: {producto.numero_serie}")
                    messages.success(request, f'Producto "{producto.numero_serie}" actualizado exitosamente.')
                    return redirect('productos:detalle_producto', producto_id=producto.id)

                except Exception as e:
                    messages.error(request, f"Error al actualizar el producto: {str(e)}")

            else:
                # Mostrar errores del formulario
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        else:
            form = ProductoForm(instance=producto)

        # Cargar datos para el contexto de forma segura
        try:
            from .models_pegatinas import PegatinasIdentificativas
            pegatinas = PegatinasIdentificativas.objects.filter(
                producto=producto,
                activa=True
            ).order_by('-fecha_generacion')
        except Exception:
            pegatinas = []

        context = {
            'form': form,
            'producto': producto,
            'title': f'Editar Producto - {producto.numero_serie}',
            'categorias': Categoria.objects.filter(activo=True).order_by('nombre'),
            'marcas': Marca.objects.filter(activo=True).order_by('nombre'),
            'ubicaciones': Ubicacion.objects.filter(activo=True).order_by('nombre'),
            'proveedores': Proveedor.objects.filter(activo=True).order_by('nombre'),
            'pegatinas': pegatinas,
        }
        return render(request, 'productos/editar_producto.html', context)

    except Exception as e:
        messages.error(request, f"Error inesperado: {str(e)}")
        return redirect('productos:lista_productos')


@login_required
@handle_errors(ajax_response=True)
def detalle_producto(request, producto_id):
    """Vista para mostrar detalles de un producto con manejo de errores"""
    try:
        # Validar ID del producto
        producto_id = safe_int_conversion(producto_id)
        if not producto_id:
            raise BusinessLogicError("ID de producto inválido")

        try:
            producto = get_object_or_404(Producto, id=producto_id, activo=True)
        except Exception as e:
            raise BusinessLogicError("Producto no encontrado")

        # Obtener datos relacionados de forma segura
        try:
            # Historial de asignaciones
            from asignaciones.models import AsignacionHistorial
            historial_asignaciones = AsignacionHistorial.objects.filter(
                producto=producto
            ).select_related('empleado_receptor', 'departamento').order_by('-fecha_entrega')

        except Exception as e:
            messages.warning(request, "Error al cargar historial de asignaciones")
            historial_asignaciones = []

        context = {
            'producto': producto,
            'historial_asignaciones': historial_asignaciones,
        }

        log_user_action(request.user, "PRODUCTO_DETAIL_ACCESSED", f"Producto: {producto.numero_serie}")
        return render(request, 'productos/detalle_producto.html', context)

    except Exception as e:
        # El decorador manejará la excepción
        raise


@login_required
@handle_errors(ajax_response=True)
def eliminar_producto(request, producto_id):
    """Vista para eliminar (desactivar) un producto con manejo de errores"""
    try:
        if request.method != 'POST':
            raise BusinessLogicError("Método no permitido")

        # Validar ID del producto
        producto_id = safe_int_conversion(producto_id)
        if not producto_id:
            raise BusinessLogicError("ID de producto inválido")

        try:
            producto = get_object_or_404(Producto, id=producto_id, activo=True)
        except Exception as e:
            raise BusinessLogicError("Producto no encontrado")

        # Validar permisos
        if not (request.user.is_staff or producto.usuario_creacion == request.user):
            raise PermissionDenied("No tiene permisos para eliminar este producto")

        # Verificar si el producto está asignado
        try:
            from asignaciones.models import AsignacionHistorial
            asignaciones_activas = AsignacionHistorial.objects.filter(
                producto=producto,
                fecha_devolucion__isnull=True,
                activo=True
            ).exists()

            if asignaciones_activas:
                raise BusinessLogicError("No se puede eliminar un producto que tiene asignaciones activas")

        except AsignacionHistorial.DoesNotExist:
            pass  # No hay asignaciones, se puede eliminar

        # Realizar eliminación lógica
        try:
            producto.activo = False
            producto.save()

            log_user_action(request.user, "PRODUCTO_DELETED", f"Producto: {producto.numero_serie}")

            if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Producto "{producto.numero_serie}" eliminado correctamente'
                })
            else:
                messages.success(request, f'Producto "{producto.numero_serie}" eliminado correctamente.')
                return redirect('productos:lista_productos')

        except Exception as e:
            raise BusinessLogicError(f"Error al eliminar el producto: {str(e)}")

    except Exception as e:
        # El decorador manejará la excepción
        raise


# Vista AJAX para obtener datos de productos
@login_required
@handle_errors(ajax_response=True)
def get_producto_data(request, producto_id):
    """Vista AJAX para obtener datos de un producto con manejo de errores"""
    try:
        # Validar ID del producto
        producto_id = safe_int_conversion(producto_id)
        if not producto_id:
            raise BusinessLogicError("ID de producto inválido")

        try:
            producto = get_object_or_404(Producto, id=producto_id, activo=True)
        except Exception as e:
            raise BusinessLogicError("Producto no encontrado")

        # Preparar datos de respuesta de forma segura
        try:
            data = {
                'id': producto.id,
                'numero_serie': producto.numero_serie,
                'modelo': producto.modelo,
                'categoria': producto.categoria.nombre if producto.categoria else '',
                'marca': producto.marca.nombre if producto.marca else '',
                'estado': producto.estado,
                'estado_display': producto.get_estado_display(),
                'condicion': producto.condicion,
                'condicion_display': producto.get_condicion_display(),
                'precio_compra': float(producto.precio_compra) if producto.precio_compra else 0,
                'fecha_compra': producto.fecha_compra.isoformat() if producto.fecha_compra else None,
                'ubicacion': producto.ubicacion_actual.nombre if producto.ubicacion_actual else '',
                'observaciones': producto.observaciones or ''
            }

            return JsonResponse({'success': True, 'data': data})

        except Exception as e:
            raise BusinessLogicError(f"Error al preparar datos del producto: {str(e)}")

    except Exception as e:
        # El decorador manejará la excepción
        raise


# ==============================================
# VISTAS PARA SISTEMA DE PEGATINAS (NUEVAS)
# ==============================================

@login_required
@handle_errors(ajax_response=True)
def detectar_tipo_producto(request):
    """Vista AJAX para detectar automáticamente el tipo de producto"""
    try:
        if request.method != 'POST':
            raise BusinessLogicError("Método no permitido")

        # Obtener solo la categoría (simplificado)
        categoria_id = safe_int_conversion(request.POST.get('categoria'))

        if not categoria_id:
            return JsonResponse({
                'success': False,
                'message': 'ID de categoría requerido'
            })

        try:
            categoria = get_object_or_404(Categoria, id=categoria_id)
        except Exception as e:
            raise BusinessLogicError("Categoría no encontrada")

        # Lógica de detección automática basada en patrones
        tipo_detectado = None
        campos_personalizados = []

        try:
            # Detectar por categoría
            categoria_lower = categoria.nombre.lower()

            if 'audio' in categoria_lower or 'sonido' in categoria_lower:
                tipo_detectado = 'EQUIPOS_AUDIO'
                campos_personalizados = [
                    {'nombre': 'potencia', 'tipo': 'NUMERO', 'requerido': True},
                    {'nombre': 'impedancia', 'tipo': 'TEXTO', 'requerido': False},
                    {'nombre': 'respuesta_frecuencia', 'tipo': 'TEXTO', 'requerido': False},
                    {'nombre': 'conectores', 'tipo': 'TEXTO', 'requerido': False}
                ]
            elif 'video' in categoria_lower or 'imagen' in categoria_lower or 'monitor' in categoria_lower:
                tipo_detectado = 'EQUIPOS_VIDEO'
                campos_personalizados = [
                    {'nombre': 'resolucion', 'tipo': 'TEXTO', 'requerido': True},
                    {'nombre': 'tamaño_pantalla', 'tipo': 'NUMERO', 'requerido': False},
                    {'nombre': 'tipo_panel', 'tipo': 'TEXTO', 'requerido': False},
                    {'nombre': 'puertos', 'tipo': 'TEXTO', 'requerido': False}
                ]
            elif 'informatica' in categoria_lower or 'ordenador' in categoria_lower or 'computador' in categoria_lower:
                tipo_detectado = 'EQUIPOS_INFORMATICA'
                campos_personalizados = [
                    {'nombre': 'procesador', 'tipo': 'TEXTO', 'requerido': True},
                    {'nombre': 'memoria_ram', 'tipo': 'TEXTO', 'requerido': True},
                    {'nombre': 'disco_duro', 'tipo': 'TEXTO', 'requerido': False},
                    {'nombre': 'sistema_operativo', 'tipo': 'TEXTO', 'requerido': False}
                ]
            elif 'impresora' in categoria_lower or 'impresion' in categoria_lower:
                tipo_detectado = 'EQUIPOS_IMPRESION'
                campos_personalizados = [
                    {'nombre': 'tipo_impresion', 'tipo': 'TEXTO', 'requerido': True},
                    {'nombre': 'velocidad', 'tipo': 'NUMERO', 'requerido': False},
                    {'nombre': 'resolucion_dpi', 'tipo': 'NUMERO', 'requerido': False},
                    {'nombre': 'conectividad', 'tipo': 'TEXTO', 'requerido': False}
                ]
            elif 'proyector' in categoria_lower:
                tipo_detectado = 'PROYECTORES'
                campos_personalizados = [
                    {'nombre': 'lumenes', 'tipo': 'NUMERO', 'requerido': True},
                    {'nombre': 'resolucion_nativa', 'tipo': 'TEXTO', 'requerido': True},
                    {'nombre': 'tipo_lampara', 'tipo': 'TEXTO', 'requerido': False},
                    {'nombre': 'vida_lampara', 'tipo': 'NUMERO', 'requerido': False}
                ]
            else:
                # Tipo genérico
                tipo_detectado = 'EQUIPOS_GENERICOS'
                campos_personalizados = [
                    {'nombre': 'especificaciones', 'tipo': 'TEXTO_LARGO', 'requerido': False},
                    {'nombre': 'accesorios', 'tipo': 'TEXTO', 'requerido': False}
                ]

            log_user_action(request.user, "TIPO_PRODUCTO_DETECTADO",
                           f"Tipo: {tipo_detectado} para categoría: {categoria.nombre}")

            return JsonResponse({
                'success': True,
                'tipo_detectado': tipo_detectado,
                'campos_personalizados': campos_personalizados,
                'mensaje': f'Tipo detectado automáticamente: {tipo_detectado}'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error en detección: {str(e)}'
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error del servidor: {str(e)}'
        })


@login_required
@handle_errors(redirect_on_error='productos:lista_productos')
def gestionar_datos_personalizados(request, producto_id):
    """Vista para gestionar datos personalizados de un producto"""
    try:
        # Validar ID del producto
        producto_id = safe_int_conversion(producto_id)
        if not producto_id:
            raise BusinessLogicError("ID de producto inválido")

        try:
            producto = get_object_or_404(Producto, id=producto_id, activo=True)
        except Exception as e:
            raise BusinessLogicError("Producto no encontrado")

        # Validar permisos
        if not (request.user.is_staff or producto.usuario_creacion == request.user):
            raise PermissionDenied("No tiene permisos para gestionar datos de este producto")

        if request.method == 'POST':
            try:
                # Obtener o crear datos personalizados
                datos_personalizados, created = DatosPersonalizados.objects.get_or_create(
                    producto=producto,
                    defaults={'datos_json': {}}
                )

                # Procesar campos del formulario
                datos_actualizados = {}
                for key, value in request.POST.items():
                    if key.startswith('campo_') and value.strip():
                        campo_nombre = key.replace('campo_', '')
                        datos_actualizados[campo_nombre] = value.strip()

                # Actualizar datos
                datos_personalizados.datos_json = datos_actualizados
                datos_personalizados.save()

                log_user_action(request.user, "DATOS_PERSONALIZADOS_UPDATED",
                               f"Producto: {producto.numero_serie}")
                messages.success(request, 'Datos personalizados actualizados correctamente.')
                return redirect('productos:detalle_producto', producto_id=producto.id)

            except Exception as e:
                raise BusinessLogicError(f"Error al guardar datos personalizados: {str(e)}")

        # GET request - mostrar formulario
        try:
            datos_personalizados = DatosPersonalizados.objects.filter(producto=producto).first()
            tipo_producto = TipoProducto.objects.filter(categoria=producto.categoria).first()
        except Exception as e:
            messages.warning(request, "Error al cargar datos personalizados")
            datos_personalizados = None
            tipo_producto = None

        context = {
            'producto': producto,
            'datos_personalizados': datos_personalizados,
            'tipo_producto': tipo_producto,
        }
        return render(request, 'productos/gestionar_datos_personalizados.html', context)

    except Exception as e:
        # El decorador manejará la excepción
        raise


@login_required
@handle_errors(redirect_on_error='productos:lista_productos')
def generar_pegatinas(request, producto_id):
    """Vista para generar pegatinas identificativas de un producto"""
    try:
        # Validar ID del producto
        producto_id = safe_int_conversion(producto_id)
        if not producto_id:
            raise BusinessLogicError("ID de producto inválido")

        try:
            producto = get_object_or_404(Producto, id=producto_id, activo=True)
        except Exception as e:
            raise BusinessLogicError("Producto no encontrado")

        if request.method == 'POST':
            try:
                # Obtener tipos de pegatinas a generar
                tipos_pegatinas = []

                # Si viene del AJAX con tipos específicos (desde la página de generar pegatinas)
                if request.META.get('CONTENT_TYPE') == 'application/json':
                    import json
                    data = json.loads(request.body)
                    tipos_pegatinas = data.get('tipos', ['QR'])
                elif request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                    # AJAX desde el detalle del producto (generarPegatinasSeleccionadas)
                    import json
                    try:
                        data = json.loads(request.body)
                        tipos_pegatinas = data.get('tipos', ['QR'])
                    except:
                        # Si no puede parsear JSON, usar QR por defecto
                        tipos_pegatinas = ['QR']
                else:
                    # Petición POST normal desde formulario
                    # Obtener los tipos seleccionados del formulario
                    for tipo in ['QR', 'CODIGO_BARRAS', 'ETIQUETA_SIMPLE', 'ETIQUETA_COMPLETA']:
                        if request.POST.get(f'tipo_{tipo}'):
                            tipos_pegatinas.append(tipo)

                    # Si no se seleccionó nada, usar QR por defecto
                    if not tipos_pegatinas:
                        tipos_pegatinas = ['QR']

                pegatinas_generadas = []

                for tipo_pegatina in tipos_pegatinas:
                    try:
                        if tipo_pegatina == 'QR':
                            pegatina = _generar_pegatina_qr(producto)
                        elif tipo_pegatina == 'CODIGO_BARRAS':
                            pegatina = _generar_pegatina_codigo_barras(producto)
                        elif tipo_pegatina == 'ETIQUETA_SIMPLE':
                            pegatina = _generar_pegatina_etiqueta_simple(producto)
                        elif tipo_pegatina == 'ETIQUETA_COMPLETA':
                            pegatina = _generar_pegatina_etiqueta_completa(producto)
                        else:
                            continue  # Tipo no válido, saltar

                        pegatinas_generadas.append(pegatina)

                    except Exception as e:
                        # Log del error pero continuar con otros tipos
                        print(f"Error generando pegatina {tipo_pegatina}: {str(e)}")
                        continue

                if not pegatinas_generadas:
                    raise Exception("No se pudo generar ninguna pegatina")

                log_user_action(request.user, "PEGATINAS_GENERADAS",
                               f"Producto: {producto.numero_serie}, Tipos: {', '.join(tipos_pegatinas)}")

                mensaje = f'{len(pegatinas_generadas)} pegatina(s) generada(s) correctamente.'
                messages.success(request, mensaje)

                # Si es petición AJAX, devolver JSON
                if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': mensaje,
                        'pegatinas_generadas': len(pegatinas_generadas),
                        'tipos_generados': tipos_pegatinas
                    })

                # Petición normal, redirigir a ver pegatinas
                return redirect('productos:ver_pegatinas', producto_id=producto.id)

            except Exception as e:
                error_msg = f"Error al generar pegatinas: {str(e)}"

                if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': error_msg
                    })

                messages.error(request, error_msg)

        context = {
            'producto': producto,
        }
        return render(request, 'productos/generar_pegatinas.html', context)

    except Exception as e:
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': f"Error del servidor: {str(e)}"
            })
        messages.error(request, f"Error inesperado: {str(e)}")
        return redirect('productos:lista_productos')


def _generar_pegatina_qr(producto):
    """Generar pegatina con código QR"""
    import qrcode
    from io import BytesIO
    from django.core.files.base import ContentFile

    # Generar código QR con información del producto
    qr_data = f"{producto.numero_serie}|{producto.marca.nombre if producto.marca else 'Sin marca'}|{producto.modelo}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    # Generar imagen QR
    qr_img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)

    # Crear registro de pegatina
    pegatina = PegatinasIdentificativas.objects.create(
        producto=producto,
        tipo_pegatina='QR',
        codigo_generado=producto.numero_serie,
        activa=True
    )

    # Guardar la imagen del QR
    filename = f"qr_{producto.numero_serie}_{pegatina.id}.png"
    pegatina.imagen_pegatina.save(
        filename,
        ContentFile(buffer.getvalue()),
        save=True
    )

    return pegatina


def _generar_pegatina_codigo_barras(producto):
    """Generar pegatina con código de barras"""
    import barcode
    from barcode.writer import ImageWriter
    from io import BytesIO
    from django.core.files.base import ContentFile

    # Usar código de barras del producto o generar uno basado en número de serie
    codigo = producto.codigo_barras if producto.codigo_barras else producto.numero_serie

    # Generar código de barras (Code128)
    code128 = barcode.get('code128', codigo, writer=ImageWriter())
    buffer = BytesIO()
    code128.write(buffer)
    buffer.seek(0)

    # Crear registro de pegatina
    pegatina = PegatinasIdentificativas.objects.create(
        producto=producto,
        tipo_pegatina='CODIGO_BARRAS',
        codigo_generado=codigo,
        activa=True
    )

    # Guardar la imagen del código de barras
    filename = f"barcode_{producto.numero_serie}_{pegatina.id}.png"
    pegatina.imagen_pegatina.save(
        filename,
        ContentFile(buffer.getvalue()),
        save=True
    )

    return pegatina


def _generar_pegatina_etiqueta_simple(producto):
    """Generar etiqueta simple con información básica"""
    from PIL import Image, ImageDraw, ImageFont
    from io import BytesIO
    from django.core.files.base import ContentFile

    # Crear imagen para la etiqueta
    width, height = 400, 200
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    try:
        # Intentar cargar una fuente del sistema
        font_large = ImageFont.truetype("arial.ttf", 20)
        font_medium = ImageFont.truetype("arial.ttf", 14)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except:
        # Usar fuente por defecto si no encuentra Arial
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Dibujar contenido de la etiqueta
    y_pos = 20
    draw.text((20, y_pos), f"N° Serie: {producto.numero_serie}", fill='black', font=font_large)
    y_pos += 30
    draw.text((20, y_pos), f"Marca: {producto.marca.nombre if producto.marca else 'N/A'}", fill='black', font=font_medium)
    y_pos += 25
    draw.text((20, y_pos), f"Modelo: {producto.modelo}", fill='black', font=font_medium)
    y_pos += 25
    draw.text((20, y_pos), f"Categoría: {producto.categoria.nombre if producto.categoria else 'N/A'}", fill='black', font=font_small)

    # Guardar imagen
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    # Crear registro de pegatina
    pegatina = PegatinasIdentificativas.objects.create(
        producto=producto,
        tipo_pegatina='ETIQUETA_SIMPLE',
        codigo_generado=producto.numero_serie,
        activa=True
    )

    # Guardar la imagen de la etiqueta
    filename = f"etiqueta_simple_{producto.numero_serie}_{pegatina.id}.png"
    pegatina.imagen_pegatina.save(
        filename,
        ContentFile(buffer.getvalue()),
        save=True
    )

    return pegatina


def _generar_pegatina_etiqueta_completa(producto):
    """Generar etiqueta completa con toda la información del producto"""
    from PIL import Image, ImageDraw, ImageFont
    from io import BytesIO
    from django.core.files.base import ContentFile
    import qrcode

    # Crear imagen más grande para la etiqueta completa
    width, height = 600, 400
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arial.ttf", 24)
        font_large = ImageFont.truetype("arial.ttf", 16)
        font_medium = ImageFont.truetype("arial.ttf", 12)
        font_small = ImageFont.truetype("arial.ttf", 10)
    except:
        font_title = ImageFont.load_default()
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Título
    y_pos = 20
    draw.text((20, y_pos), "ETIQUETA DE INVENTARIO", fill='black', font=font_title)

    # Línea separadora
    y_pos += 35
    draw.line([(20, y_pos), (width-20, y_pos)], fill='black', width=2)

    # Información principal
    y_pos += 20
    draw.text((20, y_pos), f"N° Serie: {producto.numero_serie}", fill='black', font=font_large)
    y_pos += 25
    draw.text((20, y_pos), f"Marca: {producto.marca.nombre if producto.marca else 'N/A'}", fill='black', font=font_medium)
    y_pos += 20
    draw.text((20, y_pos), f"Modelo: {producto.modelo}", fill='black', font=font_medium)
    y_pos += 20
    draw.text((20, y_pos), f"Categoría: {producto.categoria.nombre if producto.categoria else 'N/A'}", fill='black', font=font_medium)
    y_pos += 20
    draw.text((20, y_pos), f"Estado: {producto.get_estado_display()}", fill='black', font=font_medium)

    if producto.ubicacion_actual:
        y_pos += 20
        draw.text((20, y_pos), f"Ubicación: {producto.ubicacion_actual.nombre}", fill='black', font=font_small)

    # Generar QR pequeño para incluir en la etiqueta
    qr_data = f"{producto.numero_serie}|{producto.marca.nombre if producto.marca else 'Sin marca'}|{producto.modelo}"
    qr = qrcode.QRCode(version=1, box_size=3, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    # Redimensionar QR y pegarlo en la etiqueta
    qr_img = qr_img.resize((120, 120))
    img.paste(qr_img, (width-150, 50))

    # Fecha de generación
    from datetime import datetime
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    draw.text((20, height-30), f"Generado: {fecha_actual}", fill='gray', font=font_small)

    # Guardar imagen
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    # Crear registro de pegatina
    pegatina = PegatinasIdentificativas.objects.create(
        producto=producto,
        tipo_pegatina='ETIQUETA_COMPLETA',
        codigo_generado=producto.numero_serie,
        activa=True
    )

    # Guardar la imagen de la etiqueta
    filename = f"etiqueta_completa_{producto.numero_serie}_{pegatina.id}.png"
    pegatina.imagen_pegatina.save(
        filename,
        ContentFile(buffer.getvalue()),
        save=True
    )

    return pegatina


@login_required
@handle_errors(redirect_on_error='productos:lista_productos')
def ver_pegatinas(request, producto_id):
    """Vista para ver las pegatinas de un producto"""
    try:
        # Validar ID del producto
        producto_id = safe_int_conversion(producto_id)
        if not producto_id:
            raise BusinessLogicError("ID de producto inválido")

        try:
            producto = get_object_or_404(Producto, id=producto_id, activo=True)
        except Exception as e:
            raise BusinessLogicError("Producto no encontrado")

        try:
            pegatinas = PegatinasIdentificativas.objects.filter(
                producto=producto,
                activa=True
            ).order_by('-fecha_generacion')
        except Exception as e:
            messages.warning(request, "Error al cargar pegatinas")
            pegatinas = []

        context = {
            'producto': producto,
            'pegatinas': pegatinas,
        }
        return render(request, 'productos/ver_pegatinas.html', context)

    except Exception as e:
        # El decorador manejará la excepción
        raise


@login_required
@handle_errors(ajax_response=True)
def imprimir_pegatina(request, pegatina_id):
    """Vista para imprimir una pegatina específica"""
    try:
        # Validar ID de la pegatina
        pegatina_id = safe_int_conversion(pegatina_id)
        if not pegatina_id:
            raise BusinessLogicError("ID de pegatina inválido")

        try:
            pegatina = get_object_or_404(PegatinasIdentificativas, id=pegatina_id)
        except Exception as e:
            raise BusinessLogicError("Pegatina no encontrada")

        # Generar HTML para impresión
        try:
            from django.template.loader import render_to_string

            html_content = render_to_string('productos/pegatina_impresion.html', {
                'pegatina': pegatina,
                'producto': pegatina.producto
            })

            log_user_action(request.user, "PEGATINA_IMPRESA",
                           f"Pegatina ID: {pegatina.id}")

            return HttpResponse(html_content, content_type='text/html')

        except Exception as e:
            raise BusinessLogicError(f"Error al generar pegatina para impresión: {str(e)}")

    except Exception as e:
        # El decorador manejará la excepción
        raise


@login_required
@handle_errors(ajax_response=True)
def descargar_pegatina(request, pegatina_id):
    """Vista para descargar una pegatina como archivo"""
    try:
        # Validar ID de la pegatina
        pegatina_id = safe_int_conversion(pegatina_id)
        if not pegatina_id:
            raise BusinessLogicError("ID de pegatina inválido")

        try:
            pegatina = get_object_or_404(PegatinasIdentificativas, id=pegatina_id)
        except Exception as e:
            raise BusinessLogicError("Pegatina no encontrada")

        try:
            # Obtener la URL absoluta de la imagen
            imagen_url = None
            if pegatina.imagen_pegatina:
                imagen_url = request.build_absolute_uri(pegatina.imagen_pegatina.url)

            # Generar archivo HTML para descarga
            from django.template.loader import render_to_string

            html_content = render_to_string('productos/pegatina_pdf.html', {
                'pegatina': pegatina,
                'producto': pegatina.producto,
                'imagen_url_absoluta': imagen_url,
                'request': request
            })

            # Crear respuesta HTML para descarga
            response = HttpResponse(html_content, content_type='text/html')
            response['Content-Disposition'] = f'attachment; filename="pegatina_{pegatina.producto.numero_serie}_{pegatina.get_tipo_pegatina_display()}.html"'

            log_user_action(request.user, "PEGATINA_DESCARGADA",
                           f"Pegatina ID: {pegatina.id}")

            return response

        except Exception as e:
            raise BusinessLogicError(f"Error al descargar pegatina: {str(e)}")

    except Exception as e:
        # El decorador manejará la excepción
        raise


@csrf_exempt
@login_required
def obtener_campos_categoria(request):
    """Vista AJAX para obtener los campos personalizados de una categoría"""
    if request.method == 'GET':
        categoria_id = request.GET.get('categoria_id')
        try:
            if categoria_id:
                categoria = Categoria.objects.get(id=categoria_id, activo=True)
                campos_especificos = categoria.campos_especificos

                return JsonResponse({
                    'success': True,
                    'campos': campos_especificos,
                    'categoria_nombre': categoria.nombre
                })
            else:
                return JsonResponse({
                    'success': True,
                    'campos': {},
                    'categoria_nombre': ''
                })
        except Categoria.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Categoría no encontrada'
            })

    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
@handle_errors(ajax_response=True)
def marcar_pegatina_impresa(request, pegatina_id):
    """Vista para marcar una pegatina como impresa"""
    try:
        if request.method != 'POST':
            raise BusinessLogicError("Método no permitido")

        # Validar ID de la pegatina
        pegatina_id = safe_int_conversion(pegatina_id)
        if not pegatina_id:
            raise BusinessLogicError("ID de pegatina inválido")

        try:
            pegatina = get_object_or_404(PegatinasIdentificativas, id=pegatina_id, activa=True)
        except Exception as e:
            raise BusinessLogicError("Pegatina no encontrada")

        # Marcar como impresa
        try:
            pegatina.marcar_como_impresa()

            log_user_action(request.user, "PEGATINA_MARCADA_IMPRESA",
                           f"Pegatina ID: {pegatina.id} - Producto: {pegatina.producto.numero_serie}")

            if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Pegatina marcada como impresa correctamente'
                })
            else:
                messages.success(request, 'Pegatina marcada como impresa correctamente.')
                return redirect('productos:ver_pegatinas', producto_id=pegatina.producto.id)

        except Exception as e:
            raise BusinessLogicError(f"Error al marcar pegatina como impresa: {str(e)}")

    except Exception as e:
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        messages.error(request, f"Error: {str(e)}")
        return redirect('productos:lista_productos')


@login_required
@handle_errors(ajax_response=True)
def eliminar_pegatina(request, pegatina_id):
    """Vista para eliminar una pegatina"""
    try:
        if request.method != 'POST':
            raise BusinessLogicError("Método no permitido")

        # Validar ID de la pegatina
        pegatina_id = safe_int_conversion(pegatina_id)
        if not pegatina_id:
            raise BusinessLogicError("ID de pegatina inválido")

        try:
            pegatina = get_object_or_404(PegatinasIdentificativas, id=pegatina_id, activa=True)
        except Exception as e:
            raise BusinessLogicError("Pegatina no encontrada")

        # Guardar info para el log antes de eliminar
        producto_numero_serie = pegatina.producto.numero_serie
        producto_id = pegatina.producto.id

        # Eliminar pegatina (desactivar)
        try:
            pegatina.activa = False
            pegatina.save()

            # También eliminar archivo de imagen si existe
            if pegatina.imagen_pegatina:
                try:
                    pegatina.imagen_pegatina.delete(save=False)
                except:
                    pass  # Si no puede eliminar el archivo, continuar

            log_user_action(request.user, "PEGATINA_ELIMINADA",
                           f"Pegatina ID: {pegatina.id} - Producto: {producto_numero_serie}")

            if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Pegatina eliminada correctamente'
                })
            else:
                messages.success(request, 'Pegatina eliminada correctamente.')
                return redirect('productos:ver_pegatinas', producto_id=producto_id)

        except Exception as e:
            raise BusinessLogicError(f"Error al eliminar pegatina: {str(e)}")

    except Exception as e:
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        messages.error(request, f"Error: {str(e)}")
        return redirect('productos:lista_productos')
