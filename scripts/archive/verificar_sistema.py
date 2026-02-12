#!/usr/bin/env python3
"""
Script de Verificación Rápida - Sistema RRHH v2.0
Verifica que la instalación sea correcta y el sistema esté operativo
"""

import sqlite3
import sys
from datetime import datetime

def print_header(text):
    """Imprime un encabezado formateado"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_check(passed, message, expected=None, found=None):
    """Imprime resultado de una verificación"""
    symbol = "✓" if passed else "✗"
    status = "OK" if passed else "FALLO"
    
    if expected and found:
        print(f"  {symbol} {message}: {status} (esperado: {expected}, encontrado: {found})")
    else:
        print(f"  {symbol} {message}: {status}")
    
    return passed

def verificar_sistema(db_path='gestion_rrhh.db'):
    """Verificación completa del sistema"""
    
    print_header("VERIFICACIÓN SISTEMA RRHH v2.0 FINAL")
    print(f"Base de datos: {db_path}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        all_passed = True
        
        # ================================================================
        # 1. VERIFICAR ESTRUCTURA
        # ================================================================
        print_header("1. ESTRUCTURA DE BASE DE DATOS")
        
        # Tablas
        cursor.execute("SELECT COUNT(*) as n FROM sqlite_master WHERE type='table'")
        tablas = cursor.fetchone()['n']
        all_passed &= print_check(
            tablas == 19, 
            "Tablas creadas", 
            expected=19, 
            found=tablas
        )
        
        # Vistas
        cursor.execute("SELECT COUNT(*) as n FROM sqlite_master WHERE type='view'")
        vistas = cursor.fetchone()['n']
        all_passed &= print_check(
            vistas == 11, 
            "Vistas creadas", 
            expected=11, 
            found=vistas
        )
        
        # Triggers
        cursor.execute("SELECT COUNT(*) as n FROM sqlite_master WHERE type='trigger'")
        triggers = cursor.fetchone()['n']
        all_passed &= print_check(
            triggers == 13, 
            "Triggers creados", 
            expected=13, 
            found=triggers
        )
        
        # Índices
        cursor.execute("""
            SELECT COUNT(*) as n FROM sqlite_master 
            WHERE type='index' AND name NOT LIKE 'sqlite_%'
        """)
        indices = cursor.fetchone()['n']
        all_passed &= print_check(
            indices >= 60, 
            "Índices creados", 
            expected="60+", 
            found=indices
        )
        
        # ================================================================
        # 2. VERIFICAR DATOS INICIALES
        # ================================================================
        print_header("2. CONFIGURACIÓN INICIAL")
        
        # Configuración
        cursor.execute("SELECT COUNT(*) as n FROM configuracion")
        configs = cursor.fetchone()['n']
        all_passed &= print_check(
            configs == 8, 
            "Configuraciones cargadas", 
            expected=8, 
            found=configs
        )
        
        # Foreign Keys
        cursor.execute("PRAGMA foreign_keys")
        fk_status = cursor.fetchone()[0]
        all_passed &= print_check(
            fk_status == 1, 
            "Foreign Keys activadas"
        )
        
        # ================================================================
        # 3. VERIFICAR TABLAS ESPECÍFICAS
        # ================================================================
        print_header("3. TABLAS CRÍTICAS")
        
        tablas_criticas = [
            'datos_personales',
            'dias',
            'turnos',
            'convocatoria',
            'capacitaciones_participantes',
            'saldos',
            'system_errors',
            'configuracion'
        ]
        
        for tabla in tablas_criticas:
            cursor.execute(f"""
                SELECT COUNT(*) as n FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (tabla,))
            exists = cursor.fetchone()['n'] == 1
            all_passed &= print_check(exists, f"Tabla '{tabla}'")
        
        # ================================================================
        # 4. VERIFICAR TRIGGERS
        # ================================================================
        print_header("4. TRIGGERS AUTOMÁTICOS")
        
        triggers_criticos = [
            'trg_prevent_duplicate_vigente',
            'trg_saldo_insert_convocatoria',
            'trg_saldo_update_convocatoria',
            'trg_saldo_delete_convocatoria',
            'trg_detectar_patron_error',
            'trg_certificado_aprobado'
        ]
        
        for trigger in triggers_criticos:
            cursor.execute(f"""
                SELECT COUNT(*) as n FROM sqlite_master 
                WHERE type='trigger' AND name=?
            """, (trigger,))
            exists = cursor.fetchone()['n'] == 1
            all_passed &= print_check(exists, f"Trigger '{trigger}'")
        
        # ================================================================
        # 5. VERIFICAR VISTAS
        # ================================================================
        print_header("5. VISTAS ANALÍTICAS")
        
        vistas_criticas = [
            'vista_convocatorias_activas',
            'vista_saldos_actuales',
            'vista_salud_sistema',
            'vista_errores_recientes',
            'vista_patrones_errores',
            'vista_agentes_capacitados'
        ]
        
        for vista in vistas_criticas:
            cursor.execute(f"""
                SELECT COUNT(*) as n FROM sqlite_master 
                WHERE type='view' AND name=?
            """, (vista,))
            exists = cursor.fetchone()['n'] == 1
            all_passed &= print_check(exists, f"Vista '{vista}'")
        
        # ================================================================
        # 6. VERIFICAR FUNCIONAMIENTO
        # ================================================================
        print_header("6. PRUEBAS FUNCIONALES")
        
        # Vista salud sistema
        try:
            cursor.execute("SELECT estado_sistema, fecha_reporte FROM vista_salud_sistema")
            salud = cursor.fetchone()
            estado = salud['estado_sistema']
            print_check(True, f"Vista salud sistema funciona - Estado: {estado}")
        except Exception as e:
            all_passed &= print_check(False, f"Vista salud sistema - Error: {e}")
        
        # Configuración accesible
        try:
            cursor.execute("SELECT valor FROM configuracion WHERE clave='sistema_version'")
            version = cursor.fetchone()['valor']
            print_check(True, f"Configuración accesible - Versión: {version}")
        except Exception as e:
            all_passed &= print_check(False, f"Configuración - Error: {e}")
        
        # ================================================================
        # 7. INTEGRIDAD
        # ================================================================
        print_header("7. INTEGRIDAD DE DATOS")
        
        # Integrity check
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        all_passed &= print_check(
            integrity == 'ok', 
            f"Integridad de BD: {integrity}"
        )
        
        # Foreign key check
        cursor.execute("PRAGMA foreign_key_check")
        fk_errors = cursor.fetchall()
        all_passed &= print_check(
            len(fk_errors) == 0, 
            f"Consistencia FK: {len(fk_errors)} errores"
        )
        
        # ================================================================
        # RESULTADO FINAL
        # ================================================================
        print_header("RESULTADO FINAL")
        
        if all_passed:
            print("\n  🎉 ¡SISTEMA VERIFICADO EXITOSAMENTE!")
            print("  ✅ Todos los componentes están operativos")
            print("  ✅ El sistema está listo para usar")
            print("\n  Próximos pasos:")
            print("    1. Cargar datos iniciales (dispositivos, días, turnos)")
            print("    2. Agregar personal")
            print("    3. Crear convocatorias")
            print("    4. Configurar backups automáticos")
        else:
            print("\n  ⚠️  VERIFICACIÓN INCOMPLETA")
            print("  ❌ Algunos componentes tienen problemas")
            print("  📋 Revisar los errores marcados arriba")
            print("\n  Soluciones:")
            print("    1. Re-ejecutar: sqlite3 gestion_rrhh.db < schema_final_completo.sql")
            print("    2. Verificar permisos del archivo")
            print("    3. Revisar log de errores")
        
        print("\n" + "="*70 + "\n")
        
        conn.close()
        return all_passed
        
    except sqlite3.Error as e:
        print(f"\n❌ ERROR DE BASE DE DATOS: {e}")
        print("\nAsegúrate de que:")
        print("  1. El archivo gestion_rrhh.db existe")
        print("  2. Has ejecutado: sqlite3 gestion_rrhh.db < schema_final_completo.sql")
        print("  3. Tienes permisos de lectura/escritura")
        return False
    
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")
        return False


