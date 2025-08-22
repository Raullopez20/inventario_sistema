from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from core.models import TimeStampedModel, Categoria, Marca, Proveedor, Ubicacion
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
import json
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter


class TipoProducto(TimeStampedModel):
    """Configuración de tipos de productos con campos personalizados"""

    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del tipo")
    codigo_prefijo = models.CharField(
        max_length=10,
        unique=True,
        verbose_name="Prefijo del código",
        help_text="Prefijo para generar números de serie (ej: MV, ORD, TAB)"
    )
    descripcion = models.TextField(blank=True, verbose_name="Descripción")

    # Configuración de campos personalizados
    _campos_personalizados = models.TextField(
        default='{}',
        verbose_name="Campos personalizados",
        help_text="Configuración de campos específicos para este tipo de producto"
    )

    # Configuración de numeración automática
    ultimo_numero = models.IntegerField(
        default=0,
        verbose_name="Último número generado"
    )

    # Categorías asociadas a este tipo
    categorias = models.ManyToManyField(
        Categoria,
        blank=True,
        verbose_name="Categorías asociadas",
        help_text="Categorías que detectan automáticamente este tipo de producto"
    )

    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Tipo de Producto"
        verbose_name_plural = "Tipos de Productos"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def generar_numero_serie(self):
        """Genera el siguiente número de serie para este tipo de producto"""
        self.ultimo_numero += 1
        self.save()
        return f"{self.codigo_prefijo}{self.ultimo_numero:04d}"

    @property
    def campos_personalizados(self):
        """Getter para campos_personalizados - devuelve un diccionario"""
        try:
            return json.loads(self._campos_personalizados) if self._campos_personalizados else {}
        except json.JSONDecodeError:
            return {}

    @campos_personalizados.setter
    def campos_personalizados(self, value):
        """Setter para campos_personalizados - acepta un diccionario"""
        self._campos_personalizados = json.dumps(value) if value else '{}'

    @classmethod
    def detectar_tipo_por_categoria(cls, categoria):
        """Detecta el tipo de producto basado en la categoría"""
        tipo = cls.objects.filter(categorias=categoria, activo=True).first()
        return tipo


class DatosPersonalizados(TimeStampedModel):
    """Almacena los datos personalizados de cada producto"""

    producto = models.OneToOneField(
        'Producto',
        on_delete=models.CASCADE,
        related_name='datos_personalizados',
        verbose_name="Producto"
    )

    tipo_producto = models.ForeignKey(
        TipoProducto,
        on_delete=models.CASCADE,
        verbose_name="Tipo de producto"
    )

    _datos = models.TextField(
        default='{}',
        verbose_name="Datos personalizados",
        help_text="Valores de los campos personalizados"
    )

    class Meta:
        verbose_name = "Datos Personalizados"
        verbose_name_plural = "Datos Personalizados"

    def __str__(self):
        return f"Datos de {self.producto.numero_serie}"

    @property
    def datos(self):
        """Getter para datos - devuelve un diccionario"""
        try:
            return json.loads(self._datos) if self._datos else {}
        except json.JSONDecodeError:
            return {}

    @datos.setter
    def datos(self, value):
        """Setter para datos - acepta un diccionario"""
        self._datos = json.dumps(value) if value else '{}'


