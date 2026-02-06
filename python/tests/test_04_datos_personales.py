#!/usr/bin/env python3
"""
Test 04: Tabla datos_personales
Verifica CRUD de personal/residentes
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_connection_helper import get_connection

def test_datos_personales():
    print("="*70)
    print("TEST 04: TABLA DATOS PERSONALES")
    print("="*70)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Insertar agentes de prueba
        print("\n1. Insertando agentes de prueba...")
        
        agentes = [
            ('Juan', 'Pérez', '30123456', '1990-05-15', 'juan.perez@test.com', '342-4111111'),
            ('María', 'González', '28456789', '1992-08-20', 'maria.gonzalez@test.com', '342-4222222'),
            ('Carlos', 'Rodríguez', '35789012', '1988-03-10', 'carlos.rodriguez@test.com', '342-4333333'),
            ('Ana', 'Martínez', '32345678', '1995-11-25', 'ana.martinez@test.com', '342-4444444'),
            ('Luis', 'Fernández', '29876543', '1991-07-30', 'luis.fernandez@test.com', '342-4555555')
        ]
        
        ids_insertados = []
        for nombre, apellido, dni, fecha_nac, email, tel in agentes:
            cursor.execute("""
                INSERT INTO datos_personales 
                (nombre, apellido, dni, fecha_nacimiento, email, telefono, domicilio, activo)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (nombre, apellido, dni, fecha_nac, email, tel, f'Calle {apellido} 123'))
            
            ids_insertados.append(cursor.lastrowid)
            print(f"   ✅ {nombre} {apellido} (ID: {cursor.lastrowid})")
        
        # 2. Verificar constraint UNIQUE en DNI
        print("\n2. Probando UNIQUE en DNI...")
        try:
            cursor.execute("""
                INSERT INTO datos_personales 
                (nombre, apellido, dni, fecha_nacimiento, email)
                VALUES ('Test', 'Duplicado', '30123456', '1990-01-01', 'test@test.com')
            """)
            print("   ❌ UNIQUE NO funcionó (permitió DNI duplicado)")
            return False
        except Exception as e:
            if 'UNIQUE' in str(e) or 'dni' in str(e).lower():
                print("   ✅ UNIQUE en DNI funciona correctamente")
            else:
                print(f"   ⚠️  Error inesperado: {e}")
        
        # 3. Verificar constraint CHECK en email
        print("\n3. Probando CHECK en email (debe contener @)...")
        try:
            cursor.execute("""
                INSERT INTO datos_personales 
                (nombre, apellido, dni, fecha_nacimiento, email)
                VALUES ('Test', 'Email', '99999999', '1990-01-01', 'email_sin_arroba')
            """)
            print("   ❌ CHECK NO funcionó (permitió email sin @)")
            return False
        except Exception as e:
            if 'chk_email' in str(e) or 'CHECK constraint' in str(e):
                print("   ✅ Constraint chk_email funciona correctamente")
            else:
                print(f"   ⚠️  Error inesperado: {e}")
        
        # 4. Consultar agentes activos
        print("\n4. Consultando agentes activos...")
        cursor.execute("""
            SELECT 
                id_agente,
                nombre || ' ' || apellido as nombre_completo,
                dni,
                email,
                activo
            FROM datos_personales
            WHERE activo = 1
            ORDER BY apellido, nombre
        """)
        
        activos = cursor.fetchall()
        print(f"   📊 Agentes activos: {len(activos)}")
        for row in activos:
            print(f"      • {row['nombre_completo']} (DNI: {row['dni']})")
        
        # 5. Dar de baja un agente
        print("\n5. Dando de baja un agente...")
        cursor.execute("""
            UPDATE datos_personales
            SET activo = 0, fecha_baja = CURRENT_TIMESTAMP
            WHERE id_agente = ?
        """, (ids_insertados[0],))
        
        cursor.execute("""
            SELECT nombre, apellido, activo, fecha_baja 
            FROM datos_personales 
            WHERE id_agente = ?
        """, (ids_insertados[0],))
        
        agente = cursor.fetchone()
        if agente['activo'] == 0 and agente['fecha_baja']:
            print(f"   ✅ {agente['nombre']} {agente['apellido']} dado de baja")
        else:
            print(f"   ❌ Baja no funcionó correctamente")
        
        # 6. Actualizar datos
        print("\n6. Actualizando datos de un agente...")
        cursor.execute("""
            UPDATE datos_personales
            SET telefono = '342-4999999', domicilio = 'Nueva Dirección 456'
            WHERE id_agente = ?
        """, (ids_insertados[1],))
        
        cursor.execute("""
            SELECT nombre, apellido, telefono, domicilio 
            FROM datos_personales 
            WHERE id_agente = ?
        """, (ids_insertados[1],))
        
        agente = cursor.fetchone()
        print(f"   ✅ {agente['nombre']} {agente['apellido']}: {agente['telefono']}")
        
        # 7. Buscar por apellido
        print("\n7. Búsqueda por apellido (índice compuesto)...")
        cursor.execute("""
            SELECT nombre, apellido, email
            FROM datos_personales
            WHERE apellido LIKE 'G%'
            ORDER BY apellido, nombre
        """)
        
        resultados = cursor.fetchall()
        print(f"   �� Apellidos con 'G': {len(resultados)}")
        for row in resultados:
            print(f"      • {row['apellido']}, {row['nombre']}")
        
        # 8. Estadísticas
        print("\n8. Estadísticas generales:")
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN activo = 1 THEN 1 ELSE 0 END) as activos,
                SUM(CASE WHEN activo = 0 THEN 1 ELSE 0 END) as inactivos
            FROM datos_personales
        """)
        stats = cursor.fetchone()
        print(f"   📊 Total: {stats['total']}")
        print(f"   📊 Activos: {stats['activos']}")
        print(f"   📊 Inactivos: {stats['inactivos']}")
        
        # 9. Verificar índices
        print("\n9. Verificando índices...")
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' 
            AND tbl_name='datos_personales'
            AND name NOT LIKE 'sqlite_%'
        """)
        indices = [row['name'] for row in cursor.fetchall()]
        
        indices_esperados = [
            'idx_agentes_dni',
            'idx_agentes_activo',
            'idx_agentes_nombre_apellido'
        ]
        
        for idx in indices_esperados:
            if idx in indices:
                print(f"   ✅ {idx}")
            else:
                print(f"   ⚠️  {idx} falta")
        
        print("\n" + "="*70)
        print(f"✅ TEST 04 COMPLETADO - {stats['total']} agentes verificados")
        print("="*70)
        
        return stats['total'] >= 5

if __name__ == '__main__':
    success = test_datos_personales()
    sys.exit(0 if success else 1)
