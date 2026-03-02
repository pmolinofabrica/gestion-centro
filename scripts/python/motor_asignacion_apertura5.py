import json
import requests
from collections import defaultdict
from datetime import datetime

import os

CONFIG_FILE = os.environ.get('SUPABASE_CONFIG_PATH', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'supabase.json'))

def get_base():
    with open(CONFIG_FILE, 'r') as f: config = json.load(f)
    b = config.get('project_url')
    if not b.startswith('http'): b = 'https://' + b
    if 'db.' in b and '.supabase.co' in b: b = b.replace('db.', '')
    k = config.get('service_role_key')
    return b, {"apikey": k, "Authorization": f"Bearer {k}", "Content-Type": "application/json"}

def obtener_cupos(fecha_str, dispo_nombre):
    nombre = dispo_nombre.upper()
    if fecha_str in ["2026-03-07", "2026-03-08"]:
        # "Sector de lectura, rio de juegos m., rio de juegos t., autoretratate" a 1 cupo.
        # "Los demás los dejamos en 2 según el cálculo original que eran 2 residentes por dispositivo para llegar a 24 (10x2=20 + 4x1=4 = 24 residentes)"
        # El usuario menciona: "(entiendo que 10, de los 14 disponibles vamos a dejar 1 residente en: sector de lectura, rio de juegos m., rio de juegos t., autoretratate)"
        simples = ["SECTOR DE LECTURA", "RÍO DE JUEGOS M.", "RÍO DE JUEGOS T.", "AUTORRETRATATE"]
        if nombre in simples:
            return 1, 1
        else:
            return 2, 2
    else:
        # Para el RESTO DEL MES (a partir del 14/3)
        # El usuario especifica:
        # "los dispositivos que tendran dos residentes son: tarima de pintura, mesa de pintura."
        # "Los que podrian tener 2 (en caso de ser necesario) son: batik, sector de convivencia, fabrica de papel, mesa de ensamble."
        dobles_fijos = ["TARIMA DE PINTURA", "MESA DE PINTURA"]
        dobles_opcionales = ["BATIK", "SECTOR DE CONVIVENCIA", "FÁBRICA DE PAPEL", "MESA DE ENSABLE"]
        
        if nombre in dobles_fijos:
            return 2, 2
        elif nombre in dobles_opcionales:
            return 1, 2
        else:
            return 1, 1

