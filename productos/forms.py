from django import forms
from .models import Producto
from core.models import Categoria, Marca, Ubicacion, Proveedor


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'categoria', 'marca', 'modelo', 'imagen', 'numero_serie', 'codigo_barras',
            'estado', 'condicion', 'proveedor', 'fecha_compra', 'precio_compra',
            'factura_numero', 'fecha_fin_garantia', 'ubicacion_actual',
            'observaciones'
        ]
        widgets = {
            'categoria': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_categoria'
            }),
            'marca': forms.Select(attrs={
                'class': 'form-select'
            }),
            'modelo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Modelo del producto'
            }),
            'imagen': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'style': 'display: none;'
            }),
            'numero_serie': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Se generará automáticamente si se deja vacío'
            }),
            'codigo_barras': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código de barras (opcional)'
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select'
            }),
            'condicion': forms.Select(attrs={
                'class': 'form-select'
            }),
            'proveedor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'fecha_compra': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'precio_compra': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'factura_numero': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de factura (opcional)'
            }),
            'fecha_fin_garantia': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'ubicacion_actual': forms.Select(attrs={
                'class': 'form-select'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones adicionales'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['fecha_compra'].required = False
            self.fields['precio_compra'].required = False
            if self.instance.fecha_compra:
                # Formatear la fecha en yyyy-mm-dd para el input type date
                self.fields['fecha_compra'].initial = self.instance.fecha_compra.strftime('%Y-%m-%d')
                self.fields['fecha_compra'].help_text = "Fecha establecida en el registro inicial del producto"
            else:
                # Si no hay fecha, dejar el placeholder por defecto
                self.fields['fecha_compra'].widget.attrs['placeholder'] = 'dd/mm/aaaa'
            if self.instance.precio_compra:
                self.fields['precio_compra'].help_text = "Precio establecido en el registro inicial del producto"

        # Configurar querysets solo si existen los modelos
        try:
            self.fields['categoria'].queryset = Categoria.objects.filter(activo=True).order_by('nombre')
            self.fields['categoria'].empty_label = "-- Seleccionar categoría --"
        except:
            self.fields['categoria'].queryset = Categoria.objects.none()

        try:
            self.fields['marca'].queryset = Marca.objects.filter(activo=True).order_by('nombre')
            self.fields['marca'].empty_label = "-- Seleccionar marca --"
        except:
            self.fields['marca'].queryset = Marca.objects.none()

        try:
            self.fields['ubicacion_actual'].queryset = Ubicacion.objects.filter(activo=True).order_by('nombre')
            self.fields['ubicacion_actual'].empty_label = "-- Seleccionar ubicación --"
        except:
            self.fields['ubicacion_actual'].queryset = Ubicacion.objects.none()

        try:
            self.fields['proveedor'].queryset = Proveedor.objects.filter(activo=True).order_by('nombre')
            self.fields['proveedor'].empty_label = "-- Seleccionar proveedor --"
        except:
            self.fields['proveedor'].queryset = Proveedor.objects.none()

        # Hacer campos opcionales
        self.fields['numero_serie'].required = False
        self.fields['codigo_barras'].required = False
        self.fields['proveedor'].required = False
        self.fields['factura_numero'].required = False
        self.fields['fecha_fin_garantia'].required = False
        self.fields['ubicacion_actual'].required = False
        self.fields['observaciones'].required = False
        self.fields['imagen'].required = False

    def clean_numero_serie(self):
        """Validar número de serie único"""
        numero_serie = self.cleaned_data.get('numero_serie')

        if numero_serie:
            # Verificar si ya existe (excluyendo la instancia actual si estamos editando)
            queryset = Producto.objects.filter(numero_serie=numero_serie)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise forms.ValidationError("Ya existe un producto con este número de serie.")

        return numero_serie

    def clean_codigo_barras(self):
        """Validar código de barras único"""
        codigo_barras = self.cleaned_data.get('codigo_barras')

        if codigo_barras:
            # Verificar si ya existe (excluyendo la instancia actual si estamos editando)
            queryset = Producto.objects.filter(codigo_barras=codigo_barras)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise forms.ValidationError("Ya existe un producto con este código de barras.")

        return codigo_barras

    def clean_precio_compra(self):
        """Validar que el precio sea positivo"""
        precio = self.cleaned_data.get('precio_compra')

        if precio is not None and precio <= 0:
            raise forms.ValidationError("El precio debe ser mayor que 0.")

        return precio

    def clean_fecha_compra(self):
        fecha = self.cleaned_data.get('fecha_compra')
        if not fecha and self.instance and self.instance.pk:
            return self.instance.fecha_compra
        return fecha


class DatosPersonalizadosForm(forms.Form):
    """Formulario dinámico para datos personalizados"""

    def __init__(self, tipo_producto=None, datos_existentes=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if tipo_producto:
            self._agregar_campos_dinamicos(tipo_producto, datos_existentes)

    def _agregar_campos_dinamicos(self, tipo_producto, datos_existentes=None):
        """Agrega campos dinámicamente según el tipo de producto"""
        try:
            campos_config = tipo_producto.get_campos_personalizados()

            for campo_nombre, config in campos_config.items():
                field_name = f"campo_{campo_nombre}"
                field_type = config.get('type', 'text')
                field_label = config.get('label', campo_nombre.replace('_', ' ').title())
                field_required = config.get('required', False)
                field_help = config.get('help_text', '')

                # Obtener valor existente si lo hay
                initial_value = None
                if datos_existentes:
                    initial_value = datos_existentes.get_dato(campo_nombre)

                # Crear el campo según el tipo
                if field_type == 'text':
                    field = forms.CharField(
                        label=field_label,
                        required=field_required,
                        initial=initial_value,
                        help_text=field_help,
                        widget=forms.TextInput(attrs={'class': 'form-control'})
                    )
                elif field_type == 'number':
                    field = forms.IntegerField(
                        label=field_label,
                        required=field_required,
                        initial=initial_value,
                        help_text=field_help,
                        widget=forms.NumberInput(attrs={'class': 'form-control'})
                    )
                elif field_type == 'email':
                    field = forms.EmailField(
                        label=field_label,
                        required=field_required,
                        initial=initial_value,
                        help_text=field_help,
                        widget=forms.EmailInput(attrs={'class': 'form-control'})
                    )
                elif field_type == 'textarea':
                    field = forms.CharField(
                        label=field_label,
                        required=field_required,
                        initial=initial_value,
                        help_text=field_help,
                        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
                    )
                else:
                    # Campo de texto por defecto
                    field = forms.CharField(
                        label=field_label,
                        required=field_required,
                        initial=initial_value,
                        help_text=field_help,
                        widget=forms.TextInput(attrs={'class': 'form-control'})
                    )

                self.fields[field_name] = field

        except Exception as e:
            print(f"Error al agregar campos dinámicos: {e}")
            pass
