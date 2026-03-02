# 🏛️ Centro Cultural - Knowledge Base

Bienvenido a la base de conocimiento (Obsidian Vault) del proyecto de Gestión del Centro Cultural. 

## 📓 Punto de Partida y Errores Comunes
- **[[lecciones_aprendidas_stack|Lecciones Aprendidas (Gotchas)]]**: Imprescindible leer y actualizar esto antes de empezar una nueva feature o para documentar un nuevo "Pain point".

## 📚 Reglas del Sistema y Arquitectura (.ai_context)
Para conocer los pilares del desarrollo de este sistema:
- **Modelo de Datos RRHH**: [[../.ai_context/03_schema_rrhh|Esquema de RRHH Base]]
- **Estilo Frontend (Google Apps Script)**: [[../.ai_context/01_gas_frontend|Frontend GAS y Formularios]]
- **Tácticas de Backend (Supabase RPC)**: [[../.ai_context/02_supabase_rpc|Uso de RPCs y Transacciones]]
- **Gobierno DAMA (Calidad de Datos)**: [[../.ai_context/06_dama_governance|Gobierno de Datos]]
- **Sistema de Horas**: [[../.ai_context/05_hybrid_timezone|Manejo Híbrido de Timezones]]
- **Buenas prácticas SQL**: [[../.ai_context/postgres_expert|Postgres Expert Guidelines]]

## 📂 Visión de la Estructura en el Servidor
- `/scripts/google_apps/`: Código Frontend (Google Sheets / HtmlService).
- `/scripts/python/`: Scripts de migración, conexiones asíncronas y transformaciones complejas.
- `/config/`: Archivos de configuración centralizados (ej. `supabase.json`).
- `/.ai_context/`: Contexto duro (y principal) utilizado por los asistentes de inteligencia artificial.

## 🚀 Próximos módulos activos
*(Aquí listaremos en el futuro los issues o módulos en los que estamos trabajando, uniendo las Reglas de Negocio reales -ej. lógicas de 'Residentes'- con los esquemas técnicos).*

---
*Tags:* #dashboard #home #arquitectura
