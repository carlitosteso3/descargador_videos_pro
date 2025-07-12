# app.py (versión 4.0 - Sin creación de carpetas, para hosting gratuito)

import os
import re
import yt_dlp
import whisper
import time
import tempfile # Importamos la librería para archivos temporales
from flask import Flask, render_template, request, send_from_directory

# --- Configuración de Flask ---
# Le decimos a Flask que los templates están en la carpeta actual ('.')
# Obtiene la ruta absoluta del directorio donde se encuentra app.py
basedir = os.path.abspath(os.path.dirname(__file__))

# Le dice a Flask que la carpeta de plantillas está en ese mismo directorio
app = Flask(__name__, template_folder=basedir)

# --- Carga del Modelo Whisper ---
print("Cargando el modelo de Whisper...")
try:
    modelo_whisper = whisper.load_model("base")
    print("Modelo de Whisper cargado con éxito.")
except Exception as e:
    print(f"Error crítico al cargar el modelo: {e}")
    modelo_whisper = None

# --- Funciones de Lógica ---
def limpiar_nombre(nombre):
    return re.sub(r'[\\/*?:"<>|#]', "", nombre).strip()[:70]

def descargar_contenido(url, solo_audio=False):
    """Descarga contenido a la carpeta temporal del sistema y devuelve la ruta completa."""
    # Generamos un nombre base único para el archivo
    nombre_base = f"descarga_{int(time.time())}"
    
    # Definimos el formato y el nombre de salida dentro de la carpeta temporal
    nombre_archivo = f"{nombre_base}.{'m4a' if solo_audio else 'mp4'}"
    ruta_salida_completa = os.path.join(tempfile.gettempdir(), nombre_archivo)
    
    # Opciones de yt-dlp
    formato = 'bestaudio/best' if solo_audio else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    opciones = {'outtmpl': ruta_salida_completa, 'format': formato, 'quiet': True, 'no_warnings': True, 'ignoreerrors': True, 'merge_output_format': 'mp4'}
    
    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None: raise Exception("No se pudo obtener información.")
            # Devolvemos el nombre del archivo (sin la ruta) y el título original
            return nombre_archivo, info.get('title', 'video')
    except Exception as e:
        raise Exception(f"Error durante la descarga: {str(e)}")

def transcribir_video(ruta_fuente):
    """Transcribe un archivo desde la carpeta temporal."""
    if not modelo_whisper: raise Exception("Modelo de Whisper no disponible.")
    try:
        # La función de whisper necesita la ruta completa al archivo
        resultado = modelo_whisper.transcribe(audio=ruta_fuente, language="es", fp16=False)
        return resultado["text"]
    except Exception as e:
        raise Exception(f"Error en transcripción: {str(e)}")

# --- Rutas de la Aplicación Web ---

@app.route('/', methods=['GET', 'POST'])
def index():
    texto_transcrito = None
    error_message = None
    enlace_descarga_video = None
    nombre_original_video = None

    if request.method == 'POST':
        video_url = request.form['video_url']
        opcion = request.form['opcion']
        
        try:
            if opcion == 'solo_video':
                print("Descargando solo el video...")
                nombre_archivo, nombre_original_video = descargar_contenido(video_url, solo_audio=False)
                enlace_descarga_video = f"/download/{nombre_archivo}"

            elif opcion == 'solo_transcripcion':
                print("Descargando audio...")
                nombre_archivo_audio, _ = descargar_contenido(video_url, solo_audio=True)
                ruta_completa_audio = os.path.join(tempfile.gettempdir(), nombre_archivo_audio)
                
                print("Transcribiendo...")
                texto_transcrito = transcribir_video(ruta_completa_audio)
                
                print("Limpiando archivo de audio temporal...")
                os.remove(ruta_completa_audio)

            elif opcion == 'ambos':
                print("Descargando video...")
                nombre_archivo_video, nombre_original_video = descargar_contenido(video_url, solo_audio=False)
                ruta_completa_video = os.path.join(tempfile.gettempdir(), nombre_archivo_video)

                print("Transcribiendo...")
                texto_transcrito = transcribir_video(ruta_completa_video)
                enlace_descarga_video = f"/download/{nombre_archivo_video}"
            
        except Exception as e:
            print(f"ERROR: {e}")
            error_message = str(e)

    return render_template('index.html', 
                           transcripcion=texto_transcrito, 
                           error_message=error_message,
                           download_link=enlace_descarga_video,
                           video_title=nombre_original_video)

@app.route('/download/<filename>')
def download_file(filename):
    """Sirve archivos desde la carpeta temporal del sistema."""
    # La ruta de donde servir es la carpeta temporal
    directorio_temporal = tempfile.gettempdir()
    return send_from_directory(directorio_temporal, filename, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
