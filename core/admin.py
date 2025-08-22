
from django.contrib import admin
from .models import Categoria, Marca, Proveedor, Departamento, EmpleadoReceptor, Ubicacion


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'activo', 'created_at')
    list_filter = ('activo', 'created_at')
    search_fields = ('nombre', 'codigo')
    ordering = ('nombre',)


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'created_at')
    list_filter = ('activo', 'created_at')
    search_fields = ('nombre',)
    ordering = ('nombre',)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nif_cif', 'telefono', 'email', 'activo')
    list_filter = ('activo', 'created_at')
    search_fields = ('nombre', 'nif_cif', 'email')
    ordering = ('nombre',)


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'responsable', 'activo')
    list_filter = ('activo', 'created_at')
    search_fields = ('nombre', 'codigo')
    ordering = ('nombre',)


@admin.register(EmpleadoReceptor)
class EmpleadoReceptorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'dni', 'departamento', 'puesto', 'activo')
    list_filter = ('departamento', 'activo', 'fecha_alta')
    search_fields = ('nombre', 'dni', 'email')
    ordering = ('nombre',)
    date_hierarchy = 'fecha_alta'


@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'edificio', 'planta', 'sala', 'activo')
    list_filter = ('edificio', 'activo', 'created_at')
    search_fields = ('nombre', 'edificio', 'sala')
    ordering = ('edificio', 'planta', 'sala')