def generar_matriz_markdown():
    b, h = get_base()
    
    # 1. Traer Capacitaciones
    r_cap = requests.get(f"{b}/rest/v1/vista_historial_capacitaciones?estado_asistencia=eq.S%C3%AD", headers=h)
    historial = r_cap.json()
    
    caps_agente = defaultdict(dict)
    dispo_fecha_apertura = {} 
    
    for row in historial:
        agente = row['id_agente']
        dispo = row['id_dispositivo']
        fecha = row['fecha_capacitacion']
        caps_agente[agente][dispo] = fecha
        
        if dispo not in dispo_fecha_apertura:
            dispo_fecha_apertura[dispo] = fecha
        elif fecha < dispo_fecha_apertura[dispo]:
            dispo_fecha_apertura[dispo] = fecha
            
    # 2. Convocatorias (Solo fines de semana, sin 1/3, EXCLUYENDO DESCANSO (id_turno = 20))
    # NOTA: En vista_convocatoria_completa no podemos filtrar directo por texto sin URL encode seguro,
    # filtramos en memoria los id_turno == 20 ("Descanso") o por nombre.
    url_conv = f"{b}/rest/v1/vista_convocatoria_completa?anio=eq.2026&mes=eq.3&fecha_turno=neq.2026-03-01&order=fecha_turno.asc"
    r_conv = requests.get(url_conv, headers=h)
    convocatorias = r_conv.json()
    
    convocados_por_dia = defaultdict(set)
    dias_ordenados = set()
    nombres = {} 
    todos_agentes = set()
    
    for row in convocatorias:
        fecha = row['fecha_turno']
        agente = row['id_agente']
        turno_id = row['id_turno']
        
        # Filtramos explícitamente DESCANSO
        if turno_id == 20 or str(row.get('tipo_turno', '')).lower() == 'descanso':
            continue
            
        dt = datetime.strptime(fecha, "%Y-%m-%d")
        if dt.weekday() >= 5: 
            convocados_por_dia[fecha].add(agente)
            dias_ordenados.add(fecha)
            nombres[agente] = row['agente'].split(',')[0]
            todos_agentes.add(agente)

    dias_ordenados = sorted(list(dias_ordenados))
    
    # 3. Dispositivos (Traemos también el piso para ordenar)
    r_disp = requests.get(f"{b}/rest/v1/dispositivos?select=id_dispositivo,nombre_dispositivo,piso_dispositivo&activo=eq.true", headers=h)
    dispositivos_base = {d['id_dispositivo']: d['nombre_dispositivo'] for d in r_disp.json()}
    dispositivos_piso = {d['id_dispositivo']: (d.get('piso_dispositivo') or 0) for d in r_disp.json()}
    
    # Simular Capacitaciones Plan 2
    nuevos = {
        "2026-03-10": ["GUNTA", "TELA COLECTIVA"],
        "2026-03-11": ["TRAJE DE LAS FORMAS", "TOCO MADERA", "GIOCONDA", "SECTOR DE DISEÑO"],
        "2026-03-20": ["LOS PAPELES DE TU VIDA", "SASHIKO"]
    }
    nombre_a_id = {v.upper(): k for k, v in dispositivos_base.items()}
    for fecha, noms in nuevos.items():
        for nom in noms:
            d_id = nombre_a_id.get(nom)
            if d_id:
                dispo_fecha_apertura[d_id] = fecha
                for ag in todos_agentes:
                    caps_agente[ag][d_id] = fecha

    # Rotacion
    historial_rotacion = defaultdict(list)
    historial_dias_operados = defaultdict(list) 
    asignaciones_finales = defaultdict(lambda: defaultdict(list))
    
    dispos_potenciales = list(dispo_fecha_apertura.keys())
    # Ordenamos por piso numerico (ascendente) y luego alfabéticamente por nombre
    dispos_potenciales.sort(key=lambda x: (dispositivos_piso.get(x, 99), dispositivos_base.get(x, "")))

    for fecha in dias_ordenados:
        convocados_hoy = list(convocados_por_dia[fecha])
        dispos_hoy_base = [d for d in dispos_potenciales if dispo_fecha_apertura[d] < fecha]
        
        # HEURÍSTICA DE ESCASEZ: Ordenar los dispositivos de hoy según cuántos convocados saben usarlos
        # Los que tienen menos gente capacitada (más "escasos") eligen candidato primero
        def contar_capacitados(d_id):
            c = 0
            for a_id in convocados_hoy:
                f_cap = caps_agente.get(a_id, {}).get(d_id)
                if f_cap and f_cap < fecha: c += 1
            return c
            
        dispos_hoy = sorted(dispos_hoy_base, key=lambda d: contar_capacitados(d))
        
        ocupacion = {d: 0 for d in dispos_hoy}
        cupos = {d: obtener_cupos(fecha, dispositivos_base.get(d)) for d in dispos_hoy}
        
        print(f"[{fecha}] Convocados Efectivos (Sin Descanso): {len(convocados_hoy)}")
        
        # FASE 1: CUPO MÍNIMO
        while convocados_hoy:
            mejor_global = None 
            for dispo_id in dispos_hoy:
                if ocupacion[dispo_id] < cupos[dispo_id][0]:
                    for agente_id in convocados_hoy:
                        fecha_capStr = caps_agente.get(agente_id, {}).get(dispo_id)
                        if not fecha_capStr or fecha_capStr >= fecha: continue
                        
                        puntaje = 1000 - (historial_rotacion[agente_id].count(dispo_id) * 400) - (len(historial_dias_operados[agente_id]) * 100)
                        if not mejor_global or puntaje > mejor_global[0]: mejor_global = (puntaje, agente_id, dispo_id)
            if mejor_global:
                p, a_id, d_id = mejor_global
                asignaciones_finales[fecha][d_id].append((a_id, p)); ocupacion[d_id] += 1; historial_rotacion[a_id].append(d_id); historial_dias_operados[a_id].append(fecha)
                convocados_hoy.remove(a_id)
            else: break
                
        # FASE 2: CUPO MÁXIMO
        while convocados_hoy:
            mejor_global = None 
            for dispo_id in dispos_hoy:
                if ocupacion[dispo_id] < cupos[dispo_id][1]:
                    for agente_id in convocados_hoy:
                        fecha_capStr = caps_agente.get(agente_id, {}).get(dispo_id)
                        if not fecha_capStr or fecha_capStr >= fecha: continue
                        
                        puntaje = 1000 - (historial_rotacion[agente_id].count(dispo_id) * 400) - (len(historial_dias_operados[agente_id]) * 100)
                        if not mejor_global or puntaje > mejor_global[0]: mejor_global = (puntaje, agente_id, dispo_id)
            if mejor_global:
                p, a_id, d_id = mejor_global
                asignaciones_finales[fecha][d_id].append((a_id, p)); ocupacion[d_id] += 1; historial_rotacion[a_id].append(d_id); historial_dias_operados[a_id].append(fecha)
                convocados_hoy.remove(a_id)
            else: break
            
        # FASE 3: EMERGENCIA
        while convocados_hoy:
            mejor_global = None 
            for dispo_id in dispos_hoy:
                for agente_id in convocados_hoy:
                    fecha_capStr = caps_agente.get(agente_id, {}).get(dispo_id)
                    if not fecha_capStr or fecha_capStr >= fecha: continue
                    puntaje = 1000 - (ocupacion[dispo_id] * 200) - (historial_rotacion[agente_id].count(dispo_id) * 400)
                    if not mejor_global or puntaje > mejor_global[0]:
                        mejor_global = (puntaje, agente_id, dispo_id)
            if mejor_global:
                p, a_id, d_id = mejor_global
                asignaciones_finales[fecha][d_id].append((a_id, p)); ocupacion[d_id] += 1; historial_rotacion[a_id].append(d_id); historial_dias_operados[a_id].append(fecha)
                convocados_hoy.remove(a_id)
            else: 
                break
                
        if convocados_hoy:
            for sobP in convocados_hoy: asignaciones_finales[fecha][-1].append((sobP, 0))

    # OUTPUT MARKDOWN
    headers = ["Dispositivo / Cupo"] + [datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m") for d in dias_ordenados]
    md_lines = []
    md_lines.append(f"| {' | '.join(headers)} |")
    md_lines.append(f"|{'|'.join(['---'] * len(headers))}|")
    
    if -1 in [d_id for f in asignaciones_finales for d_id in asignaciones_finales[f]]:
         dispos_potenciales.append(-1)
         dispositivos_base[-1] = "❌ SIN CAPACITACIÓN"
         dispo_fecha_apertura[-1] = "2000-01-01"
    
    for dispo_id in dispos_potenciales:
        nombre_d = dispositivos_base.get(dispo_id, "Desconocido")
        piso_d = dispositivos_piso.get(dispo_id, "-")
        
        if dispo_id != -1:
            c_min, c_max = obtener_cupos("2026-03-14", nombre_d)
            if c_min == c_max: cupo_str = f"[{c_min}]"
            else: cupo_str = f"[{c_min}-{c_max}]"
            # Agregamos indicador visual del piso para la matriz
            nombre_d_corto = f"(P{piso_d}) {nombre_d[:12]} {cupo_str}"
        else: nombre_d_corto = nombre_d
            
        row = [nombre_d_corto]
        for f in dias_ordenados:
            if dispo_fecha_apertura[dispo_id] >= f: row.append("🔒")
            else:
                asignados = asignaciones_finales.get(f, {}).get(dispo_id, [])
                if not asignados: row.append("—")
                else: row.append("<br>".join([f"{nombres.get(a, '?')} ({p})" for a, p in asignados]))
        md_lines.append(f"| {' | '.join(row)} |")

    output_path = os.environ.get('OUTPUT_MD_PATH', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'knowledge_base', 'matriz_rotacion_completa.md'))
    with open(output_path, 'w') as fh:
        fh.write("# Matriz de Asignaciones Refinada (Marzo 2026)\n\n")
        fh.write("Esta tabla refleja la asignación de los 24 o 26 residentes reales (excluyendo a los que están en modo Descanso).\n")
        fh.write("Se aplica el **Plan 2** de las nuevas capacitaciones de marzo (distribuidas entre el 10, 11 y 20).\n\n")
        fh.write("\n".join(md_lines))
        fh.write("\n\n---\n\n### ⚖️ ¿Cómo leer los Puntajes (Score)?\n")
        fh.write("El algoritmo asigna residentes basándose en un sistema de puntaje que inicia en **1000 pts** cada día. Se aplican las siguientes penalizaciones (restas) para garantizar la rotación y equidad:\n\n")
        fh.write("*   **`(-400 pts)` por Repetición de Dispositivo:** Cada vez que el residente es asignado a un dispositivo en el mes, se le restan 400 pts para *ese* dispositivo específico en el futuro, forzando a que rote hacia otros.\n")
        fh.write("*   **`(-100 pts)` por Carga Laboral Histórica:** Por cada día de apertura en el que el residente *ya haya trabajado* en el mes, se le descuentan 100 pts globales, dándole prioridad a los que trabajaron menos días.\n")

        fh.write("*   **`(-200 pts)` por Saturación de Emergencia (Fase 3):** Si el motor se queda sin cupos pero aún hay residentes sin asignar (Overbooking), forzará la inserción de residentes extra en los dispositivos. Por cada residente extra sobregirado en el cupo, se restan 200 pts a la asignación, indicando estrés en la capacidad y falta de capacitación en las mesas vacías.\n")

if __name__ == '__main__':
    generar_matriz_markdown()
