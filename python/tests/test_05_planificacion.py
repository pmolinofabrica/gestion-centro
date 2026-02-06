#!/usr/bin/env python3
"""
Test 05: Tabla planificacion
Verifica demanda de personal por día/turno
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_connection_helper import get_connection

def test_planificacion():
    print("="*70)
    print("TEST 05: TABLA PLANIFICACIÓN")
    print("="*70)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Verificar que existen días y turnos
        print("\n1. Verificando prerequisitos...")
        
        cursor.execute("SELECT COUNT(*) as n FROM dias")
        dias_count = cursor.fetchone()['n']
        print(f"   📅 Días disponibles: {dias_count}")
        
        cursor.execute("SELECT COUNT(*) as n FROM turnos")
        turnos_count = cursor.fetchone()['n']
        print(f"   ⏰ Turnos disponibles: {turnos_count}")
        
        if dias_count == 0 or turnos_count == 0:
            print("   ❌ Faltan días o turnos para crear planificación")
            return False
        
        # 2. Crear planificación para próximos 7 días
        print("\n2. Creando planificación (próximos 7 días)...")
        
        # Obtener primeros 7 días
        cursor.execute("""
            SELECT id_dia, fecha, numero_dia_semana 
            FROM dias 
            ORDER BY fecha 
            LIMIT 7
        """)
        dias = cursor.fetchall()
        
        # Obtener turnos de mañana y tarde
        cursor.execute("""
            SELECT id_turno, numero_dia_semana, tipo_turno
            FROM turnos
            WHERE tipo_turno IN ('mañana', 'tarde')
            ORDER BY numero_dia_semana, tipo_turno
        """)
        turnos = cursor.fetchall()
        
        count_planificacion = 0
        for dia in dias:
            # Buscar turnos para este día de la semana
            turnos_dia = [t for t in turnos if t['numero_dia_semana'] == dia['numero_dia_semana']]
            
            for turno in turnos_dia:
                # Insertar planificación
                cant_residentes = 3  # 3 residentes por turno
                cant_visitantes = 15 if turno['tipo_turno'] == 'mañana' else 20
                
                try:
                    cursor.execute("""
                        INSERT INTO planificacion 
                        (id_dia, id_turno, cant_residentes_plan, cant_visit, plani_notas)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        dia['id_dia'],
                        turno['id_turno'],
                        cant_residentes,
                        cant_visitantes,
                        f"Planificación {turno['tipo_turno']} {dia['fecha']}"
                    ))
                    count_planificacion += 1
                except Exception as e:
                    if 'UNIQUE' not in str(e):
                        print(f"   ⚠️  Error: {e}")
        
        print(f"   ✅ {count_planificacion} planificaciones creadas")
        
        # 3. Verificar constraint UNIQUE (día + turno)
        print("\n3. Probando UNIQUE en (id_dia, id_turno)...")
        cursor.execute("SELECT id_dia, id_turno FROM planificacion LIMIT 1")
        first = cursor.fetchone()
        
        try:
            cursor.execute("""
                INSERT INTO planificacion 
                (id_dia, id_turno, cant_residentes_plan, cant_visit)
                VALUES (?, ?, 3, 10)
            """, (first['id_dia'], first['id_turno']))
            print("   ❌ UNIQUE NO funcionó (permitió duplicado)")
            return False
        except Exception as e:
            if 'UNIQUE' in str(e) or 'uq_plani_dia_turno' in str(e):
                print("   ✅ UNIQUE en (id_dia, id_turno) funciona")
            else:
                print(f"   ⚠️  Error inesperado: {e}")
        
        # 4. Verificar constraint CHECK cant_residentes > 0
        print("\n4. Probando CHECK cant_residentes > 0...")
        try:
            cursor.execute("""
                INSERT INTO planificacion 
                (id_dia, id_turno, cant_residentes_plan, cant_visit)
                SELECT 
                    (SELECT id_dia FROM dias ORDER BY fecha LIMIT 1 OFFSET 10),
                    (SELECT id_turno FROM turnos LIMIT 1),
                    0, 10
            """)
            print("   ❌ CHECK NO funcionó (permitió cant_residentes = 0)")
            return False
        except Exception as e:
            if 'chk_cant_residentes' in str(e) or 'CHECK constraint' in str(e):
                print("   ✅ Constraint chk_cant_residentes funciona")
            else:
                print(f"   ⚠️  Error inesperado: {e}")
        
        # 5. Verificar constraint CHECK cant_visit >= 0
        print("\n5. Probando CHECK cant_visit >= 0...")
        try:
            cursor.execute("""
                INSERT INTO planificacion 
                (id_dia, id_turno, cant_residentes_plan, cant_visit)
                SELECT 
                    (SELECT id_dia FROM dias ORDER BY fecha LIMIT 1 OFFSET 11),
                    (SELECT id_turno FROM turnos LIMIT 1),
                    3, -5
            """)
            print("   ❌ CHECK NO funcionó (permitió cant_visit negativo)")
            return False
        except Exception as e:
            if 'chk_cant_visit' in str(e) or 'CHECK constraint' in str(e):
                print("   ✅ Constraint chk_cant_visit funciona")
            else:
                print(f"   ⚠️  Error inesperado: {e}")
        
        # 6. Consultar planificación con JOIN
        print("\n6. Consultando planificación (con JOINs)...")
        cursor.execute("""
            SELECT 
                d.fecha,
                CASE d.numero_dia_semana
                    WHEN 0 THEN 'Lun'
                    WHEN 1 THEN 'Mar'
                    WHEN 2 THEN 'Mié'
                    WHEN 3 THEN 'Jue'
                    WHEN 4 THEN 'Vie'
                    WHEN 5 THEN 'Sáb'
                    WHEN 6 THEN 'Dom'
                END as dia_semana,
                t.tipo_turno,
                t.hora_inicio,
                p.cant_residentes_plan,
                p.cant_visit
            FROM planificacion p
            JOIN dias d ON p.id_dia = d.id_dia
            JOIN turnos t ON p.id_turno = t.id_turno
            ORDER BY d.fecha, t.hora_inicio
            LIMIT 10
        """)
        
        print("   📊 Primeras 10 planificaciones:")
        for row in cursor.fetchall():
            print(f"      {row['fecha']} ({row['dia_semana']}) {row['tipo_turno']}: "
                  f"{row['cant_residentes_plan']} residentes, {row['cant_visit']} visitantes")
        
        # 7. Actualizar planificación
        print("\n7. Actualizando planificación...")
        cursor.execute("""
            UPDATE planificacion
            SET cant_residentes_plan = 4, cant_visit = 30
            WHERE id_plani = (SELECT MIN(id_plani) FROM planificacion)
        """)
        
        cursor.execute("""
            SELECT 
                p.cant_residentes_plan, p.cant_visit,
                d.fecha, t.tipo_turno
            FROM planificacion p
            JOIN dias d ON p.id_dia = d.id_dia
            JOIN turnos t ON p.id_turno = t.id_turno
            WHERE p.id_plani = (SELECT MIN(id_plani) FROM planificacion)
        """)
        updated = cursor.fetchone()
        print(f"   ✅ Actualizado: {updated['fecha']} {updated['tipo_turno']} "
              f"-> {updated['cant_residentes_plan']} residentes, {updated['cant_visit']} visitantes")
        
        # 8. Estadísticas
        print("\n8. Estadísticas de planificación:")
        cursor.execute("""
            SELECT 
                COUNT(*) as total_planificaciones,
                SUM(cant_residentes_plan) as total_residentes_necesarios,
                SUM(cant_visit) as total_visitantes_esperados,
                AVG(cant_residentes_plan) as promedio_residentes,
                AVG(cant_visit) as promedio_visitantes
            FROM planificacion
        """)
        stats = cursor.fetchone()
        print(f"   📊 Total planificaciones: {stats['total_planificaciones']}")
        print(f"   📊 Total residentes necesarios: {stats['total_residentes_necesarios']}")
        print(f"   📊 Total visitantes esperados: {stats['total_visitantes_esperados']}")
        print(f"   📊 Promedio residentes/turno: {stats['promedio_residentes']:.1f}")
        print(f"   📊 Promedio visitantes/turno: {stats['promedio_visitantes']:.1f}")
        
        # 9. Verificar Foreign Keys
        print("\n9. Verificando Foreign Keys...")
        
        # Intentar insertar con día inexistente
        try:
            cursor.execute("""
                INSERT INTO planificacion 
                (id_dia, id_turno, cant_residentes_plan, cant_visit)
                VALUES (99999, 1, 3, 10)
            """)
            print("   ❌ FK a dias NO funcionó")
            return False
        except Exception as e:
            if 'FOREIGN KEY' in str(e) or 'fk_plani_dia' in str(e):
                print("   ✅ FK a dias funciona")
            else:
                print(f"   ⚠️  Error: {e}")
        
        # 10. Verificar índices
        print("\n10. Verificando índices...")
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' 
            AND tbl_name='planificacion'
            AND name NOT LIKE 'sqlite_%'
        """)
        indices = [row['name'] for row in cursor.fetchall()]
        
        indices_esperados = ['idx_plani_dia', 'idx_plani_turno']
        for idx in indices_esperados:
            if idx in indices:
                print(f"   ✅ {idx}")
            else:
                print(f"   ⚠️  {idx} falta")
        
        print("\n" + "="*70)
        print(f"✅ TEST 05 COMPLETADO - {stats['total_planificaciones']} planificaciones verificadas")
        print("="*70)
        
        return stats['total_planificaciones'] > 0

if __name__ == '__main__':
    success = test_planificacion()
    sys.exit(0 if success else 1)
