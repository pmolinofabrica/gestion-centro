# Gestión Centro - El Molino Fábrica Cultural

Sistema experto de gestión y optimización de recursos humanos para dispositivos de mediación cultural. Este proyecto utiliza un motor de asignación basado en Python (Heurísticas de Scoring) y una interfaz reactiva en Next.js conectada a Supabase.

## 🚀 Arquitectura del Proyecto

- **Frontend**: [Next.js](https://nextjs.org/) + [React](https://react.dev/) + [Tailwind CSS](https://tailwindcss.com/)
- **Base de Datos**: [Supabase](https://supabase.com/) (PostgreSQL) con disparadores automáticos (Triggers) para acreditación de capacitaciones.
- **Motor de Asignación**: Scripts de [Python](https://www.python.org/) que procesan el ranking de residentes y generan las planificaciones mensuales.

## 📁 Estructura de Directorios

- `/frontend`: Aplicación web principal (Matriz de Planificación y Apertura).
- `/scripts/python`: El "Cerebro" del sistema. Contiene el motor y scripts de mantenimiento.
- `/sql`: Esquemas y migraciones de la base de datos Supabase.
- `/knowledge_base`: Documentación detallada del proyecto (Arquitectura DAMA).

## 🛠️ Configuración Rápida

### Requisitos
- Node.js v18+
- Python 3.10+
- Acceso a una instancia de Supabase.

### Instalación de Frontend
```bash
cd frontend
npm install
npm run dev
```

### Ejecutar el Motor Python
```bash
# Requiere archivo config/supabase.json con service_role_key
cd scripts/python
python motor_asignacion_apertura5.py
```

## 📖 Documentación Interna (Obsidian)
Para una inmersión profunda en la lógica del sistema, consulta los archivos en `/knowledge_base`:
- `Fase_1_Datos_y_Supabase.md`: Modelo ER y Triggers.
- `Fase_2_Motor_Python.md`: Lógica de Scoring y Heurísticas.
- `Fase_3_Frontend_y_UX.md`: Guía de componentes y sistema de diseño.

---
> [!IMPORTANT]
> Este repositorio está preparado siguiendo principios DAMA para asegurar la integridad de los datos y facilidad de colaboración.
