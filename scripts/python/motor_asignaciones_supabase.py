import os
import json
from supabase import create_client, Client

# ==============================================================================
# CONFIGURACIÓN Y CONEXIÓN
# ==============================================================================
CONFIG_PATH = "../../config/supabase.json"

def get_supabase_client() -> Client:
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        
        # Usamos SERVICE ROLE KEY para poder bypasear RLS durante el batch job en background
        url: str = f"https://{config['project_url']}"
        key: str = config['service_role_key']
        return create_client(url, key)
    except Exception as e:
        print(f"Error fatal conectando a Supabase: {e}")
        exit(1)

supabase = get_supabase_client()

# ==============================================================================
# PIPELINE DE EXTRACCIÓN (FETCH)
# ==============================================================================

def fetch_data(mes_objetivo="03-2026", anio_cohorte=2026):
    print(f"--- INICIANDO EXTRACCIÓN DE DATOS DESDE SUPABASE (Cohorte {anio_cohorte}) ---")
    
    # 1. Traer Residentes Activos de la cohorte
    res_residentes = supabase.table("datos_personales").select("id_agente, nombre, apellido").eq("activo", True).eq("cohorte", anio_cohorte).execute()
    residentes = res_residentes.data
    print(f"✅ Residentes activos cargados: {len(residentes)}")
    
    # 2. Traer Dispositivos Operativos (incluyendo cupos variables)
    res_dispo = supabase.table("dispositivos").select("id_dispositivo, nombre_dispositivo, cupo_optimo").eq("activo", True).execute()
    dispositivos = res_dispo.data
    # Creamos lookup tables para agilizar el cruce ID <-> Data
    dispo_data = {d["id_dispositivo"]: {"nombre": d["nombre_dispositivo"], "cupo": d.get("cupo_optimo", 1) or 1} for d in dispositivos}
    print(f"✅ Dispositivos operativos cargados: {len(dispositivos)}")

    month, year = mes_objetivo.split("-")
    fecha_inicio = f"{year}-{month}-01"
    fecha_fin = f"{year}-{month}-31" 
    
    # NUEVO: Traer excepciones de cupos por dia (calendario_dispositivos) filtrando solo el mes objetivo
    res_calendario = supabase.table("calendario_dispositivos").select("id_dispositivo, fecha, cupo_objetivo").gte("fecha", fecha_inicio).lte("fecha", fecha_fin).execute()
    cupos_por_fecha = {}
    for row in res_calendario.data:
        ft = row["fecha"]
        did = row["id_dispositivo"]
        cupo_val = row["cupo_objetivo"]
        if ft not in cupos_por_fecha:
            cupos_por_fecha[ft] = {}
        cupos_por_fecha[ft][did] = cupo_val
    print(f"✅ Cupos dinámicos por fecha cargados: {len(res_calendario.data)}")

    # 3. Traer Matriz de Capacitaciones Aprobadas (Completa vía Relaciones)
    print("⏳ Procesando Matriz temporal jerárquica de Capacitaciones -> Dispositivos ...")
    
    # Traer fechas base de capacitaciones vinculándolas con la tabla días (días reales del evento, no de subida de datos)
    res_cap_fechas = supabase.table("capacitaciones").select("id_cap, id_dia, grupo").execute()
    
    import requests
    
    ids_dias = list(set([str(c["id_dia"]) for c in res_cap_fechas.data if c.get("id_dia")]))
    ids_dias_str = ",".join(ids_dias)
    
    dias_resp = []
    if ids_dias_str:
        dias_resp = requests.get(
            f"{supabase.supabase_url}/rest/v1/dias?select=id_dia,fecha&id_dia=in.({ids_dias_str})",
            headers={"apikey": supabase.supabase_key, "Authorization": f"Bearer {supabase.supabase_key}"}
        ).json()
        
    dias_dict = {d["id_dia"]: d["fecha"][:10] for d in dias_resp if isinstance(d, dict) and d.get("fecha")}
    
    fechas_cap = {c["id_cap"]: dias_dict.get(c.get("id_dia"), '1900-01-01') for c in res_cap_fechas.data}

    # 3.1. Qué capacitan para qué Dispositivos: {id_cap: [id_dispositivo1, id_dispositivo2]}
    res_cap_dispo = supabase.table("capacitaciones_dispositivos").select("id_cap, id_dispositivo").execute()
    cap_to_dispo = {}
    for drow in res_cap_dispo.data:
        cid = drow["id_cap"]
        did = drow["id_dispositivo"]
        if cid not in cap_to_dispo: cap_to_dispo[cid] = []
        cap_to_dispo[cid].append(did)

    # 3.2. A qué capacitaciones Asistió cada agente:
    res_caps = supabase.table("capacitaciones_participantes").select("id_agente, id_cap").eq("asistio", True).execute()
    
    # Mapeamos a un diccionario {id_agente: {id_dispositivo: fecha_aprobacion}}
    caps_por_agente = {r["id_agente"]: {} for r in residentes}
    
    for row in res_caps.data:
        agente_id = row['id_agente']
        id_cap = row['id_cap']
        fecha_cap = fechas_cap.get(id_cap, '1900-01-01')
        
        if agente_id in caps_por_agente:
            # Si la capacitacion habilitaba dispositivos, se los otorgamos al residente guardando la fecha
            if id_cap in cap_to_dispo:
                 for did in cap_to_dispo[id_cap]:
                     if did not in caps_por_agente[agente_id] or caps_por_agente[agente_id][did] > fecha_cap:
                         caps_por_agente[agente_id][did] = fecha_cap
                         
    print(f"✅ Matriz DAMA temporal de Dispositivos Autorizados procesada.")
    
    # Printeo un par de ejemplos para debuggeo
    print("\nEjemplos de residentes (Fechas Aprobación):")
    for r in residentes[:3]:
        nombres_fechas = [f"{dispo_data.get(did, {}).get('nombre', 'Unknown')} ({fecha})" for did, fecha in caps_por_agente[r['id_agente']].items()]
        print(f" - {r['apellido']} {r['nombre']} -> Puede operar: {nombres_fechas}")

    # 4. Traer Convocatorias reales del Mes (cruzando planificacion -> dias)
    print("⏳ Procesando Convocatorias mensuales ...")
    # 4.a Mapear dia a id_dia
    res_dias = supabase.table("dias").select("id_dia, fecha").gte("fecha", fecha_inicio).lte("fecha", fecha_fin).execute()
    id_dia_to_fecha = {d["id_dia"]: d["fecha"] for d in res_dias.data}
    
    # 4.b Traer ID turnos asociados a Apertura al Publico
    res_turnos = supabase.table("turnos").select("id_turno").ilike("tipo_turno", "%apertura%").execute()
    ids_aperturas = [t["id_turno"] for t in res_turnos.data]

    # 4.c Mapear planificacion a fecha (Filtrando ESTRICTAMENTE turnos de Apertura)
    if not id_dia_to_fecha:
        print("⚠ No hay fechas cargadas en Supabase para el rango seleccionado.")
        return residentes, dispo_data, caps_por_agente, {}
        
    res_plani = supabase.table("planificacion")\
        .select("id_plani, id_dia")\
        .in_("id_dia", list(id_dia_to_fecha.keys()))\
        .in_("id_turno", ids_aperturas)\
        .execute()
        
    id_plani_to_fecha = {p["id_plani"]: id_dia_to_fecha[p["id_dia"]] for p in res_plani.data}

    # 4.d Traer las convocatorias que correspondan a esas planificaciones
    if not id_plani_to_fecha:
        print("⚠ No hay planificaciones cargadas en Supabase para el rango seleccionado.")
        return residentes, dispo_data, caps_por_agente, {}
        
    res_convos = supabase.table("convocatoria")\
        .select("id_convocatoria, id_agente, id_plani")\
        .eq("estado", "vigente")\
        .eq("turno_cancelado", False)\
        .in_("id_plani", list(id_plani_to_fecha.keys()))\
        .execute()
        
    convocatorias_por_dia = {}
    for row in res_convos.data:
        dia_completo = id_plani_to_fecha[row["id_plani"]] # Ej: "2026-03-05"
        dia = dia_completo.split("-")[2]         # Nos quedamos con "05"
        if dia not in convocatorias_por_dia:
            convocatorias_por_dia[dia] = {}
        # Mapeamos {dia: {id_agente: id_convocatoria}}
        convocatorias_por_dia[dia][row["id_agente"]] = row["id_convocatoria"]
        
    print(f"✅ Convocatorias del mes procesadas (Lectura DAMA): {len(res_convos.data)} turnos en total.")

    # 5. Traer Inasistencias del mes (Hard Constraint D)
    res_inasistencias = supabase.table("inasistencias").select("id_agente, fecha_inasistencia").gte("fecha_inasistencia", fecha_inicio).lte("fecha_inasistencia", fecha_fin).execute()
    inasistencias_por_dia = {}
    for row in res_inasistencias.data:
        dia_ina = row["fecha_inasistencia"]
        if dia_ina not in inasistencias_por_dia:
            inasistencias_por_dia[dia_ina] = set()
        inasistencias_por_dia[dia_ina].add(row["id_agente"])
    print(f"✅ Inasistencias del mes cargadas: {len(res_inasistencias.data)}")

    # 6. Pre-cargar historial existente del mes desde Menu (para no partir de cero)
    res_menu_previo = supabase.table("menu").select("id_agente, id_dispositivo, fecha_asignacion").gte("fecha_asignacion", fecha_inicio).lte("fecha_asignacion", fecha_fin).execute()
    historial_previo = {}
    carga_global_previa = {}
    for row in res_menu_previo.data:
        aid = row["id_agente"]
        did = row["id_dispositivo"]
        if did == 999:
            continue  # No contar descanso como asignación
        if aid not in historial_previo:
            historial_previo[aid] = {}
        historial_previo[aid][did] = historial_previo[aid].get(did, 0) + 1
        carga_global_previa[aid] = carga_global_previa.get(aid, 0) + 1
    print(f"✅ Historial previo del mes cargado: {len(res_menu_previo.data)} filas")

    return residentes, dispo_data, caps_por_agente, convocatorias_por_dia, cupos_por_fecha, inasistencias_por_dia, historial_previo, carga_global_previa


