# Importador-de-Youtube---Proyecto-
Prueba para curso de IA generativa 2025

# Guía para usar el script de descarga de YouTube

## 1. Crear un entorno virtual en Python

Es recomendable usar un entorno virtual para instalar dependencias sin afectar el sistema global.

1. Abre una terminal en la carpeta del proyecto.
2. Ejecuta el siguiente comando para crear el entorno virtual (por ejemplo, en una carpeta llamada `venv`):

```
python -m venv venv
```

3. Activa el entorno virtual:
   - En Windows PowerShell:
     ```
     .\venv\Scripts\Activate
     ```
   - En CMD:
     ```
     venv\Scripts\activate.bat
     ```
   - En Git Bash o WSL:
     ```
     source venv/bin/activate
     ```

## 2. Instalar yt-dlp en el entorno virtual

Con el entorno virtual activado, instala yt-dlp usando pip:

```
pip install yt-dlp
```

## 3. Ejecutar el script

Con yt-dlp instalado, ejecuta el script para descargar vídeos o playlists:

```
python descargar_youtube.py
```

Puedes introducir la URL de un vídeo individual o de una playlist de YouTube.

El vídeo o los vídeos descargados se guardarán en la carpeta:
```
C:\Users\MI PORTATIL\Documents\Grabaciones de sonido
```
con el nombre del título de cada vídeo.

## Notas
- El entorno virtual se guarda en la carpeta `venv`.
- Para salir del entorno virtual, ejecuta:
  ```
  deactivate
  ```
- Si tienes problemas, asegúrate de tener Python instalado y actualizado.

