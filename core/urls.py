from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('inventario/categoria/', views.inventario_por_categoria, name='inventario_categoria'),
    path('inventario/categoria/<int:categoria_id>/', views.inventario_por_categoria, name='inventario_categoria_filtro'),
    path('inventario/departamento/', views.inventario_por_departamento, name='inventario_departamento'),
    path('inventario/departamento/<int:departamento_id>/', views.inventario_por_departamento, name='inventario_departamento_filtro'),
    # Panel de administración personalizado
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/categorias/', views.gestionar_categorias, name='gestionar_categorias'),
    path('admin-panel/categorias/eliminar/<int:categoria_id>/', views.eliminar_categoria, name='eliminar_categoria'),
    path('admin-panel/departamentos/', views.gestionar_departamentos, name='gestionar_departamentos'),
    path('admin-panel/marcas/', views.gestionar_marcas, name='gestionar_marcas'),
    path('admin-panel/empleados/', views.gestionar_empleados, name='gestionar_empleados'),
    path('admin-panel/proveedores/', views.gestionar_proveedores, name='gestionar_proveedores'),
    path('admin-panel/ubicaciones/', views.gestionar_ubicaciones, name='gestionar_ubicaciones'),
    path('admin-panel/ubicaciones/eliminar/<int:ubicacion_id>/', views.eliminar_ubicacion, name='eliminar_ubicacion'),

    # Herramientas del sistema
    path('admin-panel/herramientas/backup/', views.generar_backup, name='generar_backup'),
    path('admin-panel/herramientas/exportar/', views.exportar_datos, name='exportar_datos'),
    path('admin-panel/herramientas/limpiar-cache/', views.limpiar_cache, name='limpiar_cache'),
    path('admin-panel/herramientas/reporte/', views.generar_reporte_inventario, name='generar_reporte_inventario'),
]
