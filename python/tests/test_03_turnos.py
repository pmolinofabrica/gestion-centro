#!/usr/bin/env python3
"""
Test 1.3: Turnos
Prueba el catálogo de turnos
"""

import sys
from pathlib import Path

# Agregar ruta del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_connection_helper import get_connection

def test_turnos():
    """Prueba catálogo de turnos"""
    print("\n" + "="*70)
    print("TEST 1.3: TURNOS")
    print("="*70)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Crear turnos base
        print("\n1. Creando turnos base...")
        turnos = [
            # Lunes a Viernes - Mañana
            (1, 'mañana', '09:00', '13:00', 4.0),
            (2, 'mañana', '09:00', '13:00', 4.0),
            (3, 'mañana', '09:00', '13:00', 4.0),
            (4, 'mañana', '09:00', '13:00', 4.0),
            (5, 'mañana', '09:00', '13:00', 4.0),
            # Lunes a Viernes - Tarde
            (1, 'tarde', '14:00', '18:00', 4.0),
            (2, 'tarde', '14:00', '18:00', 4.0),
            (3, 'tarde', '14:00', '18:00', 4.0),
            (4, 'tarde', '14:00', '18:00', 4.0),
            (5, 'tarde', '14:00', '18:00', 4.0),
            # Sábado
            (6, 'apertura_publico', '10:00', '14:00', 4.0),
            # Capacitación (cualquier día)
            (8, 'capacitacion', '09:00', '17:00', 8.0),
            # Descanso
            (0, 'descanso', '00:00', '00:00', 0.0),
        ]
        
        inserted = 0
        for numero_dia, tipo, inicio, fin, horas in turnos:
            try:
                cursor.execute("""
                    INSERT INTO turnos 
                    (numero_dia_semana, tipo_turno, hora_inicio, hora_fin, cant_horas)
                    VALUES (?, ?, ?, ?, ?)
                """, (numero_dia, tipo, inicio, fin, horas))
                inserted += 1
            except:
                pass  # Ya existe
        
        print(f"   ✅ {inserted} turnos nuevos insertados")
        
        # 2. Consultar por día
        print("\n2. Turnos por día de semana:")
        dias_semana = {
            0: 'Domingo', 1: 'Lunes', 2: 'Martes', 3: 'Miércoles',
            4: 'Jueves', 5: 'Viernes', 6: 'Sábado', 8: 'Todos'
        }
        
        for num_dia, nombre_dia in dias_semana.items():
            cursor.execute("""
                SELECT COUNT(*) as n FROM turnos 
                WHERE numero_dia_semana = ?
            """, (num_dia,))
            count = cursor.fetchone()['n']
            if count > 0:
                print(f"   • {nombre_dia}: {count} turno(s)")
        
        # 3. Probar que NO se puede insertar tipo inválido
        print("\n3. Probando constraint tipo_turno (debe fallar)...")
        try:
            cursor.execute("""
                INSERT INTO turnos 
                (numero_dia_semana, tipo_turno, hora_inicio, hora_fin, cant_horas)
                VALUES (1, 'tipo_invalido', '09:00', '13:00', 4.0)
            """)
            print("   ❌ FALLO: Constraint no funcionó")
            return False
        except Exception as e:
            print(f"   ✅ Constraint funcionó correctamente")
        
        # 4. Total de horas disponibles por semana
        print("\n4. Calculando horas disponibles por semana...")
        cursor.execute("""
            SELECT SUM(cant_horas) as total_horas
            FROM turnos
            WHERE tipo_turno != 'descanso'
        """)
        total = cursor.fetchone()['total_horas']
        print(f"   📊 Total horas semanales: {total}h")
        
        cursor.execute("SELECT COUNT(*) as n FROM turnos")
        total_turnos = cursor.fetchone()['n']
        
        return total_turnos >= 13

if __name__ == '__main__':
    try:
        success = test_turnos()
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