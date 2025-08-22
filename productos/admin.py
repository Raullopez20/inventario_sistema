from django.contrib import admin
from django.utils.html import format_html
from .models import Producto


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('id_interno', 'categoria', 'marca', 'modelo', 'estado', 'condicion', 'en_garantia_display', 'fecha_compra', 'precio_compra')
    list_filter = ('categoria', 'marca', 'estado', 'condicion', 'fecha_compra', 'activo')
    search_fields = ('id_interno', 'numero_serie', 'modelo', 'marca__nombre')
    ordering = ('-created_at',)
    date_hierarchy = 'fecha_compra'

    fieldsets = (
        ('Información Básica', {
            'fields': ('categoria', 'marca', 'modelo', 'numero_serie')
        }),
        ('Estado y Condición', {
            'fields': ('estado', 'condicion', 'activo')
        }),
        ('Información de Compra', {
            'fields': ('proveedor', 'fecha_compra', 'precio_compra', 'factura_numero')
        }),
        ('Garantía', {
            'fields': ('fecha_fin_garantia',)
        }),
        ('Ubicación', {
            'fields': ('ubicacion_actual',)
        }),
        ('Especificaciones Técnicas', {
            'fields': ('especificaciones',),
            'classes': ('collapse',)
        }),
        ('Código QR', {
            'fields': ('codigo_qr',),
            'classes': ('collapse',)
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        })
    )

    readonly_fields = ('id_interno', 'codigo_qr')

    def en_garantia_display(self, obj):
        if obj.en_garantia:
            return format_html('<span style="color: green;">✓ En garantía</span>')
        else:
            return format_html('<span style="color: red;">✗ Sin garantía</span>')
    en_garantia_display.short_description = 'Garantía'
