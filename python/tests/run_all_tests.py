#!/usr/bin/env python3
"""
Ejecutar todos los tests del sistema
"""

import subprocess
import sys
from pathlib import Path

tests = [
    ('test_01_dispositivos.py', 'Dispositivos'),
    ('test_02_dias.py', 'Días'),
    ('test_03_turnos.py', 'Turnos'),
    ('test_04_datos_personales.py', 'Datos Personales'),
    ('test_05_planificacion.py', 'Planificación'),
    ('test_06_descansos.py', 'Descansos')
]

print("="*70)
print("SUITE COMPLETA DE TESTS")
print("="*70)

resultados = []
base_path = Path(__file__).parent

for archivo, nombre in tests:
    test_path = base_path / archivo
    
    if not test_path.exists():
        print(f"\n▶️  Test: {nombre}")
        print("-"*70)
        print(f"❌ Archivo no encontrado: {archivo}")
        resultados.append((nombre, False))
        continue
    
    print(f"\n▶️  Test: {nombre}")
    print("-"*70)
    
    result = subprocess.run(
        [sys.executable, str(test_path)],
        capture_output=False
    )
    
    resultados.append((nombre, result.returncode == 0))
    print()

print("="*70)
print("RESUMEN FINAL")
print("="*70)

pasados = sum(1 for _, passed in resultados if passed)
total = len(resultados)

for nombre, passed in resultados:
    status = "✅ PASADO" if passed else "❌ FALLADO"
    print(f"  {nombre}: {status}")

print()
print(f"Total: {pasados}/{total} tests pasados")

if pasados == total:
    print("\n🎉 ¡TODOS LOS TESTS PASARON!")
    sys.exit(0)
else:
    print(f"\n⚠️  {total - pasados} test(s) fallaron")
    sys.exit(1)
