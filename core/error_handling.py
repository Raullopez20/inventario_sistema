import logging
import traceback
from functools import wraps
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import DatabaseError, IntegrityError, OperationalError
from django.core.exceptions import ValidationError, PermissionDenied, ObjectDoesNotExist
from django.views.defaults import server_error
import json

# Configurar logger
logger = logging.getLogger(__name__)

class ErrorTypes:
    """Tipos de errores del sistema"""
    DATABASE = "DATABASE_ERROR"
    VALIDATION = "VALIDATION_ERROR"
    PERMISSION = "PERMISSION_ERROR"
    NOT_FOUND = "NOT_FOUND_ERROR"
    BUSINESS_LOGIC = "BUSINESS_LOGIC_ERROR"
    EXTERNAL_SERVICE = "EXTERNAL_SERVICE_ERROR"
    FILE_OPERATION = "FILE_OPERATION_ERROR"
    NETWORK = "NETWORK_ERROR"
    UNKNOWN = "UNKNOWN_ERROR"

class SystemError:
    """Clase para manejar errores del sistema"""

    @staticmethod
    def get_error_details(exception):
        """Analiza la excepción y devuelve detalles estructurados"""
        error_type = ErrorTypes.UNKNOWN
        user_message = "Ha ocurrido un error inesperado"
        technical_message = str(exception)

        # Errores de base de datos
        if isinstance(exception, (DatabaseError, OperationalError)):
            error_type = ErrorTypes.DATABASE
            user_message = "Error de conexión con la base de datos"
            if "database is locked" in str(exception).lower():
                user_message = "La base de datos está temporalmente bloqueada. Intente nuevamente en unos segundos."
            elif "no such table" in str(exception).lower():
                user_message = "Error de configuración de la base de datos. Contacte al administrador."
            elif "duplicate" in str(exception).lower():
                user_message = "Ya existe un registro con esos datos."

        elif isinstance(exception, IntegrityError):
            error_type = ErrorTypes.DATABASE
            user_message = "Error de integridad de datos"
            if "UNIQUE constraint failed" in str(exception):
                user_message = "Ya existe un registro con esos datos únicos."
            elif "FOREIGN KEY constraint failed" in str(exception):
                user_message = "No se puede realizar la operación debido a referencias de datos."

        # Errores de validación
        elif isinstance(exception, ValidationError):
            error_type = ErrorTypes.VALIDATION
            user_message = "Datos inválidos proporcionados"
            if hasattr(exception, 'message_dict'):
                user_message = "Errores de validación en los campos: " + ", ".join(exception.message_dict.keys())
            elif hasattr(exception, 'messages'):
                user_message = "; ".join(exception.messages)

        # Errores de permisos
        elif isinstance(exception, PermissionDenied):
            error_type = ErrorTypes.PERMISSION
            user_message = "No tiene permisos para realizar esta acción"

        # Errores de objeto no encontrado
        elif isinstance(exception, ObjectDoesNotExist):
            error_type = ErrorTypes.NOT_FOUND
            user_message = "El elemento solicitado no existe o fue eliminado"

        # Errores de archivo
        elif isinstance(exception, (FileNotFoundError, PermissionError, OSError)):
            error_type = ErrorTypes.FILE_OPERATION
            if isinstance(exception, FileNotFoundError):
                user_message = "Archivo no encontrado"
            elif isinstance(exception, PermissionError):
                user_message = "Sin permisos para acceder al archivo"
            else:
                user_message = "Error al procesar archivos"

        # Errores de importación/exportación
        elif "import" in str(exception).lower() or "export" in str(exception).lower():
            error_type = ErrorTypes.EXTERNAL_SERVICE
            user_message = "Error en el procesamiento de datos externos"

        # Errores de valor
        elif isinstance(exception, ValueError):
            error_type = ErrorTypes.VALIDATION
            user_message = "Valor inválido proporcionado"

        # Errores de tipo
        elif isinstance(exception, TypeError):
            error_type = ErrorTypes.BUSINESS_LOGIC
            user_message = "Error en el procesamiento de datos"

        return {
            'type': error_type,
            'user_message': user_message,
            'technical_message': technical_message,
            'exception_type': type(exception).__name__
        }

def handle_errors(ajax_response=False, redirect_on_error=None):
    """
    Decorador para manejar errores en vistas

    Args:
        ajax_response: Si True, devuelve respuesta JSON para peticiones AJAX
        redirect_on_error: URL a la que redirigir en caso de error
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            try:
                return view_func(request, *args, **kwargs)
            except Exception as e:
                # Log del error
                logger.error(f"Error en vista {view_func.__name__}: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")

                # Obtener detalles del error
                error_details = SystemError.get_error_details(e)

                # Si es una petición AJAX o se solicita respuesta JSON
                # ¡IMPORTANTE! Compatibilidad Django 2.1: nunca usar request.headers
                if ajax_response or request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': True,
                        'error_type': error_details['type'],
                        'message': error_details['user_message'],
                        'technical_details': error_details['technical_message'] if request.user.is_staff else None
                    }, status=500)

                # Para peticiones normales
                messages.error(request, error_details['user_message'])

                # Si se especifica redirección
                if redirect_on_error:
                    return redirect(redirect_on_error)

                # Renderizar página de error personalizada
                return render(request, 'core/error_page.html', {
                    'error_details': error_details,
                    'show_technical': request.user.is_staff
                }, status=500)

        return wrapper
    return decorator

def validate_data(data, required_fields=None, validators=None):
    """
    Valida datos de entrada

    Args:
        data: Diccionario con los datos a validar
        required_fields: Lista de campos requeridos
        validators: Diccionario con validadores personalizados
    """
    errors = {}

    # Validar campos requeridos
    if required_fields:
        for field in required_fields:
            if field not in data or not data[field]:
                errors[field] = f"El campo {field} es requerido"

    # Validadores personalizados
    if validators:
        for field, validator in validators.items():
            if field in data:
                try:
                    validator(data[field])
                except ValidationError as e:
                    errors[field] = str(e)

    if errors:
        raise ValidationError(errors)

    return True

class BusinessLogicError(Exception):
    """Excepción personalizada para errores de lógica de negocio"""
    pass

def log_user_action(user, action, details=None):
    """Registra acciones del usuario para auditoría"""
    try:
        logger.info(f"Usuario {user.username} - Acción: {action} - Detalles: {details}")
    except Exception as e:
        logger.error(f"Error al registrar acción del usuario: {str(e)}")

def safe_int_conversion(value, default=0):
    """Conversión segura a entero"""
    try:
        return int(value) if value else default
    except (ValueError, TypeError):
        return default

def safe_float_conversion(value, default=0.0):
    """Conversión segura a float"""
    try:
        return float(value) if value else default
    except (ValueError, TypeError):
        return default

def validate_file_upload(file, allowed_extensions=None, max_size_mb=10):
    """Valida archivos subidos"""
    if not file:
        raise ValidationError("No se ha proporcionado ningún archivo")

    # Validar extensión
    if allowed_extensions:
        file_extension = file.name.split('.')[-1].lower()
        if file_extension not in allowed_extensions:
            raise ValidationError(f"Extensión de archivo no permitida. Permitidas: {', '.join(allowed_extensions)}")

    # Validar tamaño
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"El archivo es demasiado grande. Máximo permitido: {max_size_mb}MB")

    return True
