from django.urls import path
from . import views

app_name = 'productos'

urlpatterns = [
    path('', views.lista_productos, name='lista_productos'),
    path('agregar/', views.agregar_producto, name='agregar_producto'),
    path('editar/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    path('detalle/<int:producto_id>/', views.detalle_producto, name='detalle_producto'),

    # URLs para el sistema de pegatinas identificativas
    path('detectar-tipo/', views.detectar_tipo_producto, name='detectar_tipo_producto'),
    path('<int:producto_id>/datos-personalizados/', views.gestionar_datos_personalizados, name='gestionar_datos_personalizados'),
    path('<int:producto_id>/generar-pegatinas/', views.generar_pegatinas, name='generar_pegatinas'),
    path('<int:producto_id>/pegatinas/', views.ver_pegatinas, name='ver_pegatinas'),
    path('pegatina/<int:pegatina_id>/imprimir/', views.imprimir_pegatina, name='imprimir_pegatina'),
    path('pegatina/<int:pegatina_id>/descargar/', views.descargar_pegatina, name='descargar_pegatina'),
    path('pegatina/<int:pegatina_id>/marcar-impresa/', views.marcar_pegatina_impresa, name='marcar_pegatina_impresa'),
    path('pegatina/<int:pegatina_id>/eliminar/', views.eliminar_pegatina, name='eliminar_pegatina'),

    # AJAX URLs
    path('ajax/campos-categoria/', views.obtener_campos_categoria, name='obtener_campos_categoria'),
    path('eliminar/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
]
