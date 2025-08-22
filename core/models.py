from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
import uuid
import json


class TimeStampedModel(models.Model):
    """Modelo base con timestamps automáticos"""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última modificación")

    class Meta:
        abstract = True


class Categoria(TimeStampedModel):
    """Categorías de productos: PCs, Ratones, Teclados, etc."""
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de categoría")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    codigo = models.CharField(max_length=10, unique=True, verbose_name="Código de categoría")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    usuario_creacion = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuario de creación")

    # Campos específicos que pueden tener los productos de esta categoría
    _campos_especificos = models.TextField(
        default='{}',
        blank=True,
        help_text="Campos específicos para esta categoría en formato JSON",
        verbose_name="Campos específicos"
    )

    @property
    def campos_especificos(self):
        """Getter para campos_especificos - devuelve un diccionario"""
        try:
            return json.loads(self._campos_especificos) if self._campos_especificos else {}
        except json.JSONDecodeError:
            return {}

    @campos_especificos.setter
    def campos_especificos(self, value):
        """Setter para campos_especificos - acepta un diccionario"""
        self._campos_especificos = json.dumps(value) if value else '{}'

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Marca(TimeStampedModel):
    """Marcas de productos"""
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de marca")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Proveedor(TimeStampedModel):
    """Proveedores de productos"""
    nombre = models.CharField(max_length=150, verbose_name="Nombre del proveedor")
    nif_cif = models.CharField(max_length=20, unique=True, verbose_name="NIF/CIF")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Departamento(TimeStampedModel):
    """Departamentos de la empresa"""
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del departamento")
    codigo = models.CharField(max_length=10, unique=True, verbose_name="Código")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    usuario_creacion = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="departamentos_creados", verbose_name="Usuario de creación")
    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="departamentos_responsable",
        verbose_name="Responsable"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class EmpleadoReceptor(TimeStampedModel):
    """Empleados que pueden recibir productos"""
    nombre = models.CharField(max_length=100, verbose_name="Nombre completo")
    dni = models.CharField(
        max_length=10,
        unique=True,
        validators=[RegexValidator(r'^\d{8}[A-Z]$', 'Formato DNI inválido')],
        verbose_name="DNI"
    )
    email = models.EmailField(unique=True, verbose_name="Email corporativo")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.CASCADE,
        verbose_name="Departamento"
    )
    puesto = models.CharField(max_length=100, blank=True, null=True, verbose_name="Puesto de trabajo")
    activo = models.BooleanField(default=True, verbose_name="Empleado activo")
    fecha_alta = models.DateField(verbose_name="Fecha de alta")
    fecha_baja = models.DateField(blank=True, null=True, verbose_name="Fecha de baja")

    class Meta:
        verbose_name = "Empleado Receptor"
        verbose_name_plural = "Empleados Receptores"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} - {self.departamento.nombre}"


class Ubicacion(TimeStampedModel):
    """Ubicaciones físicas donde pueden estar los productos"""
    nombre = models.CharField(max_length=100, verbose_name="Nombre de ubicación")
    edificio = models.CharField(max_length=50, blank=True, null=True, verbose_name="Edificio")
    planta = models.CharField(max_length=20, blank=True, null=True, verbose_name="Planta")
    sala = models.CharField(max_length=50, blank=True, null=True, verbose_name="Sala/Oficina")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Ubicación"
        verbose_name_plural = "Ubicaciones"
        ordering = ['edificio', 'planta', 'sala']

    def __str__(self):
        ubicacion = self.nombre
        if self.edificio:
            ubicacion += f" - {self.edificio}"
        if self.planta:
            ubicacion += f" (Planta {self.planta})"
        return ubicacion
