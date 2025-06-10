# test_transcription.py
# Al inicio de test_transcription.py, antes de los imports
import os
os.environ['PYTHONWARNINGS'] = 'ignore'

# Para suprimir warnings de ALSA
import sys
from ctypes import *
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
def py_error_handler(filename, line, function, err, fmt):
    pass

try:
    asound = cdll.LoadLibrary('libasound.so.2')
    c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
    asound.snd_lib_error_set_handler(c_error_handler)
except:
    pass

# Ahora tus imports normales
import asyncio
# ... resto del código
from pathlib import Path
from src.transcription.engine import TranscriptionEngine
from src.utils.logger import logger


async def test_transcription():
    """Probar motor de transcripción"""
    print("🎯 Prueba de Transcripción con Agentics")
    print("=" * 50)
    
    engine = TranscriptionEngine()
    
    # Buscar archivos de audio existentes
    audio_dir = Path("output/audio")
    audio_files = list(audio_dir.glob("*.wav"))
    
    if not audio_files:
        print("❌ No se encontraron archivos de audio en output/audio/")
        print("Ejecuta primero: python test_audio.py")
        return
    
    print(f"\n📁 Encontrados {len(audio_files)} archivos de audio")
    
    # Transcribir algunos archivos
    max_files = min(3, len(audio_files))
    print(f"\n🔄 Transcribiendo {max_files} archivos...\n")
    
    transcriptions = []
    
    for i, audio_file in enumerate(audio_files[:max_files]):
        print(f"[{i+1}/{max_files}] Procesando: {audio_file.name}")
        
        try:
            result = await engine.transcribe_audio(str(audio_file))
            transcriptions.append(result)
            
            print(f"✅ Texto: {result.get('text', '[Sin texto]')}")
            print(f"   Confianza: {result.get('confidence', 0):.1%}")
            if 'speaker' in result:
                print(f"   Hablante: {result['speaker']}")
            print()
            
        except Exception as e:
            print(f"❌ Error: {e}\n")
    
    # Generar resumen
    if transcriptions:
        print("\n📊 RESUMEN DE TRANSCRIPCIONES")
        print("=" * 50)
        formatted = engine.format_transcription(transcriptions)
        print(formatted)
        
        # Guardar en archivo
        output_file = "output/transcripts/test_transcription.txt"
        Path("output/transcripts").mkdir(exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(formatted)
        print(f"\n💾 Transcripción guardada en: {output_file}")


async def test_live_transcription():
    """Probar transcripción en vivo"""
    print("🎤 Prueba de Transcripción en Vivo")
    print("=" * 50)
    
    from src.audio.audio_manager import AudioManager
    
    manager = AudioManager()
    
    # Callback para mostrar transcripciones
    def on_audio(audio_bytes: bytes, timestamp: float):
        print(f"[{timestamp:6.1f}s] Audio capturado", end="\r")
    
    manager.on_audio_ready = on_audio
    
    print("\n📋 Dispositivos disponibles:")
    devices = manager.list_devices()
    
    try:
        device_index = int(input("\nSelecciona dispositivo: "))
        
        print("\n▶️  Iniciando captura con transcripción...")
        print("Habla durante 20 segundos. La transcripción aparecerá cada 5 segundos.")
        print("Presiona Ctrl+C para detener\n")
        
        manager.start(meeting_id=1000, device_index=device_index)
        
        # Esperar 20 segundos mostrando transcripciones
        await asyncio.sleep(20)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Deteniendo...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        manager.stop()
        
        # Mostrar transcripciones
        transcriptions = manager.get_transcriptions()
        if transcriptions:
            print("\n📝 TRANSCRIPCIONES CAPTURADAS:")
            print("=" * 50)
            for i, trans in enumerate(transcriptions):
                print(f"\n[Segmento {i+1}]")
                print(f"Tiempo: {trans.get('relative_timestamp', 0):.1f}s")
                print(f"Texto: {trans.get('text', '[Sin texto]')}")
                print(f"Hablante: {trans.get('speaker', 'Desconocido')}")


async def main():
    """Menú principal"""
    print("Selecciona una prueba:")
    print("1. Transcribir archivos existentes")
    print("2. Transcripción en vivo")
    
    choice = input("\nOpción (1-2): ")
    
    if choice == "1":
        await test_transcription()
    elif choice == "2":
        await test_live_transcription()
    else:
        print("Opción inválida")


if __name__ == "__main__":
    asyncio.run(main())
    