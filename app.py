# app.py (versión 3.0 - Lógica de visualización directa)

import os
import re
import yt_dlp
import whisper
import time
from flask import Flask, render_template, request, send_from_directory, redirect, url_for

app = Flask(__name__)
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

print("Cargando el modelo de Whisper...")
try:
    modelo_whisper = whisper.load_model("base")
    print("Modelo de Whisper cargado con éxito.")
except Exception as e:
    print(f"Error crítico: {e}")
    modelo_whisper = None

def limpiar_nombre(nombre):
    return re.sub(r'[\\/*?:"<>|#]', "", nombre).strip()[:70]

def descargar_contenido(url, carpeta_destino, descargar_solo_audio=False):
    nombre_archivo = 'audio.%(ext)s' if descargar_solo_audio else 'video.%(ext)s'
    formato = 'bestaudio/best' if descargar_solo_audio else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    opciones = {'outtmpl': os.path.join(carpeta_destino, nombre_archivo), 'format': formato, 'quiet': True, 'no_warnings': True, 'ignoreerrors': True, 'merge_output_format': 'mp4'}
    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None: raise Exception("No se pudo obtener información.")
            return ydl.prepare_filename(info), info.get('ext', 'mp4')
    except Exception as e:
        raise Exception(f"Error durante la descarga: {str(e)}")

def transcribir_video(ruta_fuente):
    if not modelo_whisper: raise Exception("Modelo de Whisper no disponible.")
    try:
        resultado = modelo_whisper.transcribe(ruta_fuente, language="es", fp16=False)
        return resultado["text"]
    except Exception as e:
        raise Exception(f"Error en transcripción: {str(e)}")


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        video_url = request.form['video_url']
        opcion = request.form['opcion']
        
        # Variables para pasar al template
        texto_transcrito = None
        error_message = None
        enlace_descarga_video = None

        try:
            # 1. Obtener info y crear carpeta única
            print("Obteniendo información del video...")
            with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
                info = ydl.extract_info(video_url, download=False)
                nombre_base = f"{limpiar_nombre(info.get('title', 'video'))}_{info.get('id', str(int(time.time())))}"
            
            carpeta_destino = os.path.join(DOWNLOAD_FOLDER, nombre_base)
            os.makedirs(carpeta_destino, exist_ok=True)

            # 2. Lógica según la opción elegida
            if opcion == 'solo_video':
                print("Descargando solo el video...")
                descargar_contenido(video_url, carpeta_destino)
                return redirect(url_for('results', folder_name=nombre_base))

            elif opcion == 'solo_transcripcion':
                print("Descargando audio...")
                archivo_audio, _ = descargar_contenido(video_url, carpeta_destino, True)
                print("Transcribiendo...")
                texto_transcrito = transcribir_video(archivo_audio)
                print("Limpiando archivos temporales...")
                os.remove(archivo_audio) # Limpiar el audio
                # No se guardó nada, así que borramos la carpeta
                os.rmdir(carpeta_destino) 

            elif opcion == 'ambos':
                print("Descargando video...")
                archivo_video, ext_video = descargar_contenido(video_url, carpeta_destino)
                print("Transcribiendo...")
                texto_transcrito = transcribir_video(archivo_video)
                nombre_video = f"video.{ext_video}" # Reconstruir nombre del video
                enlace_descarga_video = url_for('download_file', folder_name=nombre_base, filename=nombre_video)
            
        except Exception as e:
            print(f"ERROR: {e}")
            error_message = str(e)

        # 3. Volver a mostrar la página principal con los resultados
        return render_template('index.html', 
                               transcripcion=texto_transcrito, 
                               error_message=error_message,
                               download_link=enlace_descarga_video)

    # Si es GET, solo muestra la página
    return render_template('index.html')


@app.route('/results/<folder_name>')
def results(folder_name):
    # Esta ruta ahora solo se usa para 'Solo Video'
    path_a_la_carpeta = os.path.join(DOWNLOAD_FOLDER, folder_name)
    archivos = os.listdir(path_a_la_carpeta) if os.path.exists(path_a_la_carpeta) else []
    return render_template('results.html', files=archivos, folder=folder_name)

@app.route('/download/<folder_name>/<filename>')
def download_file(folder_name, filename):
    directorio = os.path.join(DOWNLOAD_FOLDER, folder_name)
    return send_from_directory(directorio, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)