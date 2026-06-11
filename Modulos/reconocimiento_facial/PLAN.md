### **Plan Detallado del Proyecto: Reconocimiento Facial**

Este plan está diseñado para ser modular, permitiéndote construir el sistema paso a paso.

---

#### **Fase 1: Configuración del Entorno y Estructura del Proyecto**

1.  **Instalación de Dependencias:**
    *   Crear un entorno virtual de Python para aislar las dependencias del proyecto.
    *   Instalar las bibliotecas necesarias: `Flask`, `ultralytics`, `opencv-python`, `Pillow`, `numpy` y `torch`.

2.  **Estructura de Carpetas y Archivos:**
    *   `reconocimiento_facial/`
        *   `app.py`: El archivo principal de la aplicación Flask. Contendrá las rutas y la lógica principal.
        *   `database.py`: Módulo para gestionar la conexión y las operaciones con la base de datos SQLite.
        *   `face_utils.py`: Un módulo con funciones de ayuda para el procesamiento de imágenes, como la extracción de características faciales.
        *   `templates/`: Carpeta para las plantillas HTML.
            *   `index.html`: Página de inicio.
            *   `profiles.html`: Para crear y ver los perfiles de las personas.
            *   `upload.html`: Formulario para subir videos o usar la cámara.
        *   `static/`: Para archivos estáticos.
            *   `uploads/`: Donde se guardarán temporalmente los videos subidos.
            *   `profiles_data/`: Para almacenar las imágenes de los perfiles.
            *   `detections_data/`: Para guardar las imágenes de los rostros detectados.
        *   `models/`: Aquí se guardará el modelo de Ultralytics pre-entrenado.

---

#### **Fase 2: Base de Datos y Gestión de Perfiles**

1.  **Diseño de la Base de Datos (`database.py`):**
    *   Se creará una base de datos SQLite (`database.db`).
    *   **Tabla `Personas`:**
        *   `id`: INTEGER, PRIMARY KEY
        *   `nombre`: TEXT, NOT NULL
    *   **Tabla `ImagenesPerfil`:**
        *   `id`: INTEGER, PRIMARY KEY
        *   `persona_id`: INTEGER (Foreign Key a `Personas`)
        *   `ruta_imagen`: TEXT, NOT NULL
        *   `caracteristicas_faciales`: BLOB (para almacenar el vector de características)
    *   **Tabla `Detecciones`:**
        *   `id`: INTEGER, PRIMARY KEY
        *   `persona_id`: INTEGER (Foreign Key a `Personas`, puede ser nulo si no se identifica)
        *   `ruta_imagen_captura`: TEXT, NOT NULL
        *   `fecha_hora`: TIMESTAMP

2.  **Módulo de Gestión de Perfiles (`app.py` y `templates/profiles.html`):**
    *   Crear una página web donde puedas:
        *   Añadir una nueva persona.
        *   Subir múltiples imágenes para esa persona.
    *   **Proceso:** Por cada imagen subida para un perfil, el sistema detectará el rostro, extraerá sus características (usando el modelo de Ultralytics) y las guardará en la tabla `ImagenesPerfil`.

---

#### **Fase 3: Detección y Reconocimiento Facial**

1.  **Análisis de Videos Pre-cargados (`app.py` y `face_utils.py`):**
    *   Implementar una ruta en Flask que acepte la subida de un archivo de video.
    *   El servidor procesará el video cuadro por cuadro.
    *   En cada cuadro:
        1.  Usar el modelo de Ultralytics para detectar todos los rostros.
        2.  Para cada rostro detectado, extraer su vector de características.
        3.  Comparar este vector con los vectores almacenados en la base de datos (`ImagenesPerfil`). Se usará una métrica de similitud (como la similitud del coseno) para encontrar la coincidencia más cercana.
        4.  Si la similitud supera un umbral predefinido, se considera una identificación.
        5.  Guardar la información de la detección (imagen del rostro, nombre si se identifica, y fecha/hora) en la tabla `Detecciones`.

2.  **Detección en Tiempo Real con Webcam (`app.py`):**
    *   Crear una ruta que utilice `OpenCV` para capturar video desde la cámara web.
    *   Enviar los cuadros al servidor (por ejemplo, usando WebSockets o streaming de video) para realizar el mismo proceso de detección y reconocimiento que en el paso anterior.
    *   Devolver los resultados para que se puedan dibujar cuadros delimitadores y nombres sobre el video en el navegador.

---

#### **Fase 4: Interfaz de Usuario**

1.  **Página Principal (`index.html`):**
    *   Un menú de navegación simple para ir a la gestión de perfiles o al análisis de video.

2.  **Visualización de Resultados:**
    *   En la página de análisis, mostrar el video procesado con los rostros detectados enmarcados.
    *   Si un rostro es identificado, mostrar el nombre de la persona.
    *   Crear una vista para explorar las detecciones guardadas en la base de datos.

