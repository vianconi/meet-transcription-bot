# check_agentics.py
import agentics
import inspect

print("Agentics version:", getattr(agentics, '__version__', 'Unknown'))
print("\nContenido disponible en agentics:")
print(dir(agentics))

print("\n\nClases y funciones:")
for name, obj in inspect.getmembers(agentics):
    if inspect.isclass(obj) or inspect.isfunction(obj):
        print(f"- {name}: {type(obj).__name__}")
        