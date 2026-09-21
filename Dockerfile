# Usamos la versión de Python que requieren tus scripts
FROM python:3.12-slim

# Evitar que Python genere archivos .pyc y asegurar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalamos dependencias del sistema indispensables
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    cmake \
    git \
    curl \
    libglib2.0-0 \
    libstdc++6 \
    libx11-6 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxi6 \
    libxtst6 \
    libnss3 \
    libnspr4 \
    libpango-1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxrandr2 \
    libasound2 \
    libatspi2.0-0 \
    libxfixes3 \
    libxrender1 \
    libgbm1 \
    && rm -rf /var/lib/apt/lists/*

# Instalamos las librerías de Python indicadas por los desarrolladores
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 
# Añadimos gunicorn para producción y el driver de Postgres
RUN pip install --no-cache-dir gunicorn psycopg2-binary

# Copiamos todo el proyecto
COPY . .

# Creamos directorios necesarios para datos e imágenes
RUN mkdir -p db_datos img

# Exponemos el puerto de Django
EXPOSE 8000

# Comando de inicio usando el servidor de desarrollo de Django
# (Para producción real, se recomienda usar Gunicorn)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
