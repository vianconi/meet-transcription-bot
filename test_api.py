# test_api.py
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_api():
    """Probar los endpoints básicos de la API"""
    
    # 1. Verificar estado
    print("1. Verificando estado de la API...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Estado: {response.json()}")
    
    # 2. Health check
    print("\n2. Health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health: {response.json()}")
    
    # 3. Crear una reunión
    print("\n3. Creando reunión...")
    meeting_data = {
        "meeting_url": "https://meet.google.com/abc-defg-hij",
        "title": "Reunión de prueba"
    }
    response = requests.post(f"{BASE_URL}/meetings/", params=meeting_data)
    meeting = response.json()
    print(f"Reunión creada: {meeting}")
    meeting_id = meeting["id"]
    
    # 4. Obtener reuniones
    print("\n4. Obteniendo lista de reuniones...")
    response = requests.get(f"{BASE_URL}/meetings/")
    print(f"Reuniones: {response.json()}")
    
    # 5. Obtener reunión específica
    print(f"\n5. Obteniendo reunión {meeting_id}...")
    response = requests.get(f"{BASE_URL}/meetings/{meeting_id}")
    print(f"Reunión: {response.json()}")
    
    # 6. Iniciar transcripción
    print(f"\n6. Iniciando transcripción para reunión {meeting_id}...")
    response = requests.post(f"{BASE_URL}/meetings/{meeting_id}/start")
    print(f"Respuesta: {response.json()}")
    
    # 7. Agregar transcripción de prueba
    print(f"\n7. Agregando transcripción de prueba...")
    trans_data = {
        "meeting_id": meeting_id,
        "text": "Hola, esta es una transcripción de prueba",
        "timestamp": datetime.utcnow().isoformat(),
        "speaker": "Usuario 1",
        "confidence": 0.95
    }
    response = requests.post(f"{BASE_URL}/transcriptions/", params=trans_data)
    print(f"Transcripción creada: {response.json()}")
    
    # 8. Obtener transcripciones
    print(f"\n8. Obteniendo transcripciones de la reunión {meeting_id}...")
    response = requests.get(f"{BASE_URL}/meetings/{meeting_id}/transcriptions")
    print(f"Transcripciones: {response.json()}")
    
    # 9. Detener transcripción
    print(f"\n9. Deteniendo transcripción...")
    response = requests.post(f"{BASE_URL}/meetings/{meeting_id}/stop")
    print(f"Respuesta: {response.json()}")

if __name__ == "__main__":
    test_api()
    