"""
Script interactivo para descargar vídeos de YouTube usando yt-dlp.
No requiere ffmpeg instalado por separado.
"""

# Importar la biblioteca yt-dlp
from yt_dlp import YoutubeDL

# Mensaje de bienvenida
print("Bienvenido al descargador de vídeos de YouTube (usando yt-dlp)")


# Solicitar la URL al usuario (puede ser vídeo o playlist)
url = input("Introduce la URL del vídeo o playlist de YouTube que deseas descargar: ")


# Carpeta donde se guardarán los vídeos descargados
output_folder = r'C:\Users\MI PORTATIL\Documents\Grabaciones de sonido'


# Configuración para descargar el mejor formato mp4 que ya incluya audio y vídeo combinados
# Esto evita la necesidad de ffmpeg
ydl_opts = {
    'format': 'best[ext=mp4][acodec!=none][vcodec!=none]/best',
    'outtmpl': output_folder + r'/%(title)s.%(ext)s',  # Guarda el archivo en la carpeta especificada
    'quiet': True,  # Reduce la salida de la biblioteca
}

try:
    with YoutubeDL(ydl_opts) as ydl:
        # Extraer información para saber si es playlist o vídeo
        info = ydl.extract_info(url, download=False)
        if info.get('_type') == 'playlist':
            print(f"Descargando playlist: {info.get('title', 'Playlist desconocida')}")
            print(f"Número de vídeos en la playlist: {len(info.get('entries', []))}")
        else:
            print(f"Descargando vídeo: {info.get('title', 'Vídeo desconocido')}")
        # Descargar el vídeo o playlist
        ydl.download([url])
        # Mensaje de éxito
        if info.get('_type') == 'playlist':
            print("¡Descarga de playlist completada! Los vídeos se han guardado en la carpeta especificada.")
        else:
            filename = ydl.prepare_filename(info)
            print(f"¡Descarga completada! El vídeo se ha guardado como: {filename}")
except Exception as e:
    # Manejo de errores comunes
    print("Ha ocurrido un error durante la descarga:")
    print(str(e))
    print("Por favor, verifica la URL o tu conexión a internet e inténtalo de nuevo.")
