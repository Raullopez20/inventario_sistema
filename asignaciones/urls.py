from django.urls import path
from . import views

app_name = 'asignaciones'

urlpatterns = [
    # URLs principales
    path('', views.lista_asignaciones, name='lista_asignaciones'),
    path('agregar/', views.agregar_asignacion, name='agregar_asignacion'),
    path('detalle/<int:asignacion_id>/', views.detalle_asignacion, name='detalle_asignacion'),
    path('movimientos-stock/', views.movimientos_stock, name='movimientos_stock'),

    # URLs de acciones
    path('devolver/<int:asignacion_id>/', views.devolver_producto, name='devolver_producto'),
    path('confirmar/<int:asignacion_id>/', views.confirmar_asignacion, name='confirmar_asignacion'),

    # URLs AJAX
    path('ajax/empleados-departamento/<int:departamento_id>/', views.get_empleados_departamento, name='get_empleados_departamento'),

    # Nueva URL para enviar recordatorio
    path('enviar-recordatorio/', views.enviar_recordatorio, name='enviar_recordatorio'),

    # URL para la descarga de reporte PDF real
    path('reporte/<int:asignacion_id>/', views.generar_reporte_asignacion, name='generar_reporte_asignacion'),
]
