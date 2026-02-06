#!/usr/bin/env python3
"""
=============================================================================
SYNC MANAGER v1.0
=============================================================================

Gestiona sincronización entre:
- 3 computadoras de escritorio (El Molino)
- 1 notebook remota (troubleshooting)
- Supabase (PostgreSQL en la nube)

ARQUITECTURA:
    ┌───────────────────────────────────────────────────────────────┐
    │                      SUPABASE (Cloud)                          │
    │                   Fuente de verdad (año actual)                │
    └──────────────────────────┬────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
   ┌─────────┐           ┌─────────┐           ┌─────────┐
   │  PC #1  │           │  PC #2  │           │ Notebook│
   │ (cache) │           │ (cache) │           │ (remote)│
   └─────────┘           └─────────┘           └─────────┘

ESTRATEGIA DE SINCRONIZACIÓN:
- Supabase es la fuente de verdad para el año actual
- SQLite local es caché + histórico
- Sync bidireccional con detección de conflictos
- Timestamp-based conflict resolution

Autor: Pablo - Data Analyst
Fecha: Diciembre 2025
=============================================================================
"""

import sqlite3
import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Importar el unified_db_manager
try:
    from src.database.manager import UnifiedDBManager, DBMode
except ImportError:
    # Si se ejecuta standalone, intentar agregar root al path
    import sys
    from pathlib import Path
    root_path = str(Path(__file__).parent.parent.parent)
    if root_path not in sys.path:
        sys.path.insert(0, root_path)
    
    try:
        from src.database.manager import UnifiedDBManager, DBMode
    except ImportError:
        # Fallback original
        sys.path.insert(0, str(Path(__file__).parent))
        from src.database.manager import UnifiedDBManager, DBMode

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS Y DATACLASSES
# =============================================================================

class SyncDirection(Enum):
    """Dirección de sincronización"""
    DOWNLOAD = "download"       # Cloud → Local
    UPLOAD = "upload"           # Local → Cloud
    BIDIRECTIONAL = "both"      # Ambas direcciones


class ConflictResolution(Enum):
    """Estrategia de resolución de conflictos"""
    CLOUD_WINS = "cloud"        # Supabase gana
    LOCAL_WINS = "local"        # SQLite local gana
    NEWEST_WINS = "newest"      # El más reciente gana
    MANUAL = "manual"           # Pedir intervención


@dataclass
class SyncRecord:
    """Registro de un cambio a sincronizar"""
    table: str
    record_id: int
    operation: str              # 'INSERT', 'UPDATE', 'DELETE'
    data: Dict[str, Any]
    timestamp: datetime
    source: str                 # 'local' o 'cloud'
    checksum: str
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d


@dataclass
class SyncResult:
    """Resultado de una sincronización"""
    success: bool
    downloaded: int
    uploaded: int
    conflicts: int
    errors: List[str]
    duration_seconds: float
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d


@dataclass
class SyncStatus:
    """Estado de sincronización"""
    last_sync: Optional[datetime]
    pending_uploads: int
    pending_downloads: int
    conflicts: int
    is_synced: bool
    next_sync: Optional[datetime]


# =============================================================================
# SYNC MANAGER
# =============================================================================

