#!/usr/bin/env python3
"""
ETL Migration Runner
--------------------
Entry point para ejecutar el pipeline de migración de datos.

Uso:
    python scripts/run_migration.py
    python scripts/run_migration.py --config config/sources.yaml
"""

import sys
from pathlib import Path

# Agregar src al path
ETL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ETL_ROOT / 'src'))

from extractor import (
    load_config,
    extract_exceptions,
    extract_sessions,
    extract_attendance
)
from transformer import deduplicate_resources
from loader import (
    generate_session_inserts,
    generate_resource_inserts,
    generate_participant_inserts,
    write_migration_file
)


def main(config_path: Path = None):
    """Ejecuta el pipeline ETL completo."""
    
    print("=" * 60)
    print("🔄 PIPELINE ETL - Migración de Datos Legacy")
    print("=" * 60)
    
    # Cargar configuración
    if config_path is None:
        config_path = ETL_ROOT / 'config' / 'sources.yaml'
    
    print(f"\n📋 Configuración: {config_path}")
    config = load_config(config_path)
    
    project_root = ETL_ROOT.parent
    excel_path = project_root / config['sources']['legacy_file']['path']
    output_path = ETL_ROOT / config['output']['sql_file']
    
    # Correcciones de fecha
    year_fixes = {}
    for fix in config['transformation'].get('date_fixes', []):
        year_fixes[fix['find']] = fix['replace']
    
    sheets = config['sources']['legacy_file']['sheets']
    schema = config['schema']
    
    # --- EXTRACCIÓN ---
    print("\n📥 FASE 1: Extracción")
    
    print("   Cargando excepciones...")
    exception_set = extract_exceptions(
        excel_path=excel_path,
        sheet_index=sheets['exceptions'],
        date_column=schema['exceptions']['date_column'],
        entity_column=schema['exceptions']['entity_column'],
        year_fixes=year_fixes
    )
    print(f"   ✓ {len(exception_set)} excepciones cargadas")
    
    print("   Cargando sesiones...")
    sessions_df = extract_sessions(
        excel_path=excel_path,
        sheet_index=sheets['sessions'],
        date_column=schema['sessions']['date_column'],
        group_column=schema['sessions']['group_column'],
        resource_prefix=schema['sessions']['resource_prefix'],
        year_fixes=year_fixes,
        default_group=config['transformation']['default_group']
    )
    print(f"   ✓ {len(sessions_df)} registros sesión-recurso")
    
    print("   Cargando asistencia...")
    attendance_set = extract_attendance(
        excel_path=excel_path,
        sheet_index=sheets['attendance'],
        date_column=schema['attendance']['date_column'],
        group_column=schema['attendance']['group_column'],
        entity_start_col=schema['attendance']['entity_start_col'],
        exclude_patterns=schema['attendance']['exclude_columns'],
        exception_set=exception_set,
        year_fixes=year_fixes,
        default_group=config['transformation']['default_group']
    )
    print(f"   ✓ {len(attendance_set)} registros de asistencia válidos")
    
    # --- TRANSFORMACIÓN ---
    print("\n⚙️ FASE 2: Transformación")
    
    sessions_dedup = deduplicate_resources(sessions_df)
    unique_sessions = sessions_dedup[['Fecha_Clean', 'Grupo_Clean']].drop_duplicates()
    print(f"   ✓ {len(unique_sessions)} sesiones únicas")
    print(f"   ✓ {len(sessions_dedup)} asignaciones recurso-sesión")
    
    # --- CARGA ---
    print("\n💾 FASE 3: Generación de SQL")
    
    session_sql = generate_session_inserts(sessions_dedup)
    resource_sql = generate_resource_inserts(
        sessions_dedup,
        default_time=config['transformation']['default_resource_time']
    )
    participant_sql = generate_participant_inserts(sessions_dedup, attendance_set)
    
    # Asegurar que el directorio de salida existe
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    write_migration_file(
        output_path=output_path,
        session_sql=session_sql,
        resource_sql=resource_sql,
        participant_sql=participant_sql,
        use_transactions=config['output']['sql_options']['use_transactions']
    )
    
    print("\n" + "=" * 60)
    print("✅ MIGRACIÓN COMPLETADA")
    print("=" * 60)
    print(f"\n📄 Archivo SQL generado: {output_path}")
    print("   Ejecutar en Supabase SQL Editor para aplicar cambios.\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='ETL Migration Runner')
    parser.add_argument('--config', type=Path, help='Path to config YAML')
    
    args = parser.parse_args()
    main(config_path=args.config)
