"""
WSGI config optimizado para servidor IIS con FastCGI
Soluciona el problema de populate() isn't reentrant
"""

import os
import sys
import django
from django.core.wsgi import get_wsgi_application

# Asegurar que el directorio del proyecto esté en Python path
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# Configurar variables de entorno
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventario_sistema.settings')

# Variable global para la aplicación
_application = None

def get_wsgi_app():
    """Obtiene la aplicación WSGI de forma thread-safe"""
    global _application
    if _application is None:
        try:
            # Verificar si Django ya está configurado
            if not django.apps.apps.ready:
                django.setup()
            _application = get_wsgi_application()
        except RuntimeError as e:
            if "populate() isn't reentrant" in str(e):
                # Django ya está configurado, obtener la aplicación directamente
                from django.core.handlers.wsgi import WSGIHandler
                _application = WSGIHandler()
            else:
                raise e
        except Exception as e:
            # Log del error y re-lanzar
            import logging
            logging.error(f"Error inicializando Django WSGI: {e}")
            raise e

    return _application

# Crear la aplicación
application = get_wsgi_app()
