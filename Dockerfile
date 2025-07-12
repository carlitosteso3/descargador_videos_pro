# Usamos una imagen base oficial de Python
FROM python:3.11-slim

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Actualizamos los paquetes del sistema e instalamos ffmpeg
# 'apt-get update' actualiza la lista de paquetes disponibles
# 'apt-get install -y ffmpeg' instala ffmpeg y sus dependencias sin pedir confirmación
RUN apt-get update && apt-get install -y ffmpeg

# Copiamos el archivo de requerimientos primero para aprovechar el caché de Docker
COPY requirements.txt .

# Instalamos las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto de los archivos de la aplicación (app.py, index.html, etc.)
COPY . .

# Exponemos el puerto que Flask usará (Render usa 10000 por defecto)
EXPOSE 10000

# El comando para iniciar la aplicación cuando el contenedor arranque
# Usamos gunicorn, un servidor WSGI de producción que es mejor que el de desarrollo de Flask
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--timeout", "300"]