if __name__ == "__main__":
    pass  # Evitar que se ejecute dos veces en imports
import random

# ==============================================================================
# ALGORITMO CORE: ASIGNACIÓN AUTOMÁTICA
# ==============================================================================

def execute_assignment_engine(residentes, dispo_data, caps_por_agente, convocatorias_por_dia, mes_objetivo, dias_del_mes, cupos_por_fecha, inasistencias_por_dia, historial_previo, carga_global_previa):
    print("\n--- INICIANDO MOTOR DE ASIGNACIONES v2.0 (PRODUCCIÓN) ---")

    # Helper auxiliar para obtener el cupo real de un dispositivo en un día
    def get_cupo(dispo_id, fecha_str):
        if fecha_str in cupos_por_fecha and dispo_id in cupos_por_fecha[fecha_str]:
            return cupos_por_fecha[fecha_str][dispo_id]
        return 0  # No inventar cupos si el usuario no los definió explícitamente
    
    # 2. Setup del Tracking Historico y Resultados (con historial previo pre-cargado)
    historial_rotacion = {r["id_agente"]: {d: 0 for d in dispo_data.keys()} for r in residentes}
    carga_global = {r["id_agente"]: 0 for r in residentes}
    
    # Pre-cargar historial y carga global desde datos existentes del mes
    for aid, dispos in historial_previo.items():
        if aid in historial_rotacion:
            for did, count in dispos.items():
                if did in historial_rotacion[aid]:
                    historial_rotacion[aid][did] = count
    for aid, count in carga_global_previa.items():
        if aid in carga_global:
            carga_global[aid] = count
    
    grilla_resultados = {dia: {d: [] for d in dispo_data.keys()} for dia in dias_del_mes}
    
    # KPIs Log
    estadistica_huecos = {dia: 0 for dia in dias_del_mes}
    estadistica_libres = {dia: 0 for dia in dias_del_mes}

    # 3. Iteración principal cronológica (Día por Día)
    for dia in dias_del_mes:
        print(f" > Calculando Cruces para el {dia}/{mes_objetivo} ... ", end="")
        
        # 3.a Calculo de la demanda diaria dinamica
        agentes_convocados = [res for res in residentes if res["id_agente"] in convocatorias_por_dia.get(dia, {})]
        total_convocados_hoy = len(agentes_convocados)
        
        mes, anio = mes_objetivo.split("-")
        fecha_asignacion = f"{anio}-{mes}-{dia}"
        
        dispositivos_viables = []
        for did, ddata in dispo_data.items():
            aptos = [r for r in agentes_convocados if caps_por_agente.get(r["id_agente"], {}).get(did) and caps_por_agente[r["id_agente"]][did] <= fecha_asignacion]
            if len(aptos) > 0:
                dispositivos_viables.append({
                    "id": did,
                    "score": len(aptos)  # Para priorizar dispositivos con más gente capacitada si empata
                })
                
        # Ordenamos los dispositivos por ESCASEZ (menos gente capacitada primero = más urgentes)
        dispositivos_viables.sort(key=lambda x: x["score"])
        dispositivos_viables = [x["id"] for x in dispositivos_viables]
                
        demandas_del_dia = {did: 0 for did in dispo_data.keys()}
        plazas_a_repartir = total_convocados_hoy
        
        # Primero aseguramos al menos 1 plaza para cada dispositivo donde haya alguien capacitado
        for did in dispositivos_viables:
            cupo_real = get_cupo(did, fecha_asignacion)
            if plazas_a_repartir > 0 and demandas_del_dia[did] < cupo_real:
                demandas_del_dia[did] = 1
                plazas_a_repartir -= 1
                
        # Luego repartimos el excedente de personal hasta alcanzar el cupo optimo de todos los abiertos
        for did in dispositivos_viables:
            cupo_real = get_cupo(did, fecha_asignacion)
            while plazas_a_repartir > 0 and demandas_del_dia[did] < cupo_real:
                demandas_del_dia[did] += 1
                plazas_a_repartir -= 1
                
        asignados_hoy = set()
                
        # Evaluamos para este Día cuántas personas hay capacitadas y convocadas para cada Dispositivo
        escasez_por_dispo = {}
        for d in demandas_del_dia.keys():
            aptos = 0
            for r in residentes:
                rid = r["id_agente"]
                fcap = caps_por_agente.get(rid, {}).get(d)
                if fcap and fcap <= f"{mes_objetivo.split('-')[1]}-{mes_objetivo.split('-')[0]}-{dia}":
                    if rid in convocatorias_por_dia.get(dia, {}):
                        aptos += 1
            escasez_por_dispo[d] = aptos
            
        # Ordenamos los dispositivos: primero los que tienen MENOS personas capacitadas (Más urgentes/difíciles)
        # y filtramos aquellos que no requieren plazas
        dispos_ordenados = [d for d, req in demandas_del_dia.items() if req > 0]
        dispos_ordenados.sort(key=lambda d: escasez_por_dispo[d])
        
        for target_dispo_id in dispos_ordenados:
            plazas_requeridas = demandas_del_dia[target_dispo_id]
            
            dispo_nombre = dispo_data[target_dispo_id]["nombre"]
            
            for p in range(plazas_requeridas):
                candidatos_aptos = []
                
                # Evaluación de todo el array de residentes contra los constraints
                for res in residentes:
                    agente_id = res["id_agente"]
                    
                    # HARD Constraint A: Sin Doble Asignación diurna
                    if agente_id in asignados_hoy:
                        continue
                        
                    # HARD Constraint B: Debe estar CONVOCADO hoy
                    if agente_id not in convocatorias_por_dia.get(dia, {}):
                        continue
                        
                    # HARD Constraint C: Capacitación estricta y Temporal DAMA
                    fecha_capacitacion = caps_por_agente.get(agente_id, {}).get(target_dispo_id)
                    
                    mes, anio = mes_objetivo.split("-")
                    fecha_asignacion = f"{anio}-{mes}-{dia}"
                    
                    is_capacitado_a_tiempo = fecha_capacitacion and fecha_capacitacion <= fecha_asignacion
                    if not is_capacitado_a_tiempo:
                        continue
                        
                    # HARD Constraint D: NO asignar si tiene Inasistencia hoy
                    if agente_id in inasistencias_por_dia.get(dia, set()):
                        continue
                        
                    # SOFT Constraint: Sistema de Puntajes Multicriterio
                    random.seed(f"{dia}-{agente_id}-{target_dispo_id}")  # Reproducible
                    pts = 1000
                    pts -= 500 * historial_rotacion[agente_id][target_dispo_id]  # Penalizar repetición en ESTE dispositivo
                    pts -= 80 * carga_global.get(agente_id, 0)                   # Penalizar carga global
                    pts += random.randint(0, 5)                                   # Tie-breaker reproducible
                    
                    candidatos_aptos.append({
                        "id": agente_id,
                        "nombre": f"{res['nombre']} {res['apellido']}",
                        "score": pts
                    })
                
                if not candidatos_aptos:
                    estadistica_huecos[dia] += 1
                    # print(f"  [!] Fallo Dispositivo {dispo_nombre}. Nadie capacitado.")
                else:
                    candidatos_aptos.sort(key=lambda x: x["score"], reverse=True)
                    ganador = candidatos_aptos[0]
                    
                    # Commit de la asignación
                    asignados_hoy.add(ganador["id"])
                    grilla_resultados[dia][target_dispo_id].append({"id": ganador["id"], "score": ganador["score"]})
                    historial_rotacion[ganador["id"]][target_dispo_id] += 1
                    carga_global[ganador["id"]] = carga_global.get(ganador["id"], 0) + 1
        
        # Guardamos cuantos P0 hubo
        estadistica_libres[dia] = len([r for r in residentes if r["id_agente"] not in asignados_hoy])
        print("OK")
        
    return grilla_resultados, estadistica_huecos, estadistica_libres


