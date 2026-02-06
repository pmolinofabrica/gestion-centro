# Architecture Overview: "Sheets as Interface"

## 1. High-Level Strategy
The project adopts a **"Google Sheets as Interface"** strategy. Instead of a traditional web frontend (React/Next.js), the user interacts directly with Google Sheets for data entry, viewing, and management. Logic and validation are handled by **Google Apps Script (GAS)**, which communicates directly with the **Supabase (PostgreSQL)** backend.

## 2. Technology Stack
- **Frontend / Interface**: Google Sheets
- **Backend Logic**: Google Apps Script (JavaScript ES5/ES6)
- **Database**: Supabase (PostgreSQL)
- **API**: PostgREST (Native Supabase REST API)

## 3. File Structure

```
admin_tools/
├── gas_scripts/           # Google Apps Script files
│   ├── config.gs          # Schema definitions (DAMA validation)
│   ├── sync.gs            # Generic upsert/sync logic
│   ├── download_optimized.gs  # View-based downloads
│   ├── menu_updates.gs    # Custom menu creation
│   ├── cache_manager.gs   # ID-to-name mapping cache
│   ├── Code.gs            # Core functions (REF sheets)
│   ├── sync_*.gs          # Module-specific sync
│   └── download_*.gs      # Module-specific downloads
├── sql/
│   └── dama_implementation_v1.sql  # Tables + Views (main)
└── ARCHITECTURE_OVERVIEW.md  # This file
```

## 4. Database Schema (Supabase)

### Config Tables
| Table | Purpose |
|-------|---------|
| `config_cohorte` | Yearly settings (dates, required hours) |

### Master Data Tables
| Table | Purpose |
|-------|---------|
| `datos_personales` | Resident records |
| `dias` | Calendar with working/holiday flags |
| `turnos` | Turn type definitions |

### Transactional Tables
| Table | Purpose |
|-------|---------|
| `planificacion` | Scheduled turns (slots) |
| `convocatoria` | Turn assignments to residents |
| `inasistencias` | Absences |
| `certificados` | Medical certificates |
| `tardanzas` | Lateness tracking (cycle-based) |

### SQL Views (Read Sources)
| View | Purpose |
|------|---------|
| `vista_saldos_resumen` | Hours balance with smart date logic |
| `vista_seguimiento_residentes` | Per-resident metrics + turn types JSON |
| `vista_estado_cobertura` | Planned vs assigned coverage |
| `vista_inasistencias_completa` | Absences with names |
| `vista_certificados_completa` | Certificates with names |
| `vista_cambios_turno` | Turn change audit trail |

## 5. Key GAS Functions

### Downloads (Supabase → Sheets)
| Function | Target Sheet | Source |
|----------|--------------|--------|
| `loadSeguimientoResidentes()` | SEGUIMIENTO_RESIDENTES | vista_seguimiento_residentes |
| `downloadSaldosResumen()` | SALDOS_RESUMEN | vista_saldos_resumen |
| `loadEstadoCobertura()` | ESTADO_COBERTURA | vista_estado_cobertura |
| `loadDatosPersonales()` | datos_residentes | datos_personales |
| `loadTurnos()` | REF_TURNOS | turnos |

### Sync (Sheets → Supabase)
| Function | Source Sheet | Target Table |
|----------|--------------|--------------|
| `syncConvocatoria()` | CONVOCATORIA | convocatoria |
| `syncInasistencias()` | INASISTENCIAS | inasistencias |
| `syncCertificados()` | CERTIFICADOS | certificados |

## 6. Business Rules

### Tardanzas (Lateness)
- Separate table with cycle-based counting
- Limit: 6 per cycle → triggers action
- Cycles reset after action (6, 12, 18...)

### Saldos (Hours Balance)
- `horas_objetivo_mes`: Calculated from `config_cohorte` + `fecha_alta/baja`
- Accumulated columns for running totals
- Color: Green = owes hours (good), Red = exceeded (attention)

### Inasistencias (Absences)
- Types: médico (15 max), estudio, imprevisto (1/month)
- Limit: 24 justified + 4 unjustified

## 7. Deprecated Paths
> [!WARNING]
> Do not use these directories:
> - `frontend/`, `legacy_frontend_v1/`, `app/`, `components/`

## 8. Python Scripts
Secondary use for bulk migration/analysis. Primary interface is GAS.
