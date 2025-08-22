"""
WSGI config for inventario_sistema project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import django
from django.core.wsgi import get_wsgi_application

# Configurar las variables de entorno
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventario_sistema.settings')

# Variable global para almacenar la aplicación
_application = None

def get_django_application():
    """Función para obtener la aplicación Django de forma segura."""
    global _application
    if _application is None:
        try:
            django.setup()
            _application = get_wsgi_application()
        except RuntimeError as e:
            if "populate() isn't reentrant" in str(e):
                # Si Django ya está configurado, crear una nueva instancia
                from django.core.handlers.wsgi import WSGIHandler
                _application = WSGIHandler()
            else:
                raise
    return _application

# Crear la aplicación
application = get_django_application()
