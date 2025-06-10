# test_audio.py
import time
import sys
from src.audio.audio_manager import AudioManager
from src.utils.logger import logger


def test_audio_capture():
    """Probar captura de audio"""
    print("🎤 Prueba de captura de audio")
    print("=" * 50)
    
    # Crear manager
    manager = AudioManager()
    
    # Listar dispositivos
    print("\n📋 Dispositivos de audio disponibles:")
    devices = manager.list_devices()
    
    if not devices:
        print("❌ No se encontraron dispositivos de audio")
        return
    
    # Solicitar dispositivo
    print("\n🔊 Selecciona el dispositivo de audio para capturar:")
    print("(Busca 'Stereo Mix', 'What U Hear', o similar para capturar audio del sistema)")
    
    try:
        device_index = int(input("\nÍndice del dispositivo: "))
    except ValueError:
        print("❌ Índice inválido")
        return
    
    # Configurar callback
    def on_audio(audio_bytes: bytes, timestamp: float):
        level = manager.get_audio_level()
        bars = "█" * int(level * 50)
        print(f"\r[{timestamp:6.1f}s] Audio: {bars:<50} ({level:.1%})", end="")
    
    manager.on_audio_ready = on_audio
    
    # Iniciar captura
    print(f"\n▶️  Iniciando captura con dispositivo {device_index}...")
    print("Presiona Ctrl+C para detener\n")
    
    try:
        manager.start(meeting_id=999, device_index=device_index)
        
        # Capturar por 30 segundos
        start_time = time.time()
        while time.time() - start_time < 30:
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Deteniendo captura...")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
    finally:
        manager.stop()
        print("\n✅ Prueba completada")
        print(f"📁 Archivos guardados en: {manager.output_dir}")


def test_audio_processing():
    """Probar procesamiento de audio"""
    print("\n🔧 Prueba de procesamiento de audio")
    print("=" * 50)
    
    from src.audio.processor import AudioProcessor
    import numpy as np
    
    processor = AudioProcessor()
    
    # Generar audio de prueba (tono de 440Hz)
    duration = 2.0
    sample_rate = processor.sample_rate
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = (np.sin(2 * np.pi * 440 * t) * 32767 * 0.3).astype(np.int16)
    
    # Procesar
    processor.add_chunk(audio_data, duration)
    wav_bytes = processor.process_buffer()
    
    if wav_bytes:
        print("✅ Audio procesado correctamente")
        print(f"📊 Tamaño: {len(wav_bytes)} bytes")
        
        # Guardar archivo de prueba
        processor.save_audio_to_file(wav_bytes, "output/test_tone.wav")
        print("📁 Archivo de prueba guardado: output/test_tone.wav")
    else:
        print("❌ Error al procesar audio")


def test_audio_api():
    """Probar endpoints de audio de la API"""
    import requests
    
    print("\n🌐 Prueba de API de audio")
    print("=" * 50)
    
    BASE_URL = "http://localhost:8000"
    
    # 1. Listar dispositivos
    print("\n1. Listando dispositivos de audio...")
    response = requests.get(f"{BASE_URL}/audio/devices")
    if response.status_code == 200:
        devices = response.json()["devices"]
        print(f"✅ Encontrados {len(devices)} dispositivos")
        for device in devices:
            print(f"   [{device['index']}] {device['name']}")
    else:
        print(f"❌ Error: {response.status_code}")
        return
    
    # 2. Estado inicial
    print("\n2. Verificando estado inicial...")
    response = requests.get(f"{BASE_URL}/audio/status")
    print(f"Estado: {response.json()}")
    
    # 3. Iniciar captura
    print("\n3. Iniciando captura de audio...")
    device_index = int(input("Selecciona dispositivo (índice): "))
    response = requests.post(
        f"{BASE_URL}/meetings/1/audio/start",
        params={"device_index": device_index}
    )
    print(f"Respuesta: {response.json()}")
    
    # 4. Monitorear por 10 segundos
    print("\n4. Monitoreando niveles de audio por 10 segundos...")
    for i in range(10):
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/audio/status")
        status = response.json()
        level = status.get("audio_level", 0)
        bars = "█" * int(level * 50)
        print(f"[{i+1:2d}s] Audio: {bars:<50} ({level:.1%})")
    
    # 5. Detener captura
    print("\n5. Deteniendo captura...")
    response = requests.post(f"{BASE_URL}/meetings/1/audio/stop")
    print(f"Respuesta: {response.json()}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "process":
            test_audio_processing()
        elif sys.argv[1] == "api":
            test_audio_api()
    else:
        test_audio_capture()
        