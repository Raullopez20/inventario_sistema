# Sistema de Inventario

Sistema web para la gestión integral de inventario de productos, asignaciones, pegatinas identificativas y entidades maestras (categorías, marcas, proveedores, ubicaciones, empleados). Permite trazabilidad completa de activos, generación de códigos QR, reportes PDF/Excel y administración avanzada.

## Tecnologías principales
- **Backend:** Django 5.2.4
- **Base de datos:** MySQL
- **Frontend:** Bootstrap 5, Font Awesome, Bootstrap Icons
- **Imágenes y QR:** Pillow, qrcode
- **Reportes:** ReportLab (PDF), XlsxWriter (Excel)
- **Filtros y formularios:** django-filter, django-crispy-forms, crispy-bootstrap5
- **Variables de entorno:** python-dotenv, python-decouple

## Estructura del proyecto
- **productos/**: Gestión de productos, pegatinas, tipos, datos personalizados
- **asignaciones/**: Historial de entregas, devoluciones, reparaciones, préstamos
- **core/**: Categorías, departamentos, marcas, proveedores, ubicaciones, empleados
- **media/**: Imágenes y códigos QR generados
- **static/**: Archivos estáticos (CSS, JS, imágenes)
- **templates/**: Plantillas HTML (interfaz moderna y responsiva)
- **inicializar_sistema.py**: Script para limpiar todas las tablas y reiniciar el sistema
- **limpiar_pegatinas.py**: Script para limpiar pegatinas huérfanas o duplicadas

## Instalación
1. **Clona el repositorio:**
   ```bash
   git clone <URL-del-repositorio>
   cd inventario_sistema
   ```
2. **Crea y activa un entorno virtual:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # En Windows
   source venv/bin/activate  # En Linux/Mac
   ```
3. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configura la base de datos MySQL:**
   - Crea una base de datos y usuario en MySQL.
   - Configura las variables de entorno en un archivo `.env`:
     ```env
     SECRET_KEY=tu_clave_secreta
     DB_NAME=nombre_bd
     DB_USER=usuario_bd
     DB_PASSWORD=contraseña_bd
     DB_HOST=localhost
     DB_PORT=3306
     ```
5. **Realiza las migraciones:**
   ```bash
   python manage.py migrate
   ```
6. **Crea un superusuario:**
   ```bash
   python manage.py createsuperuser
   ```
7. **Inicia el servidor:**
   ```bash
   python manage.py runserver
   ```

## Uso de scripts auxiliares
- **Reiniciar el sistema:**
  ```bash
  python inicializar_sistema.py
  ```
- **Limpiar pegatinas huérfanas/duplicadas:**
  ```bash
  python limpiar_pegatinas.py
  ```

## Funcionalidades principales
- Gestión de productos con estados y condiciones
- Asignación y devolución de productos a empleados/departamentos
- Generación y administración de pegatinas QR/barcode
- Reportes en PDF y Excel
- Filtros avanzados y formularios personalizados
- Panel de administración para entidades maestras
- Interfaz web moderna y responsiva

## Recomendaciones
- Mantén el archivo `.env` fuera del control de versiones
- Realiza copias de seguridad periódicas de la base de datos
- Usa el script de inicialización solo en entornos de desarrollo/pruebas

## Créditos
Desarrollado por el equipo de informática. Basado en Django y tecnologías open source.

---
¿Dudas o sugerencias? Contacta al administrador del sistema.