def mostrar_estadisticas(db_path='gestion_rrhh.db'):
    """Muestra estadísticas del sistema"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print_header("ESTADÍSTICAS DEL SISTEMA")
        
        # Contar registros
        tablas = [
            'datos_personales',
            'dispositivos',
            'dias',
            'turnos',
            'convocatoria',
            'capacitaciones',
            'system_errors'
        ]
        
        for tabla in tablas:
            try:
                cursor.execute(f"SELECT COUNT(*) as n FROM {tabla}")
                count = cursor.fetchone()['n']
                print(f"  • {tabla}: {count} registro(s)")
            except:
                print(f"  • {tabla}: No accesible")
        
        print()
        conn.close()
        
    except Exception as e:
        print(f"No se pueden mostrar estadísticas: {e}")


if __name__ == '__main__':
    import os
    
    # Determinar path de BD
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = 'gestion_rrhh.db'
    
    # Verificar si existe
    if not os.path.exists(db_path):
        print(f"\n❌ ERROR: No se encuentra el archivo '{db_path}'")
        print("\nPara crear la base de datos, ejecuta:")
        print(f"  sqlite3 {db_path} < schema_final_completo.sql")
        print()
        sys.exit(1)
    
    # Ejecutar verificación
    resultado = verificar_sistema(db_path)
    
    # Mostrar estadísticas
    if resultado:
        mostrar_estadisticas(db_path)
    
    # Exit code
    sys.exit(0 if resultado else 1)
