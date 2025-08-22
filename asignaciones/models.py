from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import TimeStampedModel, EmpleadoReceptor, Departamento
from productos.models import Producto
import json


class AsignacionHistorial(TimeStampedModel):
    """Historial completo de asignaciones y devoluciones de productos"""

    TIPOS_ASIGNACION = [
        ('ENTREGA', 'Entrega'),
        ('DEVOLUCION', 'Devolución'),
        ('REPARACION', 'Envío a reparación'),
        ('RETORNO_REPARACION', 'Retorno de reparación'),
        ('BAJA', 'Dar de baja'),
        ('PRESTAMO', 'Préstamo temporal'),
        ('FIN_PRESTAMO', 'Fin de préstamo'),
    ]

    MOTIVOS_DEVOLUCION = [
        ('CAMBIO_EMPLEADO', 'Cambio de empleado'),
        ('AVERIA', 'Producto averiado'),
        ('OBSOLETO', 'Producto obsoleto'),
        ('ACTUALIZACION', 'Actualización de equipo'),
        ('FIN_CONTRATO', 'Fin de contrato'),
        ('TRASLADO', 'Traslado de departamento'),
        ('ROBO_PERDIDA', 'Robo o pérdida'),
        ('OTROS', 'Otros motivos'),
    ]

    # Información básica
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        verbose_name="Producto"
    )
    empleado_receptor = models.ForeignKey(
        EmpleadoReceptor,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Empleado receptor"
    )
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.CASCADE,
        verbose_name="Departamento"
    )

    # Tipo de movimiento
    tipo_asignacion = models.CharField(
        max_length=20,
        choices=TIPOS_ASIGNACION,
        verbose_name="Tipo de asignación"
    )

    # Fechas
    fecha_entrega = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha y hora de entrega"
    )
    fecha_devolucion = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha y hora de devolución"
    )
    fecha_prevista_devolucion = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha prevista de devolución",
        help_text="Para préstamos temporales"
    )

    # Motivos y observaciones
    motivo_devolucion = models.CharField(
        max_length=20,
        choices=MOTIVOS_DEVOLUCION,
        blank=True,
        null=True,
        verbose_name="Motivo de devolución"
    )
    observaciones_entrega = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones en la entrega"
    )
    observaciones_devolucion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones en la devolución"
    )

    # Usuario que registra la operación
    usuario_entrega = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='entregas_registradas',
        verbose_name="Usuario que registra la entrega"
    )
    usuario_devolucion = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='devoluciones_registradas',
        blank=True,
        null=True,
        verbose_name="Usuario que registra la devolución"
    )

    # Documentación
    documento_entrega = models.FileField(
        upload_to='documentos_asignacion/',
        blank=True,
        null=True,
        verbose_name="Documento de entrega",
        help_text="Acta de entrega firmada o similar"
    )
    documento_devolucion = models.FileField(
        upload_to='documentos_asignacion/',
        blank=True,
        null=True,
        verbose_name="Documento de devolución"
    )

    # Estado del producto en la entrega/devolución
    estado_producto_entrega = models.CharField(
        max_length=20,
        choices=Producto.CONDICIONES,
        verbose_name="Estado del producto en la entrega"
    )
    estado_producto_devolucion = models.CharField(
        max_length=20,
        choices=Producto.CONDICIONES,
        blank=True,
        null=True,
        verbose_name="Estado del producto en la devolución"
    )

    # Firma digital o confirmación
    confirmado_empleado = models.BooleanField(
        default=False,
        verbose_name="Confirmado por empleado",
        help_text="El empleado ha confirmado la recepción"
    )
    fecha_confirmacion_empleado = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de confirmación del empleado"
    )

    # Control
    activo = models.BooleanField(
        default=True,
        verbose_name="Registro activo"
    )

    class Meta:
        verbose_name = "Asignación"
        verbose_name_plural = "Historial de Asignaciones"
        ordering = ['-fecha_entrega']
        indexes = [
            models.Index(fields=['producto', 'fecha_entrega']),
            models.Index(fields=['empleado_receptor']),
            models.Index(fields=['departamento']),
            models.Index(fields=['tipo_asignacion']),
        ]

    @property
    def esta_pendiente_devolucion(self):
        """Verifica si la asignación está pendiente de devolución"""
        return self.fecha_devolucion is None and self.tipo_asignacion in ['ENTREGA', 'PRESTAMO']

    @property
    def dias_en_posesion(self):
        """Calcula los días que el producto ha estado asignado"""
        fecha_fin = self.fecha_devolucion or timezone.now()
        return (fecha_fin - self.fecha_entrega).days

    @property
    def prestamo_vencido(self):
        """Verifica si un préstamo temporal ha vencido"""
        if self.tipo_asignacion == 'PRESTAMO' and self.fecha_prevista_devolucion:
            return timezone.now().date() > self.fecha_prevista_devolucion and not self.fecha_devolucion
        return False

    def save(self, *args, **kwargs):
        # Actualizar el estado del producto al guardar
        if self.pk is None:  # Nueva asignación
            if self.tipo_asignacion in ['ENTREGA', 'PRESTAMO']:
                self.producto.estado = 'ENTREGADO'
                self.producto.save()

        super().save(*args, **kwargs)

    def marcar_devolucion(self, usuario, motivo=None, observaciones=None, estado_producto=None):
        """
        Marca la devolución de un producto, actualiza campos y el estado del producto.
        """
        self.fecha_devolucion = timezone.now()
        self.usuario_devolucion = usuario
        if motivo:
            self.motivo_devolucion = motivo
        if observaciones:
            self.observaciones_devolucion = observaciones
        if estado_producto:
            self.estado_producto_devolucion = estado_producto
            # Actualizar estado del producto según devolución
            if estado_producto == 'AVERIADO':
                self.producto.estado = 'AVERIADO'
            elif estado_producto == 'MANTENIMIENTO':
                self.producto.estado = 'MANTENIMIENTO'
            else:
                self.producto.estado = 'DISPONIBLE'
            self.producto.save()

        self.save()

    def datos_reporte(self):
        """
        Devuelve un diccionario con los datos relevantes para el reporte profesional.
        """
        return {
            "ID": self.id,
            "Producto": self.producto.nombre,
            "Empleado": self.empleado_receptor.nombre if self.empleado_receptor else "-",
            "Departamento": self.departamento.nombre,
            "Tipo": self.get_tipo_asignacion_display(),
            "Fecha Entrega": self.fecha_entrega.strftime('%d/%m/%Y'),
            "Fecha Devolución": self.fecha_devolucion.strftime('%d/%m/%Y') if self.fecha_devolucion else "-",
            "Observaciones Entrega": self.observaciones_entrega or "-",
            "Observaciones Devolución": self.observaciones_devolucion or "-",
            "Estado Producto Entrega": self.get_estado_producto_entrega_display(),
            "Estado Producto Devolución": self.get_estado_producto_devolucion_display() if self.estado_producto_devolucion else "-",
            "Motivo Devolución": self.get_motivo_devolucion_display() if self.motivo_devolucion else "-",
        }

    def __str__(self):
        empleado_info = f" - {self.empleado_receptor.nombre}" if self.empleado_receptor else ""
        return f"{self.producto.id_interno} → {self.departamento.nombre}{empleado_info} ({self.fecha_entrega.strftime('%d/%m/%Y')})"


