#!/usr/bin/env python3
"""
Test 1.2: Días
Prueba la generación del calendario
"""

import sys
from pathlib import Path
from datetime import date, timedelta

# Agregar ruta del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_connection_helper import get_connection

def test_dias():
    """Prueba generación de calendario"""
    print("\n" + "="*70)
    print("TEST 1.2: DÍAS (CALENDARIO)")
    print("="*70)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Generar 90 días
        print("\n1. Generando 90 días de calendario...")
        start_date = date.today()
        inserted = 0
        
        for i in range(90):
            current_date = start_date + timedelta(days=i)
            
            cursor.execute("""
                INSERT OR IGNORE INTO dias 
                (fecha, mes, semana, dia, numero_dia_semana, es_feriado)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (
                current_date.isoformat(),
                current_date.month,
                current_date.isocalendar()[1],
                current_date.day,
                current_date.weekday()
            ))
            
            if cursor.rowcount > 0:
                inserted += 1
        
        print(f"   ✅ {inserted} días nuevos insertados")
        
        # 2. Verificar datos
        print("\n2. Verificando datos...")
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                MIN(fecha) as primera_fecha,
                MAX(fecha) as ultima_fecha,
                COUNT(DISTINCT mes) as meses_distintos
            FROM dias
        """)
        stats = cursor.fetchone()
        
        print(f"   • Total días: {stats['total']}")
        print(f"   • Rango: {stats['primera_fecha']} a {stats['ultima_fecha']}")
        print(f"   • Meses cubiertos: {stats['meses_distintos']}")
        
        # 3. Marcar un feriado (25 de diciembre)
        print("\n3. Marcando feriado (25 dic)...")
        cursor.execute("""
            UPDATE dias 
            SET es_feriado = 1, nombre_feriado = 'Navidad'
            WHERE mes = 12 AND dia = 25
        """)
        
        cursor.execute("SELECT COUNT(*) as n FROM dias WHERE es_feriado = 1")
        feriados = cursor.fetchone()['n']
        print(f"   ✅ Feriados marcados: {feriados}")
        
        # 4. Probar que NO se puede duplicar fecha
        print("\n4. Probando UNIQUE en fecha (debe fallar)...")
        try:
            cursor.execute("""
                INSERT INTO dias (fecha, mes, semana, dia, numero_dia_semana)
                VALUES (?, 12, 50, 11, 3)
            """, (date.today().isoformat(),))
            print("   ❌ FALLO: UNIQUE no funcionó")
            return False
        except Exception as e:
            print(f"   ✅ UNIQUE funcionó correctamente")
        
        return stats['total'] >= 90

if __name__ == '__main__':
    try:
        success = test_dias()
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