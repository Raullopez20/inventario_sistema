from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from core.models import TimeStampedModel, Categoria, Marca, Proveedor, Ubicacion
from .models_pegatinas import TipoProducto, DatosPersonalizados, PegatinasIdentificativas
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
import json


class Producto(TimeStampedModel):
    """Modelo principal para todos los productos del inventario"""

    # Estados posibles del producto
    ESTADOS = [
        ('DISPONIBLE', 'Disponible'),
        ('ENTREGADO', 'Entregado'),
        ('AVERIADO', 'Averiado'),
        ('ROTO', 'Roto/Sin reparación'),
        ('RECOGIDO', 'Recogido'),
        ('BAJA', 'Dado de baja'),
    ]

    CONDICIONES = [
        ('NUEVO', 'Nuevo'),
        ('USADO_BUENO', 'Usado - Buen estado'),
        ('USADO_REGULAR', 'Usado - Estado regular'),
        ('AVERIADO', 'Averiado'),
        ('OBSOLETO', 'Obsoleto'),
    ]

    # Campos básicos
    id_interno = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="ID Interno",
        help_text="Código único del producto generado automáticamente"
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        verbose_name="Categoría"
    )
    marca = models.ForeignKey(
        Marca,
        on_delete=models.CASCADE,
        verbose_name="Marca"
    )
    modelo = models.CharField(max_length=100, verbose_name="Modelo")

    # Imagen del producto
    imagen = models.ImageField(
        upload_to='productos/',
        blank=True,
        null=True,
        verbose_name="Imagen del producto",
        help_text="Imagen principal del producto"
    )

    # Información de identificación
    numero_serie = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Número de serie"
    )
    codigo_barras = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Código de barras"
    )

    # Estado y condición
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='DISPONIBLE',
        verbose_name="Estado actual"
    )
    condicion = models.CharField(
        max_length=20,
        choices=CONDICIONES,
        default='NUEVO',
        verbose_name="Condición física"
    )

    # Información de compra
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Proveedor"
    )
    fecha_compra = models.DateField(
        verbose_name="Fecha de compra",
        help_text="Fecha en que se adquirió el producto"
    )
    precio_compra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Precio de compra (€)"
    )
    factura_numero = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Número de factura"
    )

    # Garantía
    fecha_fin_garantia = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha fin de garantía"
    )

    # Ubicación física
    ubicacion_actual = models.ForeignKey(
        Ubicacion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Ubicación actual"
    )

    # Especificaciones técnicas (JSON flexible para cada categoría)
    _especificaciones = models.TextField(
        default='{}',
        blank=True,
        null=True,
        verbose_name="Especificaciones técnicas",
        help_text="Especificaciones específicas según la categoría del producto"
    )

    @property
    def especificaciones(self):
        """Getter para especificaciones - devuelve un diccionario"""
        try:
            return json.loads(self._especificaciones) if self._especificaciones else {}
        except json.JSONDecodeError:
            return {}

    @especificaciones.setter
    def especificaciones(self, value):
        """Setter para especificaciones - acepta un diccionario"""
        self._especificaciones = json.dumps(value) if value else '{}'

    # Código QR para identificación rápida
    codigo_qr = models.ImageField(
        upload_to='codigos_qr/',
        blank=True,
        null=True,
        verbose_name="Código QR"
    )

    # Observaciones y notas
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones",
        help_text="Notas adicionales sobre el producto"
    )

    # Control de activo
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['numero_serie']),
            models.Index(fields=['estado']),
            models.Index(fields=['categoria']),
        ]

    def save(self, *args, **kwargs):
        # Generar ID interno si no existe
        if not self.id_interno:
            self.id_interno = self.generar_id_interno()

        # Generar número de serie si no existe
        if not self.numero_serie:
            self.numero_serie = self.generar_numero_serie_automatico()

        # Llamar al save original
        super().save(*args, **kwargs)

    def generar_id_interno(self):
        """Genera un ID interno único para el producto"""
        import random
        import string

        # Generar un ID basado en categoría + número aleatorio
        if self.categoria:
            prefijo = self.categoria.codigo[:3].upper() if hasattr(self.categoria, 'codigo') else 'PRD'
        else:
            prefijo = 'PRD'

        # Generar número único
        while True:
            numero = ''.join(random.choices(string.digits, k=4))
            id_interno = f"{prefijo}{numero}"

            if not Producto.objects.filter(id_interno=id_interno).exists():
                return id_interno

    def generar_numero_serie_automatico(self):
        """Genera un número de serie automático único"""
        import random
        import string
        from datetime import datetime

        # Generar número de serie basado en año + categoría + número aleatorio
        año = datetime.now().year
        if self.categoria:
            cat_codigo = self.categoria.codigo[:3].upper() if hasattr(self.categoria, 'codigo') else 'CAT'
        else:
            cat_codigo = 'GEN'

        # Generar número único
        while True:
            numero = ''.join(random.choices(string.digits, k=4))
            numero_serie = f"{año}{cat_codigo}{numero}"

            if not Producto.objects.filter(numero_serie=numero_serie).exists():
                return numero_serie

    def generar_codigo_qr(self):
        """Genera un código QR para el producto (método simplificado)"""
        try:
            import qrcode
            from io import BytesIO
            from django.core.files import File

            # Datos para el QR
            qr_data = f"{self.numero_serie}|{self.marca.nombre if self.marca else 'Sin marca'}|{self.modelo}"

            # Crear QR
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_data)
            qr.make(fit=True)

            # Generar imagen
            qr_img = qr.make_image(fill_color="black", back_color="white")

            # Guardar en campo
            buffer = BytesIO()
            qr_img.save(buffer, format='PNG')
            buffer.seek(0)

            filename = f'qr_{self.numero_serie}.png'
            self.codigo_qr.save(filename, File(buffer), save=False)

        except Exception as e:
            # Si falla la generación del QR, no interrumpir el guardado
            print(f"Error generando QR: {e}")
            pass

