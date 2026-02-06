#!/usr/bin/env python3
"""
DIAGNÓSTICO: ¿Por qué los 5 aliases no se cargan?
Ejecutar: python3 diagnostico_aliases.py
"""

import pandas as pd
import sqlite3
import unicodedata

def normalizar(texto):
    if texto is None:
        return ''
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto

print("="*70)
print("  DIAGNÓSTICO COMPLETO DE ALIASES")
print("="*70)

# Archivos
EXCEL_EQ = 'data/equivalencias.xlsx'  # o donde esté
DB_PATH = 'data/gestion_rrhh.db'

# 1. Leer equivalencias
print("\n[1/5] Leyendo tabla de equivalencias...")
try:
    df_eq = pd.read_excel(EXCEL_EQ)
    print(f"  ✅ Leído: {len(df_eq)} filas")
    
    # Crear mapeo como lo hace el script
    alias_map = {
        normalizar(r['Residente 2025']): normalizar(r['NOMBRE Y APELLIDO']).split(',')[0]
        for _, r in df_eq.iterrows()
        if pd.notna(r['Residente 2025'])
    }
    print(f"  ✅ Mapeo creado: {len(alias_map)} aliases")
    
except Exception as e:
    print(f"  ❌ Error: {e}")
    print(f"  Asegúrate de que existe: {EXCEL_EQ}")
    exit(1)

# 2. Leer BD
print("\n[2/5] Leyendo base de datos...")
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id_agente, apellido FROM datos_personales")
    agentes_bd = {normalizar(a): i for i, a in cursor.fetchall()}
    print(f"  ✅ BD leída: {len(agentes_bd)} agentes")
    
except Exception as e:
    print(f"  ❌ Error: {e}")
    print(f"  Asegúrate de que existe: {DB_PATH}")
    exit(1)

# 3. Verificar los 5 problemáticos
print("\n[3/5] Verificando los 5 aliases problemáticos...")
print("-"*70)

problematicos = ['Flor D.', 'Luna M.', 'Ludmi P.', 'Magali W.', 'Sol F.']

resultados = {}
for alias in problematicos:
    alias_norm = normalizar(alias)
    apellido = alias_map.get(alias_norm)
    
    print(f"\n{alias}:")
    print(f"  1. Alias normalizado: '{alias_norm}'")
    
    if not apellido:
        print(f"  ❌ NO está en tabla equivalencias")
        resultados[alias] = 'NO_EN_EQUIVALENCIAS'
        continue
    
    print(f"  2. Apellido del mapa: '{apellido}'")
    
    if apellido not in agentes_bd:
        print(f"  ❌ Apellido NO encontrado en BD")
        resultados[alias] = 'NO_EN_BD'
        continue
    
    id_agente = agentes_bd[apellido]
    print(f"  3. ID en BD: {id_agente}")
    print(f"  ✅ DEBERÍA CARGARSE CORRECTAMENTE")
    resultados[alias] = 'OK'

# 4. Diagnóstico final
print("\n" + "="*70)
print("  DIAGNÓSTICO FINAL")
print("="*70)

todos_ok = all(v == 'OK' for v in resultados.values())

if todos_ok:
    print("\n✅ TODOS LOS ALIASES DEBERÍAN FUNCIONAR")
    print("\nPero si NO se están cargando, el problema puede ser:")
    print("\n1. El archivo equivalencias.xlsx NO es el que usa el script")
    print("   Verificar: ¿Dónde está realmente el archivo?")
    print(f"   El script busca en: {EXCEL_EQ}")
    print()
    print("2. Existe un problema con el orden de lectura")
    print("   Solución: Re-ejecutar el script después de guardar cambios")
    print()
    print("3. Los datos en conv.xlsx tienen el alias con formato diferente")
    print("   Ejemplo: 'Flor D.' vs 'Flor D' (sin punto)")
else:
    print("\n❌ PROBLEMAS DETECTADOS:")
    for alias, status in resultados.items():
        if status != 'OK':
            print(f"  • {alias}: {status}")

# 5. Sugerencia de solución
print("\n" + "="*70)
print("  SOLUCIÓN PROPUESTA")
print("="*70)

if todos_ok:
    print("""
PASO 1: Verificar que el script usa el archivo correcto

En cargar_final_v2_2.py, buscar la línea:
  EXCEL_EQUIVALENCIAS = ...

Debe apuntar al archivo que acabas de actualizar.

PASO 2: Verificar formato en conv.xlsx

Abrir conv.xlsx hoja 'Convocatoria' y buscar una fila con "Flor D."
¿El alias coincide EXACTAMENTE? (mayúsculas, puntos, espacios)

PASO 3: Re-ejecutar con verbose

Agregar prints en el script para ver qué está pasando:
  print(f"Buscando alias: '{alias}' normalizado: '{normalizar(alias)}'")
  print(f"Apellido encontrado: '{apellido}'")
  print(f"ID en BD: {agentes.get(apellido)}")
""")
else:
    print("""
ESTOS ALIASES NO ESTÁN CORRECTAMENTE CONFIGURADOS.

Necesitas:
  1. Agregar los aliases faltantes a equivalencias.xlsx
  2. O cargar los residentes faltantes en la BD
""")

# 6. Ver mapa completo
print("\n" + "="*70)
print("  MAPA COMPLETO DE ALIASES (primeros 10)")
print("="*70)
for i, (alias_norm, apellido) in enumerate(sorted(alias_map.items())):
    if i >= 10:
        print(f"  ... y {len(alias_map)-10} más")
        break
    print(f"  '{alias_norm}' → '{apellido}'")

conn.close()

print("\n" + "="*70)
print("  DIAGNÓSTICO COMPLETADO")
print("="*70)