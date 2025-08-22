#!/usr/bin/env python
"""
Script para limpiar pegatinas duplicadas o huérfanas
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventario_sistema.settings')
django.setup()

from productos.models_pegatinas import PegatinasIdentificativas
from productos.models import Producto

def limpiar_pegatinas():
    print("🧹 Iniciando limpieza de pegatinas...")

    # 1. Eliminar pegatinas de productos que ya no existen
    pegatinas_huerfanas = PegatinasIdentificativas.objects.filter(producto__isnull=True)
    count_huerfanas = pegatinas_huerfanas.count()
    if count_huerfanas > 0:
        pegatinas_huerfanas.delete()
        print(f"✅ Eliminadas {count_huerfanas} pegatinas huérfanas")

    # 2. Eliminar pegatinas de productos inactivos
    pegatinas_inactivas = PegatinasIdentificativas.objects.filter(producto__activo=False)
    count_inactivas = pegatinas_inactivas.count()
    if count_inactivas > 0:
        pegatinas_inactivas.update(activa=False)
        print(f"✅ Desactivadas {count_inactivas} pegatinas de productos inactivos")

    # 3. Mostrar estadísticas por producto
    print("\n📊 Resumen por producto:")
    productos_con_pegatinas = Producto.objects.filter(
        activo=True,
        pegatinas__activa=True
    ).distinct()

    for producto in productos_con_pegatinas:
        count_pegatinas = PegatinasIdentificativas.objects.filter(
            producto=producto,
            activa=True
        ).count()
        print(f"   {producto.numero_serie}: {count_pegatinas} pegatinas")

    # 4. Verificar integridad
    total_activas = PegatinasIdentificativas.objects.filter(activa=True).count()
    print(f"\n✅ Total de pegatinas activas: {total_activas}")
    print("🎉 Limpieza completada!")

if __name__ == "__main__":
    limpiar_pegatinas()