import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Motor IA de Asignaciones Diarias")
    parser.add_argument("--start-date", type=str, help="Fecha mínima YYYY-MM-DD para forzar cálculo y omitir historia.", default=None)
    args = parser.parse_args()

    mes_target = "03-2026"
    
    residentes, dispo_data, caps_por_agente, convocatorias_por_dia, cupos_por_fecha, inasistencias_por_dia, historial_previo, carga_global_previa = fetch_data(mes_objetivo=mes_target, anio_cohorte=2026)
    
    # Derivación dinámica DAMA de los días a procesar (Lo que haya bajado de Google Sheets)
    test_days = sorted(list(convocatorias_por_dia.keys()))
    if not test_days:
        print("⚠ ERROR: No se detectaron convocatorias para ningún día en la base de datos.")
        exit(1)

    if args.start_date:
        print(f" > Atención IA: Argumento Start-Date recibido. Calculando SÓLO a partir de {args.start_date}")
        y_m = mes_target.split("-")
        test_days = [d for d in test_days if f"{y_m[1]}-{y_m[0]}-{d}" >= args.start_date]
        
    print(f"\n✅ Días a procesar evaluados y filtrados: {test_days}")
    
    resultados, m_huecos, m_libres = execute_assignment_engine(
        residentes, dispo_data, caps_por_agente, convocatorias_por_dia, mes_target, test_days, cupos_por_fecha, inasistencias_por_dia, historial_previo, carga_global_previa
    )
    print("\n=== METRICAS DE ASIGNACIÓN ===\n")
    for d in test_days:
        print(f"Día {d}: Dispositivos sin cubrir: {m_huecos[d]} | Personal en Base T1: {m_libres[d]}")
        
    print("\n⏳ Subiendo plan mensual a Supabase (Tabla MENU - DAMA)...")
    batch_insert_payload = []
    
    for dia in test_days:
        day_str = dia
        month_year = mes_target.split("-")
        fecha_sql = f"{month_year[1]}-{month_year[0]}-{day_str}"
        
        asignados_hoy = set()
        
        # 1. Agentes Asignados
        for dispo_id, listado_agentes in resultados[dia].items():
            for agente_obj in listado_agentes:
                agente_id = agente_obj["id"]
                score = agente_obj["score"]
                
                asignados_hoy.add(agente_id)
                id_conv = convocatorias_por_dia.get(dia, {}).get(agente_id)
                if id_conv:
                    batch_insert_payload.append({
                        "id_convocatoria": id_conv,
                        "id_dispositivo": dispo_id,
                        "id_agente": agente_id,
                        "fecha_asignacion": fecha_sql,
                        "estado_ejecucion": "planificado",
                        "orden": max(1, score)
                    })
                    
        # 2. Agentes Convocados pero NO Asignados (Descanso / Pool P0)
        convocados_dia = convocatorias_por_dia.get(dia, {})
        for agente_id, id_conv in convocados_dia.items():
            if agente_id not in asignados_hoy:
                batch_insert_payload.append({
                    "id_convocatoria": id_conv,
                    "id_dispositivo": 999,
                    "id_agente": agente_id,
                    "fecha_asignacion": fecha_sql,
                    "estado_ejecucion": "planificado"
                })
                
    if len(batch_insert_payload) > 0:
        try:
            supabase.table("menu").insert(batch_insert_payload).execute()
            print(f"✅ ¡Éxito! {len(batch_insert_payload)} turnos publicados en UI Movimientos.")
        except Exception as e:
            print(f"❌ Error al impactar Supabase: {e}")
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                print("   Info: Los registros ya existían en BD. Omita error.")
    else:
         print("⚠ No hay turnos validos para asignar.")