class SyncManager:
    """
    Gestor de sincronización entre Supabase y SQLite local
    
    Características:
    - Sincronización bidireccional
    - Detección de conflictos
    - Resolución automática o manual
    - Registro de historial de sync
    - Optimización por timestamps
    """
    
    # Tablas a sincronizar (en orden de dependencias FK)
    SYNC_TABLES = [
        'datos_personales',
        'dispositivos', 
        'turnos',
        'dias',
        'planificacion',
        'convocatoria',
        'menu',
        'saldos',
        'inasistencias',
        'certificados',
        'capacitaciones',
        'capacitaciones_participantes'
    ]
    
    # Campos de timestamp para detección de cambios
    TIMESTAMP_FIELDS = {
        'convocatoria': 'fecha_modificacion',
        'inasistencias': 'fecha_actualizacion_estado',
        'saldos': 'fecha_actualizacion',
        'menu': 'fecha_registro',
        'planificacion': 'fecha_modificacion'
    }
    
    def __init__(self, 
                 db_manager: UnifiedDBManager = None,
                 sync_log_path: str = 'data/sync_log.json',
                 conflict_resolution: ConflictResolution = ConflictResolution.NEWEST_WINS):
        """
        Inicializa el SyncManager
        
        Args:
            db_manager: UnifiedDBManager (crea uno nuevo si None)
            sync_log_path: Ruta para guardar log de sincronizaciones
            conflict_resolution: Estrategia por defecto para conflictos
        """
        self.db = db_manager or UnifiedDBManager()
        self.sync_log_path = Path(sync_log_path)
        self.conflict_resolution = conflict_resolution
        
        # Estado
        self._last_sync: Optional[datetime] = None
        self._pending_changes: List[SyncRecord] = []
        self._conflicts: List[Tuple[SyncRecord, SyncRecord]] = []
        
        # Cargar último estado de sync
        self._load_sync_state()
        
        logger.info("SyncManager inicializado")
    
    # =========================================================================
    # GESTIÓN DE ESTADO
    # =========================================================================
    
    def _load_sync_state(self):
        """Carga el estado de la última sincronización"""
        if self.sync_log_path.exists():
            try:
                with open(self.sync_log_path) as f:
                    state = json.load(f)
                    if state.get('last_sync'):
                        self._last_sync = datetime.fromisoformat(state['last_sync'])
                    logger.info(f"Estado de sync cargado. Último: {self._last_sync}")
            except Exception as e:
                logger.warning(f"No se pudo cargar estado de sync: {e}")
    
    def _save_sync_state(self, result: SyncResult):
        """Guarda el estado de sincronización"""
        state = {
            'last_sync': result.timestamp.isoformat(),
            'last_result': result.to_dict()
        }
        
        self.sync_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.sync_log_path, 'w') as f:
            json.dump(state, f, indent=2)
    
    def get_status(self) -> SyncStatus:
        """
        Obtiene estado actual de sincronización
        
        Returns:
            SyncStatus con información actual
        """
        pending_up = len([c for c in self._pending_changes if c.source == 'local'])
        pending_down = len([c for c in self._pending_changes if c.source == 'cloud'])
        
        return SyncStatus(
            last_sync=self._last_sync,
            pending_uploads=pending_up,
            pending_downloads=pending_down,
            conflicts=len(self._conflicts),
            is_synced=(pending_up == 0 and pending_down == 0 and len(self._conflicts) == 0),
            next_sync=None  # Podría calcularse según política
        )
    
    # =========================================================================
    # DETECCIÓN DE CAMBIOS
    # =========================================================================
    
    def _compute_checksum(self, data: Dict[str, Any]) -> str:
        """Calcula checksum de un registro para detectar cambios"""
        # Excluir campos de timestamp para comparar solo datos
        filtered = {k: v for k, v in data.items() 
                   if not k.endswith('_timestamp') and not k.endswith('_modificacion')}
        serialized = json.dumps(filtered, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode()).hexdigest()
    
    def _get_local_changes(self, since: datetime = None) -> List[SyncRecord]:
        """
        Detecta cambios locales desde una fecha
        
        Args:
            since: Fecha desde la cual buscar cambios (None = todos)
        
        Returns:
            Lista de SyncRecord con cambios locales
        """
        changes = []
        
        if not since:
            since = self._last_sync or datetime(2000, 1, 1)
        
        for table in self.SYNC_TABLES:
            try:
                timestamp_field = self.TIMESTAMP_FIELDS.get(table, 'fecha_creacion')
                
                # Query local
                result = self.db.query(
                    f"SELECT * FROM {table} WHERE {timestamp_field} > ?",
                    (since.isoformat(),),
                    mode=DBMode.SQLITE
                )
                
                for row in result.data:
                    # Obtener ID primario
                    id_field = self._get_primary_key(table)
                    record_id = row.get(id_field, 0)
                    
                    changes.append(SyncRecord(
                        table=table,
                        record_id=record_id,
                        operation='UPDATE',  # Asumimos update, podría refinarse
                        data=row,
                        timestamp=datetime.now(),
                        source='local',
                        checksum=self._compute_checksum(row)
                    ))
                    
            except Exception as e:
                logger.warning(f"Error detectando cambios en {table}: {e}")
        
        return changes
    
    def _get_cloud_changes(self, since: datetime = None) -> List[SyncRecord]:
        """
        Detecta cambios en Supabase desde una fecha
        
        Args:
            since: Fecha desde la cual buscar cambios
        
        Returns:
            Lista de SyncRecord con cambios en cloud
        """
        if not self.db.supabase_connected:
            return []
        
        changes = []
        
        if not since:
            since = self._last_sync or datetime(2000, 1, 1)
        
        for table in self.SYNC_TABLES:
            try:
                timestamp_field = self.TIMESTAMP_FIELDS.get(table, 'fecha_creacion')
                
                # Query Supabase
                result = self.db.query(
                    f"SELECT * FROM {table} WHERE {timestamp_field} > ?",
                    (since.isoformat(),),
                    mode=DBMode.SUPABASE
                )
                
                for row in result.data:
                    id_field = self._get_primary_key(table)
                    record_id = row.get(id_field, 0)
                    
                    changes.append(SyncRecord(
                        table=table,
                        record_id=record_id,
                        operation='UPDATE',
                        data=row,
                        timestamp=datetime.now(),
                        source='cloud',
                        checksum=self._compute_checksum(row)
                    ))
                    
            except Exception as e:
                logger.warning(f"Error detectando cambios cloud en {table}: {e}")
        
        return changes
    
    def _get_primary_key(self, table: str) -> str:
        """Obtiene el nombre del campo de clave primaria"""
        pk_mapping = {
            'datos_personales': 'id_agente',
            'dispositivos': 'id_dispositivo',
            'turnos': 'id_turno',
            'dias': 'id_dia',
            'planificacion': 'id_plani',
            'convocatoria': 'id_convocatoria',
            'menu': 'id_menu',
            'saldos': 'id_saldo',
            'inasistencias': 'id_inasistencia',
            'certificados': 'id_certificado',
            'capacitaciones': 'id_cap',
            'capacitaciones_participantes': 'id_participante'
        }
        return pk_mapping.get(table, 'id')
    
    # =========================================================================
    # SINCRONIZACIÓN
    # =========================================================================
    
    def sync(self, direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
             tables: List[str] = None,
             force: bool = False) -> SyncResult:
        """
        Ejecuta sincronización
        
        Args:
            direction: Dirección de sync (download, upload, both)
            tables: Lista de tablas a sincronizar (None = todas)
            force: Forzar sync completo ignorando timestamps
        
        Returns:
            SyncResult con estadísticas
        """
        import time
        start_time = time.time()
        
        errors = []
        downloaded = 0
        uploaded = 0
        conflicts = 0
        
        tables_to_sync = tables or self.SYNC_TABLES
        
        logger.info(f"Iniciando sincronización: {direction.value}")
        
        # Verificar conexión a Supabase
        if not self.db.supabase_connected:
            errors.append("Supabase no está conectado")
            return SyncResult(
                success=False,
                downloaded=0,
                uploaded=0,
                conflicts=0,
                errors=errors,
                duration_seconds=time.time() - start_time,
                timestamp=datetime.now()
            )
        
        # Detectar cambios
        since = None if force else self._last_sync
        
        if direction in (SyncDirection.DOWNLOAD, SyncDirection.BIDIRECTIONAL):
            cloud_changes = self._get_cloud_changes(since)
            logger.info(f"Cambios en cloud detectados: {len(cloud_changes)}")
            
            # Aplicar cambios cloud → local
            for change in cloud_changes:
                if change.table in tables_to_sync:
                    try:
                        self._apply_to_local(change)
                        downloaded += 1
                    except Exception as e:
                        errors.append(f"Error descargando {change.table}#{change.record_id}: {e}")
        
        if direction in (SyncDirection.UPLOAD, SyncDirection.BIDIRECTIONAL):
            local_changes = self._get_local_changes(since)
            logger.info(f"Cambios locales detectados: {len(local_changes)}")
            
            # Detectar conflictos si es bidireccional
            if direction == SyncDirection.BIDIRECTIONAL:
                conflicts = self._detect_conflicts(local_changes, cloud_changes)
                logger.info(f"Conflictos detectados: {len(conflicts)}")
            
            # Aplicar cambios local → cloud
            for change in local_changes:
                if change.table in tables_to_sync:
                    # Verificar si hay conflicto
                    if any(c[0].table == change.table and c[0].record_id == change.record_id 
                           for c in self._conflicts):
                        continue  # Saltar, se resuelve aparte
                    
                    try:
                        self._apply_to_cloud(change)
                        uploaded += 1
                    except Exception as e:
                        errors.append(f"Error subiendo {change.table}#{change.record_id}: {e}")
        
        # Resolver conflictos automáticamente si está configurado
        if self._conflicts and self.conflict_resolution != ConflictResolution.MANUAL:
            resolved = self._resolve_conflicts()
            logger.info(f"Conflictos resueltos: {resolved}")
        
        duration = time.time() - start_time
        
        result = SyncResult(
            success=len(errors) == 0,
            downloaded=downloaded,
            uploaded=uploaded,
            conflicts=len(self._conflicts),
            errors=errors,
            duration_seconds=duration,
            timestamp=datetime.now()
        )
        
        # Guardar estado
        if result.success:
            self._last_sync = result.timestamp
            self._save_sync_state(result)
        
        logger.info(f"Sincronización completada: ↓{downloaded} ↑{uploaded} ⚠{conflicts} ({duration:.2f}s)")
        
        return result
    
    def sync_download(self, tables: List[str] = None) -> SyncResult:
        """Sincroniza solo descargando (cloud → local)"""
        return self.sync(SyncDirection.DOWNLOAD, tables)
    
    def sync_upload(self, tables: List[str] = None) -> SyncResult:
        """Sincroniza solo subiendo (local → cloud)"""
        return self.sync(SyncDirection.UPLOAD, tables)
    
    def full_sync(self, force: bool = False) -> SyncResult:
        """Sincronización bidireccional completa"""
        return self.sync(SyncDirection.BIDIRECTIONAL, force=force)
    
    # =========================================================================
    # APLICACIÓN DE CAMBIOS
    # =========================================================================
    
    def _apply_to_local(self, record: SyncRecord):
        """Aplica un cambio a SQLite local"""
        pk = self._get_primary_key(record.table)
        
        # Verificar si existe
        existing = self.db.query_one(
            f"SELECT * FROM {record.table} WHERE {pk} = ?",
            (record.record_id,),
            mode=DBMode.SQLITE
        )
        
        if existing:
            # UPDATE
            cols = [k for k in record.data.keys() if k != pk]
            set_clause = ", ".join([f"{c} = ?" for c in cols])
            values = [record.data[c] for c in cols] + [record.record_id]
            
            self.db.execute(
                f"UPDATE {record.table} SET {set_clause} WHERE {pk} = ?",
                tuple(values),
                mode=DBMode.SQLITE
            )
        else:
            # INSERT
            cols = list(record.data.keys())
            placeholders = ", ".join(["?" for _ in cols])
            col_names = ", ".join(cols)
            values = [record.data[c] for c in cols]
            
            self.db.execute(
                f"INSERT INTO {record.table} ({col_names}) VALUES ({placeholders})",
                tuple(values),
                mode=DBMode.SQLITE
            )
    
    def _apply_to_cloud(self, record: SyncRecord):
        """Aplica un cambio a Supabase"""
        pk = self._get_primary_key(record.table)
        
        # Verificar si existe
        existing = self.db.query_one(
            f"SELECT * FROM {record.table} WHERE {pk} = %s",
            (record.record_id,),
            mode=DBMode.SUPABASE
        )
        
        # Convertir booleanos para PostgreSQL
        data = self._convert_booleans_for_pg(record.data)
        
        if existing:
            # UPDATE
            cols = [k for k in data.keys() if k != pk]
            set_clause = ", ".join([f"{c} = %s" for c in cols])
            values = [data[c] for c in cols] + [record.record_id]
            
            self.db.execute(
                f"UPDATE {record.table} SET {set_clause} WHERE {pk} = %s",
                tuple(values),
                mode=DBMode.SUPABASE
            )
        else:
            # INSERT
            cols = list(data.keys())
            placeholders = ", ".join(["%s" for _ in cols])
            col_names = ", ".join(cols)
            values = [data[c] for c in cols]
            
            self.db.execute(
                f"INSERT INTO {record.table} ({col_names}) VALUES ({placeholders})",
                tuple(values),
                mode=DBMode.SUPABASE
            )
    
    def _convert_booleans_for_pg(self, data: Dict) -> Dict:
        """Convierte 0/1 a False/True para PostgreSQL"""
        result = {}
        for key, value in data.items():
            if isinstance(value, int) and value in (0, 1):
                # Detectar si es campo booleano por nombre
                if any(word in key.lower() for word in ['activo', 'feriado', 'requiere', 'asistio', 'aprobado', 'resolved', 'recurring', 'bloqueante', 'alerta', 'custom', 'grupo']):
                    result[key] = bool(value)
                else:
                    result[key] = value
            else:
                result[key] = value
        return result
    
    # =========================================================================
    # DETECCIÓN Y RESOLUCIÓN DE CONFLICTOS
    # =========================================================================
    
    def _detect_conflicts(self, local_changes: List[SyncRecord], 
                          cloud_changes: List[SyncRecord]) -> int:
        """
        Detecta conflictos entre cambios locales y cloud
        
        Un conflicto ocurre cuando el mismo registro fue modificado
        en ambos lados desde la última sincronización.
        """
        self._conflicts = []
        
        for local in local_changes:
            for cloud in cloud_changes:
                if (local.table == cloud.table and 
                    local.record_id == cloud.record_id and
                    local.checksum != cloud.checksum):
                    self._conflicts.append((local, cloud))
        
        return len(self._conflicts)
    
    def _resolve_conflicts(self) -> int:
        """
        Resuelve conflictos según la estrategia configurada
        
        Returns:
            Número de conflictos resueltos
        """
        resolved = 0
        
        for local, cloud in self._conflicts[:]:
            try:
                if self.conflict_resolution == ConflictResolution.CLOUD_WINS:
                    self._apply_to_local(cloud)
                    resolved += 1
                    
                elif self.conflict_resolution == ConflictResolution.LOCAL_WINS:
                    self._apply_to_cloud(local)
                    resolved += 1
                    
                elif self.conflict_resolution == ConflictResolution.NEWEST_WINS:
                    if local.timestamp > cloud.timestamp:
                        self._apply_to_cloud(local)
                    else:
                        self._apply_to_local(cloud)
                    resolved += 1
                
                self._conflicts.remove((local, cloud))
                
            except Exception as e:
                logger.error(f"Error resolviendo conflicto: {e}")
        
        return resolved
    
    def get_conflicts(self) -> List[Dict]:
        """
        Obtiene lista de conflictos pendientes
        
        Returns:
            Lista de dicts con información de cada conflicto
        """
        return [
            {
                'table': local.table,
                'record_id': local.record_id,
                'local_data': local.data,
                'cloud_data': cloud.data,
                'local_timestamp': local.timestamp.isoformat(),
                'cloud_timestamp': cloud.timestamp.isoformat()
            }
            for local, cloud in self._conflicts
        ]
    
    def resolve_conflict(self, table: str, record_id: int, 
                         keep: str = 'cloud') -> bool:
        """
        Resuelve un conflicto específico manualmente
        
        Args:
            table: Nombre de la tabla
            record_id: ID del registro
            keep: 'cloud' o 'local'
        
        Returns:
            True si se resolvió correctamente
        """
        for local, cloud in self._conflicts[:]:
            if local.table == table and local.record_id == record_id:
                try:
                    if keep == 'cloud':
                        self._apply_to_local(cloud)
                    else:
                        self._apply_to_cloud(local)
                    
                    self._conflicts.remove((local, cloud))
                    return True
                except Exception as e:
                    logger.error(f"Error resolviendo conflicto: {e}")
                    return False
        
        return False
    
    # =========================================================================
    # UTILIDADES
    # =========================================================================
    
    def check_sync_needed(self) -> bool:
        """
        Verifica si es necesaria una sincronización
        
        Returns:
            True si hay cambios pendientes
        """
        if not self.db.supabase_connected:
            return False
        
        # Verificar si hay cambios locales
        local_changes = self._get_local_changes(self._last_sync)
        if local_changes:
            return True
        
        # Verificar si hay cambios en cloud
        cloud_changes = self._get_cloud_changes(self._last_sync)
        if cloud_changes:
            return True
        
        return False
    
    def get_sync_preview(self) -> Dict[str, Any]:
        """
        Previsualiza qué se sincronizaría sin ejecutar
        
        Returns:
            Dict con preview de cambios
        """
        local_changes = self._get_local_changes(self._last_sync)
        cloud_changes = self._get_cloud_changes(self._last_sync) if self.db.supabase_connected else []
        
        preview = {
            'will_download': len(cloud_changes),
            'will_upload': len(local_changes),
            'potential_conflicts': 0,
            'tables_affected': set(),
            'details': {
                'download': [],
                'upload': []
            }
        }
        
        for change in cloud_changes:
            preview['tables_affected'].add(change.table)
            preview['details']['download'].append({
                'table': change.table,
                'id': change.record_id
            })
        
        for change in local_changes:
            preview['tables_affected'].add(change.table)
            preview['details']['upload'].append({
                'table': change.table,
                'id': change.record_id
            })
        
        preview['tables_affected'] = list(preview['tables_affected'])
        
        # Detectar posibles conflictos
        self._detect_conflicts(local_changes, cloud_changes)
        preview['potential_conflicts'] = len(self._conflicts)
        
        return preview


