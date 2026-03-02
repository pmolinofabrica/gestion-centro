import json
import requests
from collections import defaultdict
from datetime import datetime

CONFIG_FILE = '/home/pablo/Documentos/gestion-centro/config/supabase.json'

def get_base():
    with open(CONFIG_FILE, 'r') as f: config = json.load(f)
    b = config.get('project_url')
    if not b.startswith('http'): b = 'https://' + b
    if 'db.' in b and '.supabase.co' in b: b = b.replace('db.', '')
    k = config.get('service_role_key')
    return b, {"apikey": k, "Authorization": f"Bearer {k}", "Content-Type": "application/json"}

def generar_matriz_markdown():
    b, h = get_base()
    
    # 1. Historial de capacitaciones
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
            
    # 2. Convocatorias (Solo fines de semana, sin el 1/3)
    url_conv = f"{b}/rest/v1/vista_convocatoria_completa?anio=eq.2026&mes=eq.3&fecha_turno=neq.2026-03-01&order=fecha_turno.asc"
    r_conv = requests.get(url_conv, headers=h)
    convocatorias = r_conv.json()
    
    convocados_por_dia = defaultdict(list)
    dias_ordenados = set()
    nombres = {} 
    
    for row in convocatorias:
        fecha = row['fecha_turno']
        agente = row['id_agente']
        dt = datetime.strptime(fecha, "%Y-%m-%d")
        if dt.weekday() >= 5: # Fines de semana
            convocados_por_dia[fecha].append(agente)
            dias_ordenados.add(fecha)
            # Acortamos nombre a "Apellido, N." para la tabla
            apellidos = row['agente'].split(',')[0]
            nombres[agente] = apellidos

    dias_ordenados = sorted(list(dias_ordenados))
    
    # 3. Dispositivos
    r_disp = requests.get(f"{b}/rest/v1/dispositivos?select=id_dispositivo,nombre_dispositivo&activo=eq.true", headers=h)
    dispositivos_base = {d['id_dispositivo']: d['nombre_dispositivo'] for d in r_disp.json()}
    
    # ROTACION Y MOTOR
    historial_rotacion = defaultdict(list)
    historial_dias_operados = defaultdict(list) 
    asignaciones_finales = defaultdict(dict)
    
    dispos_potenciales = list(dispo_fecha_apertura.keys())
    # Ordenamos dispositivos por nombre para que la tabla sea consistente
    dispos_potenciales.sort(key=lambda x: dispositivos_base.get(x, ""))

    for fecha in dias_ordenados:
        convocados_hoy = convocados_por_dia[fecha].copy() 
        dispos_hoy = [d for d in dispos_potenciales if dispo_fecha_apertura[d] < fecha]
        
        for dispo_id in dispos_hoy:
            candidatos_validos = []
            for agente_id in convocados_hoy:
                fecha_capStr = caps_agente.get(agente_id, {}).get(dispo_id)
                if not fecha_capStr or fecha_capStr >= fecha: continue
                
                puntaje = 1000
                veces_en_este = historial_rotacion[agente_id].count(dispo_id)
                puntaje -= (veces_en_este * 400) 
                
                veces_total = len(historial_dias_operados[agente_id])
                puntaje -= (veces_total * 100) 
                
                dt_hoy = datetime.strptime(fecha, "%Y-%m-%d")
                opero_ayer = any((dt_hoy - datetime.strptime(d, "%Y-%m-%d")).days == 1 for d in historial_dias_operados[agente_id])
                if opero_ayer: puntaje -= 500 
                    
                candidatos_validos.append({"id": agente_id, "nombre": nombres[agente_id], "puntaje": puntaje})
                
            if candidatos_validos:
                mejor = sorted(candidatos_validos, key=lambda x: x['puntaje'], reverse=True)[0]
                asignaciones_finales[fecha][dispo_id] = f"{mejor['nombre']} ({mejor['puntaje']})"
                
                historial_rotacion[mejor['id']].append(dispo_id)
                historial_dias_operados[mejor['id']].append(fecha)
                convocados_hoy.remove(mejor['id'])
            else:
                asignaciones_finales[fecha][dispo_id] = "—" # Sin residente aplicable

    # GENERAR MARKDOWN (INVERTIDO: Filas=Dispositivos, Columnas=Días)
    # Una tabla cruzada (Grid) es 10x mejor para visualizar que listas planas
    
    # Encabezados
    headers = ["Dispositivo"] + [datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m") for d in dias_ordenados]
    md_lines = []
    md_lines.append(f"| {' | '.join(headers)} |")
    md_lines.append(f"|{'|'.join(['---'] * len(headers))}|")
    
    for dispo_id in dispos_potenciales:
        nombre_d = dispositivos_base.get(dispo_id, "Desconocido")
        # Acortamos el nombre del dispositivo para que entre prolijo
        nombre_d_corto = nombre_d[:15] + "..." if len(nombre_d) > 15 else nombre_d
        
        row = [nombre_d_corto]
        for f in dias_ordenados:
            if dispo_fecha_apertura[dispo_id] >= f:
                # Si en ese día todavía no estaba capacitado, lo cerramos
                row.append("🔒 (Cerrado)")
            else:
                asignado = asignaciones_finales.get(f, {}).get(dispo_id, "—")
                row.append(asignado)
        md_lines.append(f"| {' | '.join(row)} |")

    with open('/home/pablo/.gemini/antigravity/brain/38d79bb8-3e11-4214-bba2-c22807cfb777/matriz_rotacion.md', 'w') as fh:
        fh.write("# Matriz de Asignaciones (Marzo 2026)\n\n")
        fh.write("> [!NOTE] \n> Una tabla de doble entrada (Dispositivos en Y, Días en X) es el mejor modelo mental posible porque te permite ver la carga horizontal de la rotación y los huecos en las cuadrículas. El número entre paréntesis es el *Puntaje del Motor* final.\n\n")
        fh.write("\n".join(md_lines))
        fh.write("\n\n### Diccionario de Estados\n- **🔒 (Cerrado)**: El dispositivo aún no había dictado su capacitación en esta fecha.\n- **—**: Ningún residente activo, matriculado y convocado ese día cumplía con los requisitos.\n")
        
    print("Markdown generado con éxito en /home/pablo/.gemini/antigravity/brain/38d79bb8-3e11-4214-bba2-c22807cfb777/matriz_rotacion.md")

if __name__ == '__main__':
    generar_matriz_markdown()
