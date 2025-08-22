from django.contrib import admin
from django.utils.html import format_html
from .models import AsignacionHistorial, MovimientoStock


@admin.register(AsignacionHistorial)
class AsignacionHistorialAdmin(admin.ModelAdmin):
    list_display = ('producto', 'empleado_receptor', 'departamento', 'tipo_asignacion', 'fecha_entrega', 'estado_asignacion', 'dias_en_posesion')
    list_filter = ('tipo_asignacion', 'departamento', 'fecha_entrega', 'confirmado_empleado')
    search_fields = ('producto__id_interno', 'empleado_receptor__nombre', 'departamento__nombre')
    ordering = ('-fecha_entrega',)
    date_hierarchy = 'fecha_entrega'

    fieldsets = (
        ('Información de Asignación', {
            'fields': ('producto', 'empleado_receptor', 'departamento', 'tipo_asignacion')
        }),
        ('Fechas', {
            'fields': ('fecha_entrega', 'fecha_devolucion', 'fecha_prevista_devolucion')
        }),
        ('Estado del Producto', {
            'fields': ('estado_producto_entrega', 'estado_producto_devolucion')
        }),
        ('Usuarios', {
            'fields': ('usuario_entrega', 'usuario_devolucion')
        }),
        ('Devolución', {
            'fields': ('motivo_devolucion', 'observaciones_devolucion'),
            'classes': ('collapse',)
        }),
        ('Observaciones y Documentos', {
            'fields': ('observaciones_entrega', 'documento_entrega', 'documento_devolucion'),
            'classes': ('collapse',)
        }),
        ('Confirmación', {
            'fields': ('confirmado_empleado', 'fecha_confirmacion_empleado'),
            'classes': ('collapse',)
        })
    )

    readonly_fields = ('dias_en_posesion',)

    def estado_asignacion(self, obj):
        if obj.fecha_devolucion:
            return format_html('<span style="color: blue;">✓ Devuelto</span>')
        elif obj.prestamo_vencido:
            return format_html('<span style="color: red;">⚠ Préstamo vencido</span>')
        else:
            return format_html('<span style="color: orange;">→ Pendiente</span>')
    estado_asignacion.short_description = 'Estado'


@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ('producto', 'tipo_movimiento', 'usuario', 'created_at', 'descripcion_corta')
    list_filter = ('tipo_movimiento', 'created_at', 'usuario')
    search_fields = ('producto__id_interno', 'descripcion')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    def descripcion_corta(self, obj):
        return obj.descripcion[:50] + "..." if len(obj.descripcion) > 50 else obj.descripcion
    descripcion_corta.short_description = 'Descripción'
