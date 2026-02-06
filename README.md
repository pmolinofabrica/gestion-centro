# Sistema de Gestión de Datos Operativos

> Plataforma integral para la gestión del ciclo de vida del dato, desde la captura en interfaces de usuario hasta la persistencia en base de datos relacional.

[![Stack](https://img.shields.io/badge/Stack-Google_Apps_Script_%7C_Supabase_%7C_Python-blue)]()
[![Data Quality](https://img.shields.io/badge/Data_Quality-green)]()

---

## 🎯 Objetivo del Proyecto

Desarrollar un sistema que garantice la **integridad, consistencia y trazabilidad** de los datos operativos de una organización, eliminando la fragmentación típica de los archivos planos gestionados manualmente.

### Problemática Inicial

| Desafío | Impacto |
|---------|---------|
| Datos dispersos en múltiples fuentes | Inconsistencias entre registros |
| Ingreso manual sin validación | Errores de tipeo, duplicados |
| Sin historial de cambios | Imposibilidad de auditoría |
| Consultas complejas imposibles | Decisiones sin soporte analítico |

### Solución Implementada

Arquitectura de tres capas que separa responsabilidades:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Google Sheets  │────▶│  Apps Script    │────▶│    Supabase     │
│    (UI/UX)      │     │  (Middleware)   │     │   (PostgreSQL)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
      Frontend              Lógica                  Backend
```

---

## 📊 Módulos del Sistema

### 1. Datos Maestros (`master_data`)
- Registro de entidades con validación de campos obligatorios
- Clasificación por período/cohorte
- Estado activo/inactivo con trazabilidad temporal

### 2. Planificación de Demanda (`demand_planning`)
- Definición de requerimientos por período/slot
- Cuotas de recursos por categoría
- Sincronización bidireccional UI ↔ Database

### 3. Asignación de Recursos (`resource_allocation`)
- Vinculación de entidades a slots específicos
- Control de estado: vigente, cancelada, completada
- Historial de modificaciones con motivo de cambio

### 4. Gestión de Excepciones (`exception_handling`)
- Registro de eventos atípicos con tipificación
- Documentación de soporte
- Cálculo automático de balances

### 5. Eventos de Desarrollo (`development_events`)
- Registro de sesiones programadas
- Matriz de recursos por evento
- Control de participación y certificaciones
- Vista consolidada: entidades × recursos habilitados

---

## 🔧 Arquitectura Técnica

### Stack Tecnológico

| Capa | Tecnología | Propósito |
|------|------------|-----------|
| Frontend | Google Sheets | Interface familiar para usuarios |
| Middleware | Google Apps Script | Validación, transformación, API calls |
| Backend | Supabase (PostgreSQL) | Persistencia, integridad referencial |
| ETL | Python + Pandas | Migración de datos legacy |

### Principios de Diseño de Datos

1. **Integridad Referencial**: Foreign keys en todas las relaciones
2. **Unicidad Garantizada**: Constraints `UNIQUE` en combinaciones de negocio
3. **Idempotencia**: Operaciones re-ejecutables sin efectos secundarios
4. **Trazabilidad**: Timestamps de creación/modificación en cada registro

### Estructura del Repositorio

```
project/
├── scripts/
│   ├── google_apps/      # Código Apps Script (middleware)
│   └── migrations/       # Scripts de migración legacy
├── sql/
│   ├── schema*.sql       # Definición de estructura
│   ├── functions/        # RPCs y triggers
│   ├── grants/           # Permisos y seguridad
│   └── seeds/            # Datos iniciales
├── etl/                  # 📦 Módulo ETL (ver abajo)
├── docs/                 # Documentación técnica
└── config/               # Configuración del proyecto
```

---

## 📦 Módulo de Ingeniería de Datos & Calidad (ETL)

> Sistema automatizado para migrar registros históricos desde fuentes no estructuradas hacia la arquitectura relacional.

### El Desafío

Datos legacy en hojas de cálculo con:
- **Duplicidad de entidades** por variaciones en identificadores
- **Redundancia transaccional** por errores de copiado
- **Datos sucios** (fechas inválidas, formatos inconsistentes)
- **Falta de relaciones** explícitas entre tablas

### La Solución

Pipeline ETL modular que aplica reglas de negocio antes de la persistencia:

```
etl/
├── config/sources.yaml   # Configuración externalizada
├── src/
│   ├── extractor.py      # Ingesta con deduplicación O(1)
│   ├── transformer.py    # Reglas de negocio
│   └── loader.py         # Generación SQL idempotente
├── scripts/run_migration.py
└── output/               # Artefactos generados
```

### Técnicas Aplicadas

| Técnica | Implementación | Principio |
|---------|----------------|-----------|
| Deduplicación | SET-based para unicidad automática | Unicidad |
| Resolución de conflictos | Excepciones prevalecen sobre actividad | Consistencia |
| SQL Idempotente | `ON CONFLICT DO NOTHING` | Reproducibilidad |
| Transaccionalidad | `BEGIN/COMMIT` para atomicidad | Integridad |

📖 [Documentación completa del módulo ETL](./etl/README.md)

---

## 🚀 Configuración y Uso

### Prerequisitos

```bash
# Python 3.10+
pip install -r requirements.txt

# Variables de entorno
cp .env.example .env
# Configurar DATABASE_URL, API_KEY
```

### Sincronización desde UI

1. Abrir la interfaz de usuario (Google Sheets)
2. Menú personalizado → Seleccionar módulo
3. Los datos se sincronizan automáticamente con el backend

### Migración de Datos Legacy

```bash
cd etl
python scripts/run_migration.py
# Output: output/migration_output.sql
```

---

## 📈 Métricas de Calidad de Datos

| Dimensión | Implementación | Estado |
|-----------|----------------|--------|
| **Integridad** | Foreign keys, NOT NULL | ✅ |
| **Unicidad** | Constraints UNIQUE | ✅ |
| **Consistencia** | Triggers de validación | ✅ |
| **Trazabilidad** | Timestamps, audit logs | ✅ |
| **Accesibilidad** | APIs REST, vistas SQL | ✅ |

---

## 📄 Licencia

Código disponible como referencia técnica para implementaciones similares.

---