class PegatinasIdentificativas(TimeStampedModel):
    """Gestiona las pegatinas identificativas de los productos"""

    TIPOS_PEGATINA = [
        ('QR', 'Código QR'),
        ('CODIGO_BARRAS', 'Código de barras'),
        ('ETIQUETA_SIMPLE', 'Etiqueta simple'),
        ('ETIQUETA_COMPLETA', 'Etiqueta completa'),
    ]

    producto = models.ForeignKey(
        'Producto',
        on_delete=models.CASCADE,
        related_name='pegatinas',
        verbose_name="Producto"
    )

    tipo_pegatina = models.CharField(
        max_length=20,
        choices=TIPOS_PEGATINA,
        verbose_name="Tipo de pegatina"
    )

    codigo_generado = models.CharField(
        max_length=200,
        verbose_name="Código generado"
    )

    imagen_pegatina = models.ImageField(
        upload_to='pegatinas/',
        blank=True,
        null=True,
        verbose_name="Imagen de la pegatina"
    )

    fecha_generacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de generación"
    )

    impresa = models.BooleanField(
        default=False,
        verbose_name="Impresa"
    )

    fecha_impresion = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de impresión"
    )

    activa = models.BooleanField(default=True, verbose_name="Activa")

    class Meta:
        verbose_name = "Pegatina Identificativa"
        verbose_name_plural = "Pegatinas Identificativas"
        ordering = ['-fecha_generacion']

    def __str__(self):
        return f"Pegatina {self.get_tipo_pegatina_display()} - {self.producto.numero_serie}"

    def marcar_como_impresa(self):
        """Marca la pegatina como impresa"""
        self.impresa = True
        self.fecha_impresion = timezone.now()
        self.save()

    def generar_pegatina(self):
        """Genera la imagen de la pegatina según el tipo"""
        if self.tipo_pegatina == 'QR':
            return self._generar_qr()
        elif self.tipo_pegatina == 'CODIGO_BARRAS':
            return self._generar_codigo_barras()
        elif self.tipo_pegatina == 'ETIQUETA_SIMPLE':
            return self._generar_etiqueta_simple()
        elif self.tipo_pegatina == 'ETIQUETA_COMPLETA':
            return self._generar_etiqueta_completa()

    def _generar_qr(self):
        """Genera un código QR con información del producto"""
        qr_data = {
            'numero_serie': self.producto.numero_serie,
            'tipo': self.producto.datos_personalizados.tipo_producto.nombre if hasattr(self.producto, 'datos_personalizados') else '',
            'categoria': self.producto.categoria.nombre,
            'marca': self.producto.marca.nombre,
            'modelo': self.producto.modelo,
        }

        # Añadir datos personalizados si existen
        if hasattr(self.producto, 'datos_personalizados'):
            qr_data.update(self.producto.datos_personalizados.datos)

        qr_string = json.dumps(qr_data, ensure_ascii=False)

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_string)
        qr.make(fit=True)

        qr_image = qr.make_image(fill_color="black", back_color="white")

        # Guardar en memoria
        buffer = BytesIO()
        qr_image.save(buffer, format='PNG')
        buffer.seek(0)

        # Guardar en el modelo
        filename = f"qr_{self.producto.numero_serie}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.png"
        self.imagen_pegatina.save(filename, File(buffer), save=False)

        return qr_image

    def _generar_codigo_barras(self):
        """Genera un código de barras con el número de serie"""
        try:
            # Usar Code128 que es versátil para alfanuméricos
            code128 = barcode.get_barcode_class('code128')
            barcode_instance = code128(self.producto.numero_serie, writer=ImageWriter())

            buffer = BytesIO()
            barcode_instance.write(buffer)
            buffer.seek(0)

            # Guardar en el modelo
            filename = f"barcode_{self.producto.numero_serie}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.imagen_pegatina.save(filename, File(buffer), save=False)

            return barcode_instance
        except Exception as e:
            # Fallback: generar imagen simple con el número de serie
            img = Image.new('RGB', (300, 100), color='white')
            draw = ImageDraw.Draw(img)
            draw.text((10, 40), self.producto.numero_serie, fill='black')

            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)

            filename = f"simple_{self.producto.numero_serie}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.imagen_pegatina.save(filename, File(buffer), save=False)

            return img

    def _generar_etiqueta_simple(self):
        """Genera una etiqueta simple con información básica"""
        # Crear imagen de etiqueta
        img = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img)

        # Información básica
        y_pos = 20
        draw.text((20, y_pos), f"S/N: {self.producto.numero_serie}", fill='black')
        y_pos += 30
        draw.text((20, y_pos), f"{self.producto.categoria.nombre}", fill='black')
        y_pos += 30
        draw.text((20, y_pos), f"{self.producto.marca.nombre} {self.producto.modelo}", fill='black')

        # Añadir datos personalizados importantes
        if hasattr(self.producto, 'datos_personalizados'):
            datos = self.producto.datos_personalizados.datos
            for key, value in list(datos.items())[:2]:  # Solo los primeros 2 campos
                if value:
                    y_pos += 25
                    draw.text((20, y_pos), f"{key}: {value}", fill='black')

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        filename = f"simple_{self.producto.numero_serie}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.png"
        self.imagen_pegatina.save(filename, File(buffer), save=False)

        return img

    def _generar_etiqueta_completa(self):
        """Genera una etiqueta completa con toda la información"""
        # Crear imagen más grande para toda la información
        img = Image.new('RGB', (600, 400), color='white')
        draw = ImageDraw.Draw(img)

        # Título
        draw.text((20, 20), "INVENTARIO - IDENTIFICACIÓN", fill='black')
        draw.line((20, 45, 580, 45), fill='black', width=2)

        # Información básica
        y_pos = 60
        draw.text((20, y_pos), f"Número de Serie: {self.producto.numero_serie}", fill='black')
        y_pos += 30
        draw.text((20, y_pos), f"Categoría: {self.producto.categoria.nombre}", fill='black')
        y_pos += 30
        draw.text((20, y_pos), f"Marca: {self.producto.marca.nombre}", fill='black')
        y_pos += 30
        draw.text((20, y_pos), f"Modelo: {self.producto.modelo}", fill='black')
        y_pos += 30
        draw.text((20, y_pos), f"Estado: {self.producto.get_estado_display()}", fill='black')

        # Datos personalizados
        if hasattr(self.producto, 'datos_personalizados'):
            y_pos += 40
            draw.text((20, y_pos), "Datos Específicos:", fill='black')
            y_pos += 25

            datos = self.producto.datos_personalizados.datos
            for key, value in datos.items():
                if value and y_pos < 350:  # Límite de espacio
                    draw.text((40, y_pos), f"• {key}: {value}", fill='black')
                    y_pos += 25

        # Fecha de generación
        draw.text((20, 370), f"Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}", fill='gray')

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        filename = f"completa_{self.producto.numero_serie}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.png"
        self.imagen_pegatina.save(filename, File(buffer), save=False)

        return img
