#!/usr/bin/env python
"""
Script para limpiar todas las tablas de la base de datos y empezar desde cero
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventario_sistema.settings')
django.setup()

from django.db import transaction
from productos.models import Producto, DatosPersonalizados, PegatinasIdentificativas
from productos.models_pegatinas import TipoProducto
from asignaciones.models import AsignacionHistorial
from core.models import Categoria, Departamento, Marca, Proveedor, EmpleadoReceptor, Ubicacion
from django.contrib.auth.models import User

def limpiar_tablas():
    """Limpia todas las tablas del sistema manteniendo el superusuario"""

    print("🗑️  Iniciando limpieza de tablas...")

    with transaction.atomic():
        # Eliminar datos de productos y asignaciones
        print("   Eliminando asignaciones...")
        AsignacionHistorial.objects.all().delete()

        print("   Eliminando pegatinas identificativas...")
        PegatinasIdentificativas.objects.all().delete()

        print("   Eliminando datos personalizados...")
        DatosPersonalizados.objects.all().delete()

        print("   Eliminando productos...")
        Producto.objects.all().delete()

        # Eliminar datos maestros
        print("   Eliminando empleados...")
        EmpleadoReceptor.objects.all().delete()

        print("   Eliminando tipos de productos...")
        TipoProducto.objects.all().delete()

        print("   Eliminando ubicaciones...")
        Ubicacion.objects.all().delete()

        print("   Eliminando proveedores...")
        Proveedor.objects.all().delete()

        print("   Eliminando marcas...")
        Marca.objects.all().delete()

        print("   Eliminando departamentos...")
        Departamento.objects.all().delete()

        print("   Eliminando categorías...")
        Categoria.objects.all().delete()

        # Mantener solo el superusuario
        print("   Eliminando usuarios (manteniendo superusuarios)...")
        User.objects.filter(is_superuser=False).delete()

    print("✅ Limpieza completada exitosamente!")
    print(f"📊 Usuarios restantes: {User.objects.count()} (solo superusuarios)")

def crear_tipos_productos_iniciales():
    """Crea los tipos de productos iniciales con sus prefijos"""

    print("\n📋 Creando tipos de productos iniciales...")

    tipos_productos = [
        {
            'nombre': 'Móvil/Teléfono',
            'codigo_prefijo': 'MOV',
            'descripcion': 'Teléfonos móviles y smartphones',
            'campos_personalizados': {
                'imei': {'tipo': 'text', 'label': 'IMEI', 'requerido': True},
                'operadora': {'tipo': 'select', 'label': 'Operadora', 'opciones': ['Movistar', 'Vodafone', 'Orange', 'Yoigo', 'Libre']},
                'plan_datos': {'tipo': 'text', 'label': 'Plan de datos'},
                'numero_telefono': {'tipo': 'text', 'label': 'Número de teléfono'}
            }
        },
        {
            'nombre': 'Ratón',
            'codigo_prefijo': 'RAT',
            'descripcion': 'Ratones de ordenador',
            'campos_personalizados': {
                'tipo_conexion': {'tipo': 'select', 'label': 'Tipo de conexión', 'opciones': ['USB', 'Bluetooth', 'Wireless 2.4GHz']},
                'dpi': {'tipo': 'number', 'label': 'DPI máximo'},
                'botones': {'tipo': 'number', 'label': 'Número de botones'}
            }
        },
        {
            'nombre': 'Teclado',
            'codigo_prefijo': 'TEC',
            'descripcion': 'Teclados de ordenador',
            'campos_personalizados': {
                'tipo_conexion': {'tipo': 'select', 'label': 'Tipo de conexión', 'opciones': ['USB', 'Bluetooth', 'Wireless 2.4GHz']},
                'tipo_teclas': {'tipo': 'select', 'label': 'Tipo de teclas', 'opciones': ['Mecánico', 'Membrana', 'Chiclet']},
                'idioma': {'tipo': 'select', 'label': 'Idioma', 'opciones': ['Español', 'Inglés', 'Internacional']}
            }
        },
        {
            'nombre': 'Monitor',
            'codigo_prefijo': 'MON',
            'descripcion': 'Monitores y pantallas',
            'campos_personalizados': {
                'tamaño_pulgadas': {'tipo': 'number', 'label': 'Tamaño (pulgadas)'},
                'resolucion': {'tipo': 'select', 'label': 'Resolución', 'opciones': ['1920x1080', '2560x1440', '3840x2160', '1366x768']},
                'tipo_panel': {'tipo': 'select', 'label': 'Tipo de panel', 'opciones': ['IPS', 'TN', 'VA', 'OLED']}
            }
        },
        {
            'nombre': 'Ordenador Portátil',
            'codigo_prefijo': 'POR',
            'descripcion': 'Laptops y portátiles',
            'campos_personalizados': {
                'procesador': {'tipo': 'text', 'label': 'Procesador'},
                'memoria_ram': {'tipo': 'select', 'label': 'RAM', 'opciones': ['4GB', '8GB', '16GB', '32GB', '64GB']},
                'almacenamiento': {'tipo': 'text', 'label': 'Almacenamiento'},
                'tarjeta_grafica': {'tipo': 'text', 'label': 'Tarjeta gráfica'},
                'sistema_operativo': {'tipo': 'select', 'label': 'Sistema Operativo', 'opciones': ['Windows 10', 'Windows 11', 'macOS', 'Linux']}
            }
        },
        {
            'nombre': 'Ordenador Sobremesa',
            'codigo_prefijo': 'SOB',
            'descripcion': 'PCs de sobremesa y torres',
            'campos_personalizados': {
                'procesador': {'tipo': 'text', 'label': 'Procesador'},
                'memoria_ram': {'tipo': 'select', 'label': 'RAM', 'opciones': ['4GB', '8GB', 'Â16GB', '32GB', '64GB']},
                'almacenamiento': {'tipo': 'text', 'label': 'Almacenamiento'},
                'tarjeta_grafica': {'tipo': 'text', 'label': 'Tarjeta gráfica'},
                'sistema_operativo': {'tipo': 'select', 'label': 'Sistema Operativo', 'opciones': ['Windows 10', 'Windows 11', 'Linux']}
            }
        },
        {
            'nombre': 'Impresora',
            'codigo_prefijo': 'IMP',
            'descripcion': 'Impresoras y multifuncionales',
            'campos_personalizados': {
                'tipo_impresion': {'tipo': 'select', 'label': 'Tipo', 'opciones': ['Láser', 'Inyección tinta', 'Térmica']},
                'color': {'tipo': 'select', 'label': 'Color', 'opciones': ['Monocromo', 'Color']},
                'funciones': {'tipo': 'multiselect', 'label': 'Funciones', 'opciones': ['Imprimir', 'Escanear', 'Fotocopiar', 'Fax']}
            }
        },
        {
            'nombre': 'Tablet',
            'codigo_prefijo': 'TAB',
            'descripcion': 'Tablets y dispositivos táctiles',
            'campos_personalizados': {
                'tamaño_pantalla': {'tipo': 'number', 'label': 'Tamaño pantalla (pulgadas)'},
                'almacenamiento': {'tipo': 'select', 'label': 'Almacenamiento', 'opciones': ['16GB', '32GB', '64GB', '128GB', '256GB', '512GB']},
                'conectividad': {'tipo': 'multiselect', 'label': 'Conectividad', 'opciones': ['WiFi', '4G', '5G', 'Bluetooth']},
                'sistema_operativo': {'tipo': 'select', 'label': 'Sistema Operativo', 'opciones': ['Android', 'iOS', 'Windows']}
            }
        },
        {
            'nombre': 'Auriculares',
            'codigo_prefijo': 'AUR',
            'descripcion': 'Auriculares y cascos de audio',
            'campos_personalizados': {
                'tipo_conexion': {'tipo': 'select', 'label': 'Conexión', 'opciones': ['Jack 3.5mm', 'USB', 'Bluetooth', 'Wireless']},
                'tipo_auricular': {'tipo': 'select', 'label': 'Tipo', 'opciones': ['In-ear', 'On-ear', 'Over-ear']},
                'cancelacion_ruido': {'tipo': 'boolean', 'label': 'Cancelación de ruido'}
            }
        },
        {
            'nombre': 'Webcam',
            'codigo_prefijo': 'WEB',
            'descripcion': 'Cámaras web y videoconferencia',
            'campos_personalizados': {
                'resolucion': {'tipo': 'select', 'label': 'Resolución', 'opciones': ['720p', '1080p', '4K']},
                'fps': {'tipo': 'select', 'label': 'FPS', 'opciones': ['30fps', '60fps']},
                'microfono_integrado': {'tipo': 'boolean', 'label': 'Micrófono integrado'}
            }
        }
    ]

    for tipo_data in tipos_productos:
        tipo, created = TipoProducto.objects.get_or_create(
            nombre=tipo_data['nombre'],
            defaults={
                'codigo_prefijo': tipo_data['codigo_prefijo'],
                'descripcion': tipo_data['descripcion'],
                'campos_personalizados': tipo_data['campos_personalizados'],
                'ultimo_numero': 0
            }
        )
        if created:
            print(f"   ✓ Creado: {tipo.nombre} ({tipo.codigo_prefijo})")
        else:
            print(f"   - Ya existe: {tipo.nombre}")

def crear_categorias_iniciales():
    """Crea las categorías iniciales y las asocia con los tipos de productos"""

    print("\n📂 Creando categorías iniciales...")

    categorias_data = [
        {'nombre': 'Telefonía', 'codigo': 'TEL', 'descripcion': 'Dispositivos de comunicación móvil', 'tipo_producto': 'Móvil/Teléfono'},
        {'nombre': 'Periféricos', 'codigo': 'PER', 'descripcion': 'Dispositivos de entrada y salida', 'tipo_producto': None},
        {'nombre': 'Informática', 'codigo': 'INF', 'descripcion': 'Equipos informáticos y computación', 'tipo_producto': None},
        {'nombre': 'Audio y Video', 'codigo': 'AUD', 'descripcion': 'Dispositivos de audio y vídeo', 'tipo_producto': None},
        {'nombre': 'Impresión', 'codigo': 'IMP', 'descripcion': 'Equipos de impresión y escaneo', 'tipo_producto': 'Impresora'},
    ]

    for cat_data in categorias_data:
        categoria, created = Categoria.objects.get_or_create(
            nombre=cat_data['nombre'],
            defaults={
                'codigo': cat_data['codigo'],
                'descripcion': cat_data['descripcion']
            }
        )

        if created:
            print(f"   ✓ Creada: {categoria.nombre} ({categoria.codigo})")
        else:
            print(f"   - Ya existe: {categoria.nombre}")

        # Asociar con tipo de producto si se especifica
        if cat_data['tipo_producto']:
            try:
                tipo_producto = TipoProducto.objects.get(nombre=cat_data['tipo_producto'])
                tipo_producto.categorias.add(categoria)
                print(f"     → Asociada con tipo: {tipo_producto.nombre}")
            except TipoProducto.DoesNotExist:
                pass

def asociar_categorias_con_tipos():
    """Asocia las categorías restantes con sus tipos de productos correspondientes"""

    print("\n🔗 Asociando categorías con tipos de productos...")

    # Obtener categorías
    cat_perifericos = Categoria.objects.get(codigo='PER')
    cat_informatica = Categoria.objects.get(codigo='INF')
    cat_audio = Categoria.objects.get(codigo='AUD')

    # Asociaciones
    asociaciones = [
        # Periféricos
        ('Ratón', cat_perifericos),
        ('Teclado', cat_perifericos),
        ('Monitor', cat_perifericos),
        ('Webcam', cat_perifericos),

        # Informática
        ('Ordenador Portátil', cat_informatica),
        ('Ordenador Sobremesa', cat_informatica),
        ('Tablet', cat_informatica),

        # Audio
        ('Auriculares', cat_audio),
    ]

    for tipo_nombre, categoria in asociaciones:
        try:
            tipo_producto = TipoProducto.objects.get(nombre=tipo_nombre)
            tipo_producto.categorias.add(categoria)
            print(f"   ✓ {tipo_nombre} → {categoria.nombre}")
        except TipoProducto.DoesNotExist:
            print(f"   ✗ No encontrado: {tipo_nombre}")

if __name__ == '__main__':
    print("🚀 SCRIPT DE INICIALIZACIÓN DEL SISTEMA DE INVENTARIO")
    print("=" * 60)

    # Limpiar tablas
    limpiar_tablas()

    # Crear datos iniciales
    crear_tipos_productos_iniciales()
    crear_categorias_iniciales()
    asociar_categorias_con_tipos()

    print("\n" + "=" * 60)
    print("✅ INICIALIZACIÓN COMPLETADA")
    print("\nResumen:")
    print(f"📋 Tipos de productos: {TipoProducto.objects.count()}")
    print(f"📂 Categorías: {Categoria.objects.count()}")
    print(f"👥 Usuarios: {User.objects.count()}")
    print("\n🎯 El sistema está listo para agregar productos con numeración automática!")
