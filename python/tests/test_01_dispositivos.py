#!/usr/bin/env python3
"""
Test 1.1: Dispositivos
Prueba operaciones básicas en la tabla dispositivos
"""

import sys
from pathlib import Path

# Agregar ruta del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_connection_helper import get_connection

def test_dispositivos():
    """Prueba CRUD básico en dispositivos"""
    print("\n" + "="*70)
    print("TEST 1.1: DISPOSITIVOS")
    print("="*70)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. INSERT - Insertar dispositivos
        print("\n1. Insertando dispositivos...")
        dispositivos = [
            ('Sala Papel', 1),
            ('Sala Textil', 2),
            ('Sala Madera', 3),
            ('Café Literario', 0),
            ('Tienda del Molino', 0),
            ('Laboratorio Observación', 1)
        ]
        
        for nombre, piso in dispositivos:
            cursor.execute("""
                INSERT INTO dispositivos (nombre_dispositivo, piso_dispositivo)
                VALUES (?, ?)
            """, (nombre, piso))
        
        print(f"   ✅ {len(dispositivos)} dispositivos insertados")
        
        # 2. SELECT - Consultar dispositivos
        print("\n2. Consultando dispositivos...")
        cursor.execute("SELECT * FROM dispositivos ORDER BY piso_dispositivo, nombre_dispositivo")
        results = cursor.fetchall()
        
        for row in results:
            print(f"   • [{row['id_dispositivo']}] {row['nombre_dispositivo']} - Piso {row['piso_dispositivo']}")
        
        # 3. UPDATE - Actualizar un dispositivo
        print("\n3. Actualizando dispositivo...")
        cursor.execute("""
            UPDATE dispositivos 
            SET piso_dispositivo = 2 
            WHERE nombre_dispositivo = 'Laboratorio Observación'
        """)
        print(f"   ✅ Dispositivo actualizado")
        
        # 4. Probar que NO se puede insertar piso negativo
        print("\n4. Probando constraint CHK_PISO (debe fallar)...")
        try:
            cursor.execute("""
                INSERT INTO dispositivos (nombre_dispositivo, piso_dispositivo)
                VALUES ('Test Negativo', -1)
            """)
            print("   ❌ FALLO: Constraint no funcionó")
            return False
        except Exception as e:
            print(f"   ✅ Constraint funcionó correctamente")
        
        # 5. Contar total
        cursor.execute("SELECT COUNT(*) as total FROM dispositivos")
        total = cursor.fetchone()['total']
        print(f"\n📊 Total dispositivos en la base de datos: {total}")
        
        return total >= 6

if __name__ == '__main__':
    try:
        success = test_dispositivos()
        print(f"\n{'='*70}")
        if success:
            print("✅ TEST PASADO - Todo funciona correctamente")
        else:
            print("❌ TEST FALLIDO - Revisa los errores arriba")
        print(f"{'='*70}\n")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        