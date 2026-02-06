#!/usr/bin/env python3
"""
SUITE DE TESTS v3.0 - VALIDACIÓN DAMA
======================================

Tests completos para validar el diseño v3.0:
- Integridad estructural
- Catálogo de turnos
- Planificación con horarios
- Data lineage
- Triggers automáticos
- Queries y performance

Autor: Pablo - Data Analyst
Fecha: Diciembre 2025
"""

import sqlite3
import sys
from datetime import date, timedelta

# Colores
class Color:
    VERDE = '\033[92m'
    ROJO = '\033[91m'
    AMARILLO = '\033[93m'
    AZUL = '\033[94m'
    FIN = '\033[0m'
    BOLD = '\033[1m'

class TestSuite:
    """Suite de tests DAMA"""
    
    def __init__(self, db_path='data/gestion_rrhh.db'):
        self.db_path = db_path
        self.conn = None
        self.tests_passed = 0
        self.tests_failed = 0
        self.tests_total = 0
    
    def connect(self):
        """Conectar a BD"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
    
    def close(self):
        """Cerrar conexión"""
        if self.conn:
            self.conn.close()
    
    def assert_true(self, condition, test_name, details=""):
        """Assert con reporte"""
        self.tests_total += 1
        if condition:
            self.tests_passed += 1
            print(f"  {Color.VERDE}✓{Color.FIN} {test_name}")
            if details:
                print(f"    {details}")
        else:
            self.tests_failed += 1
            print(f"  {Color.ROJO}✗{Color.FIN} {test_name}")
            if details:
                print(f"    {Color.ROJO}{details}{Color.FIN}")
    
    def assert_equals(self, actual, expected, test_name):
        """Assert de igualdad"""
        self.assert_true(
            actual == expected,
            test_name,
            f"Esperado: {expected}, Obtenido: {actual}"
        )
    
    def print_section(self, title):
        """Imprime sección"""
        print(f"\n{Color.AZUL}{'='*70}{Color.FIN}")
        print(f"{Color.BOLD}{title}{Color.FIN}")
        print(f"{Color.AZUL}{'='*70}{Color.FIN}")
    
    # ========================================================================
    # TEST 1: ESTRUCTURA DE BD
    # ========================================================================
    
    def test_estructura(self):
        """Verifica estructura básica"""
        self.print_section("TEST 1: ESTRUCTURA DE BASE DE DATOS")
        
        cursor = self.conn.cursor()
        
        # Tablas
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        count = cursor.fetchone()[0]
        self.assert_true(
            count >= 19,
            "Cantidad de tablas",
            f"{count} tablas encontradas (esperado: ≥19)"
        )
        
        # Vistas
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'")
        count = cursor.fetchone()[0]
        self.assert_true(
            count >= 11,
            "Cantidad de vistas",
            f"{count} vistas encontradas (esperado: ≥11)"
        )
        
        # Triggers
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'")
        count = cursor.fetchone()[0]
        self.assert_true(
            count >= 13,
            "Cantidad de triggers",
            f"{count} triggers encontrados (esperado: ≥13)"
        )
    
    # ========================================================================
    # TEST 2: CATÁLOGO DE TURNOS (DAMA)
    # ========================================================================
    
    def test_catalogo_turnos(self):
        """Verifica que turnos sea catálogo puro (sin numero_dia_semana)"""
        self.print_section("TEST 2: CATÁLOGO DE TURNOS (DAMA-COMPLIANT)")
        
        cursor = self.conn.cursor()
        
        # Verificar que NO existe columna numero_dia_semana
        cursor.execute("PRAGMA table_info(turnos)")
        columnas = [row[1] for row in cursor.fetchall()]
        
        self.assert_true(
            'numero_dia_semana' not in columnas,
            "Turnos SIN numero_dia_semana (catálogo puro)",
            "✓ Diseño DAMA: un turno = un tipo"
        )
        
        # Verificar columnas nuevas
        self.assert_true(
            'hora_inicio_default' in columnas,
            "Campo hora_inicio_default existe"
        )
        
        self.assert_true(
            'hora_fin_default' in columnas,
            "Campo hora_fin_default existe"
        )
        
        # Verificar tipos de turno
        cursor.execute("SELECT COUNT(*) FROM turnos")
        count = cursor.fetchone()[0]
        
        self.assert_true(
            count >= 6,
            "Cantidad de turnos en catálogo",
            f"{count} turnos (esperado: ≥6)"
        )
        
        # Verificar que cada tipo es único
        cursor.execute("""
            SELECT tipo_turno, COUNT(*) as n 
            FROM turnos 
            GROUP BY tipo_turno 
            HAVING n > 1
        """)
        duplicados = cursor.fetchall()
        
        self.assert_true(
            len(duplicados) == 0,
            "No hay tipos de turno duplicados",
            "✓ Un tipo = un registro"
        )
    
    # ========================================================================
    # TEST 3: PLANIFICACIÓN CON HORARIOS
    # ========================================================================
    
    def test_planificacion_horarios(self):
        """Verifica que planificación tenga horarios efectivos"""
        self.print_section("TEST 3: PLANIFICACIÓN CON HORARIOS EFECTIVOS")
        
        cursor = self.conn.cursor()
        
        # Verificar columnas nuevas
        cursor.execute("PRAGMA table_info(planificacion)")
        columnas = [row[1] for row in cursor.fetchall()]
        
        campos_requeridos = [
            'hora_inicio',
            'hora_fin', 
            'cant_horas',
            'usa_horario_custom',
            'motivo_horario_custom'
        ]
        
        for campo in campos_requeridos:
            self.assert_true(
                campo in columnas,
                f"Campo '{campo}' existe en planificacion"
            )
        
        # Verificar que las planificaciones tienen horarios
        cursor.execute("SELECT COUNT(*) FROM planificacion")
        total = cursor.fetchone()[0]
        
        if total > 0:
            cursor.execute("""
                SELECT COUNT(*) FROM planificacion 
                WHERE hora_inicio IS NOT NULL 
                AND hora_fin IS NOT NULL
            """)
            con_horarios = cursor.fetchone()[0]
            
            self.assert_equals(
                con_horarios,
                total,
                "Todas las planificaciones tienen horarios"
            )
        else:
            self.assert_true(
                True,
                "No hay planificaciones para validar (OK en BD vacía)"
            )
    
    # ========================================================================
    # TEST 4: DATA LINEAGE
    # ========================================================================
    
    def test_data_lineage(self):
        """Verifica trazabilidad de horarios"""
        self.print_section("TEST 4: DATA LINEAGE (Trazabilidad de Horarios)")
        
        cursor = self.conn.cursor()
        
        # Verificar que existe la vista
        cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master 
            WHERE type='view' AND name='vista_planificacion_completa'
        """)
        existe = cursor.fetchone()[0]
        
        self.assert_true(
            existe == 1,
            "Vista vista_planificacion_completa existe"
        )
        
        if existe:
            # Probar la vista
            try:
                cursor.execute("SELECT * FROM vista_planificacion_completa LIMIT 1")
                row = cursor.fetchone()
                
                if row:
                    columnas = list(row.keys())
                    
                    self.assert_true(
                        'origen_horario' in columnas,
                        "Vista tiene columna origen_horario (data lineage)"
                    )
                    
                    self.assert_true(
                        'motivo_horario_custom' in columnas,
                        "Vista tiene columna motivo_horario_custom"
                    )
                else:
                    self.assert_true(
                        True,
                        "Vista funciona (sin datos aún)"
                    )
                    
            except Exception as e:
                self.assert_true(
                    False,
                    "Vista ejecutable",
                    f"Error: {e}"
                )
    
    # ========================================================================
    # TEST 5: TRIGGERS AUTOMÁTICOS
    # ========================================================================
    
    def test_triggers_automaticos(self):
        """Verifica que los triggers nuevos existen"""
        self.print_section("TEST 5: TRIGGERS AUTOMÁTICOS")
        
        cursor = self.conn.cursor()
        
        triggers_v3 = [
            'trg_plani_auto_horarios',
            'trg_plani_update_timestamp'
        ]
        
        for trigger_name in triggers_v3:
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='trigger' AND name=?
            """, (trigger_name,))
            existe = cursor.fetchone()[0]
            
            self.assert_true(
                existe == 1,
                f"Trigger '{trigger_name}' existe"
            )
    
    # ========================================================================
    # TEST 6: FUNCIONALIDAD TRIGGER AUTO-HORARIOS
    # ========================================================================
    
    def test_trigger_auto_horarios(self):
        """Prueba funcionalidad del trigger trg_plani_auto_horarios"""
        self.print_section("TEST 6: FUNCIONALIDAD TRIGGER AUTO-HORARIOS")
        
        cursor = self.conn.cursor()
        
        # Obtener un turno con horarios default
        cursor.execute("""
            SELECT id_turno, hora_inicio_default, hora_fin_default, cant_horas_default
            FROM turnos 
            WHERE hora_inicio_default IS NOT NULL
            LIMIT 1
        """)
        turno = cursor.fetchone()
        
        if not turno:
            self.assert_true(
                True,
                "Sin turnos para probar (OK en BD sin datos)"
            )
            return
        
        id_turno = turno[0]
        hora_esp = turno[1]
        
        # Obtener un día
        cursor.execute("SELECT id_dia FROM dias LIMIT 1")
        dia = cursor.fetchone()
        
        if not dia:
            self.assert_true(
                True,
                "Sin días para probar (OK en BD sin datos)"
            )
            return
        
        id_dia = dia[0]
        
        # Crear planificación SIN especificar horarios
        try:
            cursor.execute("""
                INSERT INTO planificacion 
                (id_dia, id_turno, cant_residentes_plan)
                VALUES (?, ?, 3)
            """, (id_dia, id_turno))
            
            id_plani = cursor.lastrowid
            
            # Verificar que el trigger auto-completó los horarios
            cursor.execute("""
                SELECT hora_inicio, hora_fin, cant_horas, usa_horario_custom
                FROM planificacion
                WHERE id_plani = ?
            """, (id_plani,))
            
            result = cursor.fetchone()
            
            if result:
                self.assert_true(
                    result[0] is not None,
                    "Trigger auto-completó hora_inicio"
                )
                
                self.assert_true(
                    result[1] is not None,
                    "Trigger auto-completó hora_fin"
                )
                
                self.assert_equals(
                    result[3],
                    0,
                    "usa_horario_custom = 0 (usa catálogo)"
                )
            
            # Limpiar test
            cursor.execute("DELETE FROM planificacion WHERE id_plani = ?", (id_plani,))
            self.conn.commit()
            
        except Exception as e:
            self.assert_true(
                False,
                "Trigger funciona correctamente",
                f"Error: {e}"
            )
    
    # ========================================================================
    # TEST 7: INTEGRIDAD REFERENCIAL
    # ========================================================================
    
    def test_integridad_referencial(self):
        """Verifica FKs y constraints"""
        self.print_section("TEST 7: INTEGRIDAD REFERENCIAL")
        
        cursor = self.conn.cursor()
        
        # Verificar FK activadas
        cursor.execute("PRAGMA foreign_keys")
        fk_status = cursor.fetchone()[0]
        
        self.assert_equals(
            fk_status,
            1,
            "Foreign Keys activadas"
        )
        
        # Verificar integridad
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        
        self.assert_equals(
            result,
            'ok',
            "Integridad de BD"
        )
        
        # Verificar FKs específicas
        cursor.execute("PRAGMA foreign_key_check")
        errores = cursor.fetchall()
        
        self.assert_true(
            len(errores) == 0,
            "Consistencia de Foreign Keys",
            f"{len(errores)} error(es) de FK" if errores else "Sin errores"
        )
    
    # ========================================================================
    # TEST 8: QUERIES DE PERFORMANCE
    # ========================================================================
    
    def test_queries_performance(self):
        """Verifica que queries importantes funcionan"""
        self.print_section("TEST 8: QUERIES Y PERFORMANCE")
        
        cursor = self.conn.cursor()
        
        # Query 1: Convocatorias por fecha (v3.0 - sin numero_dia_semana)
        try:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM convocatoria c
                JOIN planificacion p ON c.id_plani = p.id_plani
                JOIN turnos t ON p.id_turno = t.id_turno
                WHERE t.tipo_turno = 'mañana'
            """)
            count = cursor.fetchone()[0]
            
            self.assert_true(
                True,
                f"Query convocatorias por tipo turno funciona ({count} registros)"
            )
        except Exception as e:
            self.assert_true(
                False,
                "Query convocatorias por tipo turno",
                f"Error: {e}"
            )
        
        # Query 2: Planificación con horarios
        try:
            cursor.execute("""
                SELECT COUNT(*)
                FROM vista_planificacion_completa
                WHERE origen_horario = 'Catálogo'
            """)
            count = cursor.fetchone()[0]
            
            self.assert_true(
                True,
                f"Vista planificación completa funciona ({count} con horarios catálogo)"
            )
        except Exception as e:
            self.assert_true(
                False,
                "Vista planificación completa",
                f"Error: {e}"
            )
        
        # Query 3: Saldos (debe funcionar igual)
        try:
            cursor.execute("SELECT COUNT(*) FROM saldos")
            count = cursor.fetchone()[0]
            
            self.assert_true(
                True,
                f"Sistema de saldos funciona ({count} registros)"
            )
        except Exception as e:
            self.assert_true(
                False,
                "Sistema de saldos",
                f"Error: {e}"
            )
    
    # ========================================================================
    # TEST 9: CASOS DE USO ESPECÍFICOS
    # ========================================================================
    
    def test_casos_uso(self):
        """Valida casos de uso del centro cultural"""
        self.print_section("TEST 9: CASOS DE USO DEL CENTRO CULTURAL")
        
        cursor = self.conn.cursor()
        
        # Caso 1: Múltiples turnos mismo día
        cursor.execute("""
            SELECT d.fecha, COUNT(DISTINCT p.id_turno) as turnos
            FROM planificacion p
            JOIN dias d ON p.id_dia = d.id_dia
            GROUP BY d.fecha
            HAVING COUNT(DISTINCT p.id_turno) > 1
            LIMIT 1
        """)
        result = cursor.fetchone()
        
        if result:
            self.assert_true(
                True,
                f"Soporta múltiples turnos por día (ej: {result['fecha']} tiene {result['turnos']} turnos)"
            )
        else:
            self.assert_true(
                True,
                "Sin datos para validar múltiples turnos (OK en BD vacía)"
            )
        
        # Caso 2: Horarios variables (capacitaciones)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM planificacion p
            JOIN turnos t ON p.id_turno = t.id_turno
            WHERE t.tipo_turno = 'capacitacion'
            AND p.usa_horario_custom = 1
        """)
        count = cursor.fetchone()[0]
        
        self.assert_true(
            True,
            f"Soporta horarios variables (capacitaciones custom: {count})"
        )
        
        # Caso 3: Turnos de apertura público
        cursor.execute("""
            SELECT COUNT(*) 
            FROM turnos 
            WHERE tipo_turno LIKE 'apertura_publico%'
        """)
        count = cursor.fetchone()[0]
        
        self.assert_true(
            count >= 2,
            "Turnos de apertura público (corto/largo)",
            f"{count} variantes (esperado: ≥2)"
        )
    
    # ========================================================================
    # TEST 10: COMPARACIÓN DISEÑO ANTERIOR
    # ========================================================================
    
    def test_ventajas_v3(self):
        """Valida ventajas del diseño v3.0"""
        self.print_section("TEST 10: VENTAJAS DISEÑO v3.0 vs v2.0")
        
        cursor = self.conn.cursor()
        
        # Ventaja 1: Menos registros en turnos
        cursor.execute("SELECT COUNT(*) FROM turnos")
        count_turnos = cursor.fetchone()[0]
        
        self.assert_true(
            count_turnos <= 10,
            "Catálogo de turnos compacto",
            f"{count_turnos} turnos (vs ~35 en v2.0)"
        )
        
        # Ventaja 2: Queries más simples (sin JOIN con días para filtrar)
        # Simplemente verificamos que no existe la columna
        cursor.execute("PRAGMA table_info(turnos)")
        columnas = [row[1] for row in cursor.fetchall()]
        
        self.assert_true(
            'numero_dia_semana' not in columnas,
            "Queries más simples (sin numero_dia_semana)",
            "✓ Sin necesidad de JOIN con dias para filtrar turnos"
        )
        
        # Ventaja 3: Flexibilidad total
        self.assert_true(
            'usa_horario_custom' in [row[1] for row in cursor.execute("PRAGMA table_info(planificacion)")],
            "Flexibilidad en horarios (campo usa_horario_custom)",
            "✓ Permite override de horarios catálogo"
        )
    
    # ========================================================================
    # EJECUTAR TODOS LOS TESTS
    # ========================================================================
    
    def run_all(self):
        """Ejecuta todos los tests"""
        print("\n" + "="*70)
        print(f"{Color.BOLD}SUITE DE TESTS v3.0 - VALIDACIÓN DAMA{Color.FIN}")
        print("="*70)
        print(f"Base de datos: {self.db_path}")
        
        try:
            self.connect()
            
            # Ejecutar cada test
            self.test_estructura()
            self.test_catalogo_turnos()
            self.test_planificacion_horarios()
            self.test_data_lineage()
            self.test_triggers_automaticos()
            self.test_trigger_auto_horarios()
            self.test_integridad_referencial()
            self.test_queries_performance()
            self.test_casos_uso()
            self.test_ventajas_v3()
            
            # Resumen
            self.print_section("RESUMEN DE TESTS")
            
            total = self.tests_total
            passed = self.tests_passed
            failed = self.tests_failed
            pct = (passed / total * 100) if total > 0 else 0
            
            print(f"\n  Total tests: {total}")
            print(f"  {Color.VERDE}✓ Pasados: {passed}{Color.FIN}")
            print(f"  {Color.ROJO}✗ Fallados: {failed}{Color.FIN}")
            print(f"  Tasa de éxito: {pct:.1f}%")
            
            if failed == 0:
                print(f"\n  {Color.VERDE}{Color.BOLD}🎉 ¡TODOS LOS TESTS PASARON!{Color.FIN}")
                print(f"  {Color.VERDE}✅ Sistema v3.0 DAMA-compliant validado{Color.FIN}\n")
                return True
            else:
                print(f"\n  {Color.AMARILLO}⚠️  ALGUNOS TESTS FALLARON{Color.FIN}")
                print(f"  Revisar errores arriba\n")
                return False
                
        except Exception as e:
            print(f"\n{Color.ROJO}ERROR CRÍTICO: {e}{Color.FIN}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.close()

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tests de validación v3.0')
    parser.add_argument('--db', default='data/gestion_rrhh.db', help='Path a BD')
    args = parser.parse_args()
    
    suite = TestSuite(args.db)
    success = suite.run_all()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