# =============================================================================
# CLI Y PRUEBAS
# =============================================================================

def main():
    """Función principal - interfaz de línea de comandos"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SyncManager - Sincronización Supabase ↔ SQLite')
    parser.add_argument('--status', action='store_true', help='Mostrar estado de sync')
    parser.add_argument('--preview', action='store_true', help='Previsualizar sin ejecutar')
    parser.add_argument('--sync', action='store_true', help='Ejecutar sincronización completa')
    parser.add_argument('--download', action='store_true', help='Solo descargar (cloud → local)')
    parser.add_argument('--upload', action='store_true', help='Solo subir (local → cloud)')
    parser.add_argument('--force', action='store_true', help='Forzar sync completo')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("  SYNC MANAGER - Sincronización Supabase ↔ SQLite")
    print("=" * 70)
    
    # Crear manager
    db = UnifiedDBManager()
    sync = SyncManager(db)
    
    if args.status:
        status = sync.get_status()
        print(f"\n📊 Estado de sincronización:")
        print(f"   Última sync: {status.last_sync or 'Nunca'}")
        print(f"   Pendientes subir: {status.pending_uploads}")
        print(f"   Pendientes bajar: {status.pending_downloads}")
        print(f"   Conflictos: {status.conflicts}")
        print(f"   Sincronizado: {'✅ Sí' if status.is_synced else '❌ No'}")
    
    elif args.preview:
        print("\n🔍 Previsualización de sincronización:")
        preview = sync.get_sync_preview()
        print(f"   Descargar: {preview['will_download']} registros")
        print(f"   Subir: {preview['will_upload']} registros")
        print(f"   Conflictos potenciales: {preview['potential_conflicts']}")
        print(f"   Tablas afectadas: {', '.join(preview['tables_affected']) or 'Ninguna'}")
    
    elif args.sync:
        print("\n🔄 Ejecutando sincronización completa...")
        result = sync.full_sync(force=args.force)
        print(f"\n📋 Resultado:")
        print(f"   Éxito: {'✅' if result.success else '❌'}")
        print(f"   Descargados: {result.downloaded}")
        print(f"   Subidos: {result.uploaded}")
        print(f"   Conflictos: {result.conflicts}")
        print(f"   Duración: {result.duration_seconds:.2f}s")
        if result.errors:
            print(f"   Errores: {len(result.errors)}")
            for err in result.errors[:5]:
                print(f"     - {err}")
    
    elif args.download:
        print("\n⬇️ Descargando cambios...")
        result = sync.sync_download()
        print(f"   Descargados: {result.downloaded}")
        print(f"   Éxito: {'✅' if result.success else '❌'}")
    
    elif args.upload:
        print("\n⬆️ Subiendo cambios...")
        result = sync.sync_upload()
        print(f"   Subidos: {result.uploaded}")
        print(f"   Éxito: {'✅' if result.success else '❌'}")
    
    else:
        # Sin argumentos, mostrar status
        status = sync.get_status()
        print(f"\n📊 Estado actual:")
        print(f"   Supabase: {'✅ Conectado' if db.supabase_connected else '❌ Offline'}")
        print(f"   Última sync: {status.last_sync or 'Nunca'}")
        print(f"   Sync necesario: {'Sí' if sync.check_sync_needed() else 'No'}")
        print("\nUso: python sync_manager.py --help")
    
    db.close()
    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