class MovimientoStock(TimeStampedModel):
    """Registro de movimientos de stock (altas, bajas, transferencias)"""

    TIPOS_MOVIMIENTO = [
        ('ALTA', 'Alta de producto'),
        ('BAJA', 'Baja de producto'),
        ('TRANSFERENCIA', 'Transferencia de ubicación'),
        ('ACTUALIZACION', 'Actualización de datos'),
        ('REPARACION', 'Envío a reparación'),
        ('RETORNO_REPARACION', 'Retorno de reparación'),
    ]

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        verbose_name="Producto"
    )
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TIPOS_MOVIMIENTO,
        verbose_name="Tipo de movimiento"
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Usuario que registra"
    )

    # Ubicaciones
    ubicacion_origen = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Ubicación origen"
    )
    ubicacion_destino = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Ubicación destino"
    )

    # Detalles del movimiento
    descripcion = models.TextField(
        verbose_name="Descripción del movimiento"
    )
    _valor_anterior = models.TextField(
        default='{}',
        blank=True,
        verbose_name="Valores anteriores",
        help_text="Para actualizaciones, guarda los valores previos"
    )
    _valor_nuevo = models.TextField(
        default='{}',
        blank=True,
        verbose_name="Valores nuevos"
    )

    @property
    def valor_anterior(self):
        """Getter para valor_anterior - devuelve un diccionario"""
        try:
            return json.loads(self._valor_anterior) if self._valor_anterior else {}
        except json.JSONDecodeError:
            return {}

    @valor_anterior.setter
    def valor_anterior(self, value):
        """Setter para valor_anterior - acepta un diccionario"""
        self._valor_anterior = json.dumps(value) if value else '{}'

    @property
    def valor_nuevo(self):
        """Getter para valor_nuevo - devuelve un diccionario"""
        try:
            return json.loads(self._valor_nuevo) if self._valor_nuevo else {}
        except json.JSONDecodeError:
            return {}

    @valor_nuevo.setter
    def valor_nuevo(self, value):
        """Setter para valor_nuevo - acepta un diccionario"""
        self._valor_nuevo = json.dumps(value) if value else '{}'

    class Meta:
        verbose_name = "Movimiento de Stock"
        verbose_name_plural = "Movimientos de Stock"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.producto.id_interno} - {self.get_tipo_movimiento_display()} ({self.created_at.strftime('%d/%m/%Y %H:%M')})"
