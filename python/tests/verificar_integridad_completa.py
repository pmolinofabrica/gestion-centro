#!/usr/bin/env python3
"""
Verificación de Integridad Completa del Sistema
Verifica que nada se haya roto durante las pruebas
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_connection_helper import get_connection

def verificar_integridad():
    print("="*70)
    print("VERIFICACIÓN DE INTEGRIDAD COMPLETA DEL SISTEMA")
    print("="*70)
    
    errores = []
    warnings = []
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # ============================================================
        # 1. VERIFICAR ESTRUCTURA DE TABLAS
        # ============================================================
        print("\n[1] ESTRUCTURA DE TABLAS")
        print("-"*70)
        
        tablas_esperadas = [
            'dispositivos', 'dias', 'turnos', 'datos_personales', 
            'planificacion', 'capacitaciones', 'capacitaciones_dispositivos',
            'capacitaciones_participantes', 'convocatoria', 'convocatoria_historial',
            'cambio_transaccion', 'cambio_transaccion_detalle', 'cambio_validacion',
            'descansos', 'disponibilidad', 'inasistencias', 'certificados',
            'menu', 'saldos', 'system_errors', 'error_patterns', 'configuracion'
        ]
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tablas_existentes = [row['name'] for row in cursor.fetchall()]
        
        for tabla in tablas_esperadas:
            if tabla in tablas_existentes:
                print(f"   ✅ {tabla}")
            else:
                print(f"   ❌ {tabla} FALTA")
                errores.append(f"Tabla {tabla} no existe")
        
        # Tablas extra (no esperadas)
        for tabla in tablas_existentes:
            if tabla not in tablas_esperadas and not tabla.startswith('vista_'):
                print(f"   ⚠️  {tabla} (extra)")
                warnings.append(f"Tabla extra: {tabla}")
        
        # ============================================================
        # 2. VERIFICAR SCHEMA DE CONVOCATORIA
        # ============================================================
        print("\n[2] SCHEMA DE CONVOCATORIA")
        print("-"*70)
        
        cursor.execute("""
            SELECT sql FROM sqlite_master WHERE name='convocatoria'
        """)
        schema = cursor.fetchone()
        
        if schema:
            schema_sql = schema['sql']
            
            # Verificar id_turno
            if 'id_turno INTEGER NOT NULL' in schema_sql:
                print("   ✅ id_turno INTEGER NOT NULL (estado original)")
            elif 'id_turno INTEGER,' in schema_sql or 'id_turno INTEGER\n' in schema_sql:
                print("   ⚠️  id_turno INTEGER (permite NULL - migración aplicada)")
                warnings.append("Tabla convocatoria fue modificada (permite NULL)")
            else:
                print("   ❌ id_turno en estado desconocido")
                errores.append("Schema de convocatoria alterado")
            
            # Verificar id_plani
            if 'id_plani INTEGER NOT NULL' in schema_sql:
                print("   ✅ id_plani INTEGER NOT NULL (estado original)")
            elif 'id_plani INTEGER,' in schema_sql or 'id_plani INTEGER\n' in schema_sql:
                print("   ⚠️  id_plani INTEGER (permite NULL)")
                warnings.append("id_plani permite NULL")
        else:
            print("   ❌ Tabla convocatoria no encontrada")
            errores.append("Tabla convocatoria no existe")
        
        # ============================================================
        # 3. VERIFICAR TRIGGERS
        # ============================================================
        print("\n[3] TRIGGERS")
        print("-"*70)
        
        triggers_esperados = {
            'convocatoria': [
                'trg_prevent_duplicate_vigente',
                'trg_update_fecha_modificacion',
                'trg_registrar_historial_cambio',
                'trg_saldo_insert_convocatoria',
                'trg_saldo_update_convocatoria',
                'trg_saldo_delete_convocatoria'
            ],
            'descansos': ['trg_asignar_descanso_aprobado'],
            'inasistencias': [
                'trg_auto_requiere_certificado',
                'trg_update_requiere_certificado'
            ],
            'certificados': [
                'trg_certificado_aprobado',
                'trg_certificado_rechazado'
            ],
            'system_errors': [
                'trg_detectar_patron_error',
                'trg_error_resuelto'
            ]
        }
        
        cursor.execute("""
            SELECT tbl_name, name FROM sqlite_master 
            WHERE type='trigger'
            ORDER BY tbl_name, name
        """)
        triggers_existentes = {}
        for row in cursor.fetchall():
            tabla = row['tbl_name']
            if tabla not in triggers_existentes:
                triggers_existentes[tabla] = []
            triggers_existentes[tabla].append(row['name'])
        
        for tabla, triggers in triggers_esperados.items():
            print(f"\n   Tabla: {tabla}")
            for trigger in triggers:
                if tabla in triggers_existentes and trigger in triggers_existentes[tabla]:
                    print(f"      ✅ {trigger}")
                else:
                    print(f"      ❌ {trigger} FALTA")
                    errores.append(f"Trigger {trigger} no existe en {tabla}")
        
        # ============================================================
        # 4. VERIFICAR VISTAS
        # ============================================================
        print("\n[4] VISTAS ANALÍTICAS")
        print("-"*70)
        
        vistas_esperadas = [
            'vista_convocatorias_activas',
            'vista_saldos_actuales',
            'vista_dispositivos_ocupacion',
            'vista_agentes_capacitados',
            'vista_cambios_pendientes',
            'vista_inasistencias_mes',
            'vista_errores_recientes',
            'vista_patrones_errores',
            'vista_salud_sistema',
            'vista_errores_por_componente',
            'vista_errores_timeline'
        ]
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='view'
            ORDER BY name
        """)
        vistas_existentes = [row['name'] for row in cursor.fetchall()]
        
        for vista in vistas_esperadas:
            if vista in vistas_existentes:
                print(f"   ✅ {vista}")
            else:
                print(f"   ❌ {vista} FALTA")
                errores.append(f"Vista {vista} no existe")
        
        # Vistas extra
        for vista in vistas_existentes:
            if vista not in vistas_esperadas:
                print(f"   ⚠️  {vista} (extra)")
        
        # ============================================================
        # 5. VERIFICAR INTEGRIDAD REFERENCIAL
        # ============================================================
        print("\n[5] INTEGRIDAD REFERENCIAL")
        print("-"*70)
        
        cursor.execute("PRAGMA foreign_key_check")
        fk_errors = cursor.fetchall()
        
        if len(fk_errors) == 0:
            print("   ✅ Sin errores de Foreign Keys")
        else:
            print(f"   ❌ {len(fk_errors)} errores de Foreign Keys:")
            for error in fk_errors[:5]:
                print(f"      - {error}")
                errores.append(f"FK error: {error}")
        
        # ============================================================
        # 6. VERIFICAR INTEGRIDAD DE BASE DE DATOS
        # ============================================================
        print("\n[6] INTEGRIDAD DE BASE DE DATOS")
        print("-"*70)
        
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        
        if integrity == 'ok':
            print("   ✅ Base de datos íntegra")
        else:
            print(f"   ❌ Problemas de integridad: {integrity}")
            errores.append(f"Integrity check: {integrity}")
        
        # ============================================================
        # 7. VERIFICAR DATOS EN TABLAS PRINCIPALES
        # ============================================================
        print("\n[7] DATOS EN TABLAS")
        print("-"*70)
        
        tablas_datos = [
            'dispositivos', 'dias', 'turnos', 'datos_personales',
            'planificacion', 'convocatoria', 'descansos', 'saldos'
        ]
        
        for tabla in tablas_datos:
            try:
                cursor.execute(f"SELECT COUNT(*) as n FROM {tabla}")
                count = cursor.fetchone()['n']
                print(f"   📊 {tabla}: {count} registro(s)")
            except Exception as e:
                print(f"   ❌ {tabla}: Error al contar - {e}")
                errores.append(f"Error en tabla {tabla}: {e}")
        
        # ============================================================
        # 8. VERIFICAR FOREIGN KEYS ACTIVADAS
        # ============================================================
        print("\n[8] CONFIGURACIÓN")
        print("-"*70)
        
        cursor.execute("PRAGMA foreign_keys")
        fk_status = cursor.fetchone()[0]
        
        if fk_status == 1:
            print("   ✅ Foreign Keys: ACTIVADAS")
        else:
            print("   ⚠️  Foreign Keys: DESACTIVADAS")
            warnings.append("Foreign Keys desactivadas")
        
        # ============================================================
        # 9. VERIFICAR CONSTRAINT DE TURNOS
        # ============================================================
        print("\n[9] CONSTRAINTS CRÍTICOS")
        print("-"*70)
        
        cursor.execute("""
            SELECT sql FROM sqlite_master WHERE name='turnos'
        """)
        turnos_schema = cursor.fetchone()['sql']
        
        if 'chk_horas CHECK (cant_horas > 0' in turnos_schema:
            print("   ✅ Constraint chk_horas intacto (cant_horas > 0)")
        else:
            print("   ❌ Constraint chk_horas modificado o ausente")
            errores.append("Constraint chk_horas alterado")
        
        # ============================================================
        # 10. PRUEBA FUNCIONAL BÁSICA
        # ============================================================
        print("\n[10] PRUEBA FUNCIONAL")
        print("-"*70)
        
        try:
            # Insertar dispositivo de prueba
            cursor.execute("""
                INSERT INTO dispositivos (nombre_dispositivo, piso_dispositivo)
                VALUES ('TEST_VERIFICACION', 0)
            """)
            test_id = cursor.lastrowid
            print("   ✅ INSERT funciona")
            
            # Leer
            cursor.execute("""
                SELECT * FROM dispositivos WHERE id_dispositivo = ?
            """, (test_id,))
            if cursor.fetchone():
                print("   ✅ SELECT funciona")
            
            # Actualizar
            cursor.execute("""
                UPDATE dispositivos SET piso_dispositivo = 1 
                WHERE id_dispositivo = ?
            """, (test_id,))
            print("   ✅ UPDATE funciona")
            
            # Eliminar
            cursor.execute("""
                DELETE FROM dispositivos WHERE id_dispositivo = ?
            """, (test_id,))
            print("   ✅ DELETE funciona")
            
            conn.rollback()  # No guardar cambios de prueba
            
        except Exception as e:
            print(f"   ❌ Error en operaciones: {e}")
            errores.append(f"Error funcional: {e}")
        
        # ============================================================
        # RESUMEN FINAL
        # ============================================================
        print("\n" + "="*70)
        print("RESUMEN")
        print("="*70)
        
        if len(errores) == 0 and len(warnings) == 0:
            print("\n✅ SISTEMA COMPLETAMENTE ÍNTEGRO")
            print("   No se detectaron problemas.")
            print("   El sistema está funcionando correctamente.")
            return True
        
        elif len(errores) == 0 and len(warnings) > 0:
            print(f"\n⚠️  SISTEMA FUNCIONAL CON {len(warnings)} ADVERTENCIA(S)")
            print("\nAdvertencias detectadas:")
            for w in warnings:
                print(f"   - {w}")
            print("\nEl sistema funciona pero hay cambios respecto al estado original.")
            return True
        
        else:
            print(f"\n❌ SISTEMA CON {len(errores)} ERROR(ES)")
            print("\nErrores críticos detectados:")
            for e in errores:
                print(f"   - {e}")
            
            if len(warnings) > 0:
                print(f"\nAdemás hay {len(warnings)} advertencia(s):")
                for w in warnings:
                    print(f"   - {w}")
            
            print("\n⚠️  RECOMENDACIÓN: Restaurar desde backup")
            print("   cp data/gestion_rrhh_PRE_MIGRACION.db data/gestion_rrhh.db")
            return False

if __name__ == '__main__':
    try:
        success = verificar_integridad()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR FATAL EN VERIFICACIÓN: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
