import json
import pandas as pd
import re
from datetime import datetime
from db_connect import get_supabase_client, get_gspread_client
import gspread
from gspread.utils import rowcol_to_a1

def load_config():
    try:
        with open('config_tables.json', 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

TABLES_CONFIG = load_config()

def find_filter_year_in_header(header_row):
    for cell in header_row:
        val = str(cell).strip()
        if val.isdigit() and len(val) == 4 and 2020 <= int(val) <= 2030: return int(val)
    return None

def refresh_references(spreadsheet, supabase, filter_year=None):
    print(f"🔄 Actualizando Referencias ({filter_year if filter_year else 'Histórico'})...")
    
    # Función auxiliar robusta para escribir en Sheets
    def safe_write(sheet_name, data):
        try:
            try: ws = spreadsheet.worksheet(sheet_name)
            except: ws = spreadsheet.add_worksheet(sheet_name, 100, 15)
            
            ws.clear()
            if len(data) > 0:
                # Usamos range_name='A1' para máxima compatibilidad
                ws.update(range_name='A1', values=data)
            print(f"   ✅ {sheet_name}: {len(data)-1} registros.")
        except Exception as e:
            print(f"   ❌ Error escribiendo en {sheet_name}: {e}")

    # 1. REF_TURNOS
    try:
        res = supabase.table('turnos').select('id_turno, tipo_turno').execute()
        vals = [['tipo_turno', 'id_turno']] + [[t['tipo_turno'], t['id_turno']] for t in res.data]
        safe_write('REF_TURNOS', vals)
    except Exception as e: print(f"   ⚠️ Error descargando TURNOS: {e}")

    # 2. REF_PERSONAL
    try:
        q = supabase.table('datos_personales').select('dni, apellido, nombre, cohorte').order('apellido')
        if filter_year: q = q.eq('cohorte', filter_year)
        res = q.execute()
        
        vals = [['selector_agente', 'dni', 'cohorte']]
        for p in res.data:
            dni = str(p['dni']).strip()
            coh = p['cohorte'] if p['cohorte'] else '?'
            label = f"{p['apellido']}, {p['nombre']} ({coh}) | {dni}"
            vals.append([label, dni, coh])
        safe_write('REF_PERSONAL', vals)
    except Exception as e: print(f"   ⚠️ Error descargando PERSONAL: {e}")

    # 3. REF_ESTADO
    try:
        q = supabase.table('vista_estado_cobertura').select('*')
        if filter_year: q = q.eq('anio', filter_year)
        res = q.execute()
        
        headers = ['fecha', 'anio', 'tipo_turno', 'solicitados', 'cubiertos', 'faltantes', 'estado']
        vals = [headers]
        for r in res.data:
            vals.append([r['fecha'], r['anio'], r['tipo_turno'], r['solicitados'], r['cubiertos'], r['faltantes'], r['estado']])
        safe_write('REF_ESTADO', vals)
    except Exception as e: print(f"   ⚠️ Error descargando ESTADO: {e}")

def get_maps(supabase, table_context, filter_year=None):
    maps = {}
    print("⏳ Cargando mapas...")
    try:
        maps['dias'] = {d['fecha']: d['id_dia'] for d in supabase.table('dias').select('id_dia, fecha').execute().data}
        maps['turnos'] = {t['tipo_turno']: t['id_turno'] for t in supabase.table('turnos').select('id_turno, tipo_turno').execute().data}

        if table_context == 'convocatoria':
            q = supabase.table('datos_personales').select('id_agente, dni')
            if filter_year: q = q.eq('cohorte', filter_year)
            maps['agentes'] = {str(a['dni']).replace('.','').strip(): a['id_agente'] for a in q.execute().data if a['dni']}
            
            plani_data = supabase.table('planificacion').select('id_plani, id_dia, id_turno').execute().data
            maps['planificacion'] = {(p['id_dia'], p['id_turno']): p['id_plani'] for p in plani_data}

            # MAPA OCUPACIÓN
            q_ocup = supabase.table('vista_ocupacion').select('id_agente, fecha, id_turno')
            if filter_year: q_ocup = q_ocup.eq('anio', filter_year)
            maps['ocupacion'] = {}
            for row in q_ocup.execute().data:
                key = (row['id_agente'], row['fecha'])
                if key not in maps['ocupacion']: maps['ocupacion'][key] = set()
                maps['ocupacion'][key].add(row['id_turno'])

    except Exception as e: print(f"⚠️ Error mapas: {e}")
    return maps

def validate_data(row, config):
    for f in config.get("mandatory_fields", []):
        if row.get(f) is None and f != config.get("unique_key"): return False, f"Falta {f}"
    return True, None

def sync_sheet_to_table(sheet_name, table_name):
    print(f"\n--- 🚀 Sincronización Final: {table_name} ---")
    gc, sc = get_gspread_client(), get_supabase_client()
    sh = gc.open(sheet_name)
    
    try: ws = sh.worksheet(table_name)
    except: ws = sh.worksheet(TABLES_CONFIG.get(table_name, {}).get("csv_source_suggestion", "").replace(".csv", ""))
    
    vals = ws.get_all_values()
    if not vals: return
    
    f_year = find_filter_year_in_header(vals[0])
    if not f_year and table_name != 'convocatoria':
        try: f_year = find_filter_year_in_header(sh.worksheet('convocatoria').row_values(1))
        except: pass
    if f_year: print(f"🎯 Año: {f_year}")

    if table_name == 'convocatoria': refresh_references(sh, sc, f_year)
    db_maps = get_maps(sc, table_name, f_year) if table_name in ['planificacion', 'convocatoria'] else {}

    headers = [str(h).lower().strip() for h in vals[0]]
    st_idx = headers.index('sync_status') + 1 if 'sync_status' in headers else len(headers) + 1
    config = TABLES_CONFIG.get(table_name, {})
    conflict = config.get("unique_key")
    if isinstance(conflict, list): conflict = ",".join(conflict)
    
    updates, success, fails = [], 0, 0
    local_ocup = {} 

    for i, row_vals in enumerate(vals[1:], 2):
        if len(row_vals) < len(headers): row_vals += [''] * (len(headers) - len(row_vals))
        row_raw = dict(zip(headers, row_vals))
        row = {}
        
        for k, v in row_raw.items():
            if k in ['sync_status', '']: continue
            val = v if v != "" else None
            if val and config.get("data_types", {}).get(k) == 'date':
                try: val = pd.to_datetime(val, dayfirst=True).strftime('%Y-%m-%d')
                except: pass
            if val and config.get("data_types", {}).get(k) == 'time':
                try: val = pd.to_datetime(str(val).replace('.','').upper()).strftime('%H:%M:%S')
                except: pass
            row[k] = val
        
        if not row: updates.append([""]); continue

        skip, warn = False, ""
        
        if table_name == 'convocatoria':
            dni_raw = str(row.get('agente', '')).split('|')[-1].strip().replace('.', '')
            if dni_raw in db_maps.get('agentes', {}): row['id_agente'] = db_maps['agentes'][dni_raw]
            else: updates.append([f"Error: Agente desconocido"]); fails+=1; continue

            fecha, turno = str(row.get('fecha', '')).split(' ')[0], str(row.get('tipo_turno', '')).strip()
            id_dia, id_turno = db_maps['dias'].get(fecha), db_maps['turnos'].get(turno)
            
            if id_dia and id_turno:
                row['id_turno'] = id_turno
                if (id_dia, id_turno) in db_maps.get('planificacion', {}):
                    row['id_plani'] = db_maps['planificacion'][(id_dia, id_turno)]
                    row['fecha_convocatoria'] = datetime.now().isoformat()
                    
                    key_ocup = (row['id_agente'], fecha)
                    db_turnos = db_maps.get('ocupacion', {}).get(key_ocup, set())
                    if db_turnos and id_turno not in db_turnos: warn = " ⚠️ (Doble Turno DB)"
                    if key_ocup in local_ocup and local_ocup[key_ocup] != id_turno: warn = " ⚠️ (Doble Turno Local)"
                    local_ocup[key_ocup] = id_turno
                else: updates.append([f"Error: No planificado"]); fails+=1; continue
            else: updates.append(["Error: Fecha/Turno inválido"]); fails+=1; continue

        elif table_name == 'planificacion':
            fecha = str(row.get('fecha', '')).split(' ')[0]
            if fecha in db_maps['dias']: row['id_dia'] = db_maps['dias'][fecha]
            else: updates.append(["Error: Fecha"]); fails+=1; continue
            
            turno = str(row.get('tipo_turno', '')).strip()
            if turno in db_maps['turnos']: row['id_turno'] = db_maps['turnos'][turno]
            
            if row.get('hora_inicio') or row.get('hora_fin'):
                row['usa_horario_custom'] = True
                row['motivo_horario_custom'] = "Manual"
            else: row['usa_horario_custom'] = False

        valid, err = validate_data(row, config)
        if valid:
            try:
                payload = {k: v for k, v in row.items() if k not in ['fecha', 'tipo_turno', 'agente', 'hora_inicio', 'hora_fin', 'selector_agente'] and not k.isdigit() and 'filtro' not in k.lower()}
                sc.table(table_name).upsert(payload, on_conflict=conflict).execute()
                updates.append([f"OK{warn}"])
                success += 1
            except Exception as e:
                updates.append([f"DB: {str(e).split('CONTEXT')[0]}"]); fails += 1
        else: updates.append([f"Dato: {err}"]); fails += 1

    if updates:
        try: ws.update(f"{rowcol_to_a1(2, st_idx)}:{rowcol_to_a1(len(vals)+1, st_idx)}", updates)
        except: pass
    print(f"Resumen: {success} OK | {fails} Errores")