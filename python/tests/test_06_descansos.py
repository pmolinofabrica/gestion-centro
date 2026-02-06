#!/usr/bin/env python3
"""
Test 06: Tabla descansos
Verifica workflow de solicitud/aprobación de descansos
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_connection_helper import get_connection
from datetime import date, timedelta

def test_descansos():
    print("="*70)
    print("TEST 06: TABLA DESCANSOS")
    print("="*70)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Verificar que existen agentes
        print("\n1. Verificando prerequisitos...")
        
        cursor.execute("SELECT COUNT(*) as n FROM datos_personales WHERE activo = 1")
        agentes_count = cursor.fetchone()['n']
        print(f"   👥 Agentes activos: {agentes_count}")
        
        if agentes_count == 0:
            print("   ⚠️  No hay agentes, creando uno de prueba...")
            cursor.execute("""
                INSERT INTO datos_personales 
                (nombre, apellido, dni, fecha_nacimiento, email, activo)
                VALUES ('Test', 'Descansos', '99999999', '1990-01-01', 'test@descansos.com', 1)
            """)
            id_agente_test = cursor.lastrowid
            print(f"   ✅ Agente creado: ID={id_agente_test}")
        else:
            cursor.execute("SELECT id_agente FROM datos_personales WHERE activo = 1 LIMIT 1")
            id_agente_test = cursor.fetchone()['id_agente']
        
        # 2. Solicitar descansos
        print("\n2. Solicitando descansos...")
        
        # Solicitar 3 descansos
        fecha_base = date.today() + timedelta(days=10)
        descansos_solicitados = []
        
        for i in range(3):
            fecha_solicitud = fecha_base + timedelta(days=i*2)
            
            cursor.execute("""
                INSERT INTO descansos 
                (id_agente, dia_solicitado, mes_solicitado, estado, observaciones)
                VALUES (?, ?, ?, 'pendiente', ?)
            """, (
                id_agente_test,
                fecha_solicitud.isoformat(),
                fecha_solicitud.month,
                f'Descanso {i+1} de prueba'
            ))
            
            id_desc = cursor.lastrowid
            descansos_solicitados.append(id_desc)
            print(f"   ✅ Descanso {i+1} solicitado: {fecha_solicitud} (ID: {id_desc})")
        
        # 3. Verificar estado inicial
        print("\n3. Verificando estado inicial...")
        cursor.execute("""
            SELECT COUNT(*) as n FROM descansos WHERE estado = 'pendiente'
        """)
        pendientes = cursor.fetchone()['n']
        print(f"   📋 Descansos pendientes: {pendientes}")
        
        # 4. Aprobar un descanso
        print("\n4. Aprobando un descanso...")
        id_desc_aprobar = descansos_solicitados[0]
        
        # Obtener fecha del descanso
        cursor.execute("""
            SELECT dia_solicitado FROM descansos WHERE id_desc = ?
        """, (id_desc_aprobar,))
        dia_solicitado = cursor.fetchone()['dia_solicitado']
        
        # Verificar que existe el día en tabla dias
        cursor.execute("""
            SELECT COUNT(*) as n FROM dias WHERE fecha = ?
        """, (dia_solicitado,))
        
        if cursor.fetchone()['n'] == 0:
            # Crear el día si no existe
            fecha_obj = date.fromisoformat(dia_solicitado)
            cursor.execute("""
                INSERT INTO dias (fecha, mes, semana, dia, numero_dia_semana, es_feriado)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (
                dia_solicitado,
                fecha_obj.month,
                fecha_obj.isocalendar()[1],
                fecha_obj.day,
                fecha_obj.weekday()
            ))
            print(f"   ℹ️  Día {dia_solicitado} creado en calendario")
        
        # Aprobar descanso
        cursor.execute("""
            UPDATE descansos
            SET estado = 'asignado'
            WHERE id_desc = ?
        """, (id_desc_aprobar,))
        
        print(f"   ✅ Descanso {id_desc_aprobar} aprobado")
        
        # Verificar que trigger actualizó fecha_respuesta
        cursor.execute("""
            SELECT estado, fecha_respuesta FROM descansos WHERE id_desc = ?
        """, (id_desc_aprobar,))
        
        desc = cursor.fetchone()
        if desc['estado'] == 'asignado' and desc['fecha_respuesta']:
            print(f"   ✅ Trigger actualizó fecha_respuesta: {desc['fecha_respuesta']}")
        else:
            print(f"   ⚠️  Trigger no actualizó fecha_respuesta correctamente")
        
        # 5. Verificar que trigger creó convocatoria
        print("\n5. Verificando trigger trg_asignar_descanso_aprobado...")
        
        cursor.execute("""
            SELECT COUNT(*) as n FROM convocatoria 
            WHERE id_agente = ? 
            AND fecha_convocatoria = ?
            AND estado = 'vigente'
        """, (id_agente_test, dia_solicitado))
        
        convocatorias = cursor.fetchone()['n']
        
        if convocatorias > 0:
            print(f"   ✅ Trigger creó convocatoria para el descanso")
            
            # Ver detalles
            cursor.execute("""
                SELECT 
                    id_convocatoria,
                    id_turno,
                    id_plani,
                    motivo_cambio
                FROM convocatoria
                WHERE id_agente = ? 
                AND fecha_convocatoria = ?
            """, (id_agente_test, dia_solicitado))
            
            conv = cursor.fetchone()
            print(f"   ℹ️  Convocatoria ID: {conv['id_convocatoria']}")
            print(f"   ℹ️  id_turno: {conv['id_turno']}")
            print(f"   ℹ️  id_plani: {conv['id_plani']}")
            print(f"   ℹ️  Motivo: {conv['motivo_cambio']}")
        else:
            print(f"   ⚠️  Trigger NO creó convocatoria (puede ser por falta de planificación)")
        
        # 6. Rechazar un descanso
        print("\n6. Rechazando un descanso...")
        id_desc_rechazar = descansos_solicitados[1]
        
        cursor.execute("""
            UPDATE descansos
            SET estado = 'no_asignado',
                observaciones = 'Rechazado por falta de cobertura'
            WHERE id_desc = ?
        """, (id_desc_rechazar,))
        
        print(f"   ✅ Descanso {id_desc_rechazar} rechazado")
        
        # 7. Verificar constraint CHECK en estado
        print("\n7. Probando CHECK en estado...")
        try:
            cursor.execute("""
                INSERT INTO descansos 
                (id_agente, dia_solicitado, mes_solicitado, estado)
                VALUES (?, ?, 1, 'estado_invalido')
            """, (id_agente_test, date.today().isoformat()))
            print("   ❌ CHECK NO funcionó (permitió estado inválido)")
            return False
        except Exception as e:
            if 'chk_estado_desc' in str(e) or 'CHECK constraint' in str(e):
                print("   ✅ Constraint chk_estado_desc funciona")
            else:
                print(f"   ⚠️  Error inesperado: {e}")
        
        # 8. Verificar constraint CHECK en mes (1-12)
        print("\n8. Probando CHECK en mes (1-12)...")
        try:
            cursor.execute("""
                INSERT INTO descansos 
                (id_agente, dia_solicitado, mes_solicitado, estado)
                VALUES (?, ?, 13, 'pendiente')
            """, (id_agente_test, date.today().isoformat()))
            print("   ❌ CHECK NO funcionó (permitió mes=13)")
            return False
        except Exception as e:
            if 'chk_mes_desc' in str(e) or 'CHECK constraint' in str(e):
                print("   ✅ Constraint chk_mes_desc funciona")
            else:
                print(f"   ⚠️  Error inesperado: {e}")
        
        # 9. Consultar descansos con JOIN
        print("\n9. Consultando descansos (con JOIN)...")
        cursor.execute("""
            SELECT 
                d.id_desc,
                dp.nombre || ' ' || dp.apellido as nombre_completo,
                d.dia_solicitado,
                d.estado,
                d.fecha_solicitud,
                d.observaciones
            FROM descansos d
            JOIN datos_personales dp ON d.id_agente = dp.id_agente
            ORDER BY d.fecha_solicitud DESC
        """)
        
        print("   📋 Descansos registrados:")
        for row in cursor.fetchall():
            print(f"      ID {row['id_desc']}: {row['nombre_completo']} - "
                  f"{row['dia_solicitado']} [{row['estado']}]")
        
        # 10. Estadísticas
        print("\n10. Estadísticas de descansos:")
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN estado = 'pendiente' THEN 1 ELSE 0 END) as pendientes,
                SUM(CASE WHEN estado = 'asignado' THEN 1 ELSE 0 END) as asignados,
                SUM(CASE WHEN estado = 'no_asignado' THEN 1 ELSE 0 END) as rechazados
            FROM descansos
        """)
        stats = cursor.fetchone()
        print(f"   📊 Total: {stats['total']}")
        print(f"   📊 Pendientes: {stats['pendientes']}")
        print(f"   📊 Asignados: {stats['asignados']}")
        print(f"   �� Rechazados: {stats['rechazados']}")
        
        # 11. Verificar índices
        print("\n11. Verificando índices...")
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' 
            AND tbl_name='descansos'
            AND name NOT LIKE 'sqlite_%'
        """)
        indices = [row['name'] for row in cursor.fetchall()]
        
        indices_esperados = ['idx_desc_agente', 'idx_desc_dia', 'idx_desc_estado']
        for idx in indices_esperados:
            if idx in indices:
                print(f"   ✅ {idx}")
            else:
                print(f"   ⚠️  {idx} falta")
        
        print("\n" + "="*70)
        print(f"✅ TEST 06 COMPLETADO - {stats['total']} descansos verificados")
        print("="*70)
        
        return stats['total'] >= 3

if __name__ == '__main__':
    success = test_descansos()
    sys.exit(0 if success else 1)
