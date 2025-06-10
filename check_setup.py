#!/usr/bin/env python3
"""Script para verificar la instalación del entorno"""

import sys
import importlib

def check_python_version():
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Se requiere 3.8+")
        return False

def check_dependencies():
    dependencies = [
        "fastapi",
        "sqlmodel",
        "uvicorn",
        "agentics",
        "selenium",
        "pyaudio",
        "speech_recognition",
        "webdriver_manager",
        "pydub"
    ]
    
    all_ok = True
    for dep in dependencies:
        try:
            importlib.import_module(dep)
            print(f"✅ {dep}")
        except ImportError:
            print(f"❌ {dep} - No instalado")
            all_ok = False
    
    return all_ok

def main():
    print("🔍 Verificando entorno de desarrollo...\n")
    
    python_ok = check_python_version()
    print()
    deps_ok = check_dependencies()
    
    print("\n" + "="*50)
    if python_ok and deps_ok:
        print("✅ ¡Entorno configurado correctamente!")
    else:
        print("❌ Hay problemas con la configuración")
        print("Ejecuta: pip install -r requirements.txt")

if __name__ == "__main__":
    main()