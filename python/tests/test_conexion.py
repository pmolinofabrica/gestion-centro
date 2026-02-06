#!/usr/bin/env python3
"""
Script de prueba de conexión con Foreign Keys
"""

from db_connection_helper import get_connection

def test_conexion():
    """Prueba la conexión y las Foreign Keys"""
    
    print("="*70)
    print("  TEST DE CONEXIÓN")
    print("="*70)
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Verificar Foreign Keys
            cursor.execute("PRAGMA foreign_keys")
            fk_status = cursor.fetchone()[0]
            print(f"\n1. Foreign Keys: {'✓ ACTIVADAS' if fk_status else '✗ DESACTIVADAS'}")
            
            # 2. Ver configuración
            print("\n2. Configuración del sistema:")
            cursor.execute("SELECT clave, valor FROM configuracion LIMIT 3")
            for row in cursor.fetchall():
                print(f"   • {row['clave']}: {row['valor']}")
            
            # 3. Contar tablas
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM datos_personales) as agentes,
                    (SELECT COUNT(*) FROM dispositivos) as dispositivos,
                    (SELECT COUNT(*) FROM dias) as dias,
                    (SELECT COUNT(*) FROM turnos) as turnos
            """)
            counts = cursor.fetchone()
            
            print("\n3. Estado de las tablas:")
            print(f"   • Agentes: {counts['agentes']}")
            print(f"   • Dispositivos: {counts['dispositivos']}")
            print(f"   • Días generados: {counts['dias']}")
            print(f"   • Turnos: {counts['turnos']}")
            
            # 4. Salud del sistema
            cursor.execute("SELECT estado_sistema FROM vista_salud_sistema")
            salud = cursor.fetchone()['estado_sistema']
            print(f"\n4. Estado del sistema: {salud}")
            
            print("\n" + "="*70)
            print("✅ CONEXIÓN FUNCIONANDO CORRECTAMENTE")
            print("="*70)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    
    return True

if __name__ == '__main__':
    import sys
    success = test_conexion()
    sys.exit(0 if success else 1)
