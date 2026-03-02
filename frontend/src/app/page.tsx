"use client";

import React, { useState, useEffect } from 'react';
import { Calendar, Users, Settings, RefreshCcw, Activity, ShieldAlert, ArrowRightLeft, Check, XCircle, AlertCircle, MapPin, UserMinus, UserPlus, FileBox, Search, User, MonitorSmartphone, Undo2, LockKeyhole } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';

// === Global App State Mock ===
const MOCK_MONTHS = ["Febrero 2026", "Marzo 2026", "Abril 2026"];

// === Mock Data based on the Python engine ===
const MOCK_DEVICES_BACKUP = [
  { id: "d1", name: "(P1) FÁBRICA DE LENGUAJES", min: 1, max: 1 },
  { id: "d2", name: "(P1) FÁBRICA DE PAPEL", min: 1, max: 2 },
  { id: "d3", name: "(P1) HOMENAJE A L...", min: 1, max: 1 },
  { id: "d4", name: "(P1) LOS PAPELES", min: 1, max: 1 },
  { id: "d5", name: "(P1) PATIO DE ARTE", min: 1, max: 1 },
  { id: "d6", name: "(P1) SECTOR DE LECTURA", min: 1, max: 1 },
  { id: "d7", name: "(P2) AUTORRETRATATE", min: 1, max: 1 },
  { id: "d8", name: "(P2) MESA DE ENSAMBLAJE", min: 1, max: 2 },
  { id: "d9", name: "(P2) MESA DE PINTURA", min: 2, max: 2 },
  { id: "d10", name: "(P2) RÍO DE JUEGOS M", min: 1, max: 1 },
  { id: "d11", name: "(P2) TARIMA DE PINTURA", min: 2, max: 2 },
  { id: "d12", name: "(P2) TOCO MADERA", min: 1, max: 1 },
  { id: "d13", name: "(P3) BATIK", min: 1, max: 2 },
  { id: "d14", name: "(P3) MOLDERÍA", min: 1, max: 1 },
  { id: "d15", name: "(P3) RÍO DE JUEGOS T", min: 1, max: 1 },
  { id: "d16", name: "(P3) SASHIKO", min: 1, max: 1 },
  { id: "d17", name: "(P3) SECTOR DE CONV...", min: 1, max: 2 },
  { id: "d18", name: "(P3) SECTOR DE DISEÑO", min: 1, max: 1 },
  { id: "d19", name: "(P3) TELA COLECTIVA", min: 1, max: 1 },
  { id: "d20", name: "(P3) TRAJE DE FORMAS", min: 1, max: 1 },
];

const ALL_RESIDENTS_DB = [
  { name: "Candioti", caps: { "d1": "2024-05-12", "d6": "2025-01-20", "d8": "2026-03-11" } },
  { name: "Raminy", caps: { "d2": "2024-06-12", "d10": "2025-04-20", "d17": "2026-02-11" } },
  { name: "Zárate", caps: { "d3": "2024-05-12", "d11": "2025-01-20", "d16": "2026-03-10" } },
  { name: "Amici", caps: { "d13": "2024-12-12", "d8": "2025-01-20", "d14": "2026-03-10" } },
  { name: "De Martino", caps: { "d8": "2024-05-12", "d14": "2025-01-20", "d5": "2026-01-11" } },
  { name: "Ojeda", caps: { "d1": "2024-05-12", "d4": "2025-06-20", "d9": "2025-11-11" } },
  { name: "Mendicino", caps: { "d11": "2024-05-12", "d17": "2025-01-20", "d20": "2025-08-11" } },
  { name: "Senkus", caps: {} },
  { name: "Ifrán", caps: {} }
];

const CALL_STATUS_DB = {
  "07/03": { "Candioti": "convocado", "Raminy": "descanso", "Zárate": "no_convocado", "Amici": "convocado", "De Martino": "convocado", "Ojeda": "convocado", "Mendicino": "descanso", "Senkus": "convocado", "Ifrán": "no_convocado" },
  "14/03": { "Candioti": "descanso", "Raminy": "convocado", "Zárate": "convocado", "Amici": "convocado", "De Martino": "convocado", "Ojeda": "no_convocado", "Mendicino": "convocado", "Senkus": "convocado", "Ifrán": "descanso" }
}

export default function AsignacionesApp() {
  const [activeTab, setActiveTab] = useState<string>('plan'); // 'plan', 'exec', 'devices', 'menu'
  const [selectedMonth, setSelectedMonth] = useState("Marzo 2026");

  // DB States
  const [dbDevices, setDbDevices] = useState<{ id: string, name: string, min: number, max: number }[]>(MOCK_DEVICES_BACKUP);
  const [dbResidents, setDbResidents] = useState<{ id_agente: number, nombre: string, apellido: string }[]>([]);
  const [allResidentsDb, setAllResidentsDb] = useState<{ id: number, name: string, caps: Record<string, string> }[]>([]);
  const [assignmentsDb, setAssignmentsDb] = useState<Record<string, Record<string, { id: number, name: string, score: number }[]>>>({});
  const [agentGroups, setAgentGroups] = useState<Record<string, string>>({});
  const [calendarDb, setCalendarDb] = useState<Record<string, Record<string, number>>>({}); // { '07/03': { 'd1': 1, 'd2': 2 } }
  const [convocadosCountDb, setConvocadosCountDb] = useState<Record<string, number>>({}); // { '07/03': 15 }
  const [isLoading, setIsLoading] = useState(true);
  const [activeDates, setActiveDates] = useState<string[]>([]); // Dynamic dates from DB

  // Selection states 
  const [selectedResident, setSelectedResident] = useState<{ id: number, name: string, score: number, device: string, date: string } | null>(null);
  const [selectedDevice, setSelectedDevice] = useState<{ id: string, name: string } | null>(null);
  const [selectedDateFilter, setSelectedDateFilter] = useState<string | null>(null);
  const [showVacantsSidebar, setShowVacantsSidebar] = useState(false);
  const [selectedVacant, setSelectedVacant] = useState<{ id: number, name: string, date: string } | null>(null);
  const [convocadosDb, setConvocadosDb] = useState<Record<string, number[]>>({}); // { '07/03': [id1, id2] }

  // === UndoStack con persistencia en localStorage ===
  // IMPORTANTE: Inicializar en [] para SSR. Cargar desde localStorage en useEffect (cliente solo).
  const UNDO_STORAGE_KEY = 'gestion_centro_undo_stack';
  const UNDO_MAX_ENTRIES = 50;

  const saveUndoStack = (stack: any[]) => {
    const capped = stack.length > UNDO_MAX_ENTRIES ? stack.slice(-UNDO_MAX_ENTRIES) : stack;
    try { localStorage.setItem(UNDO_STORAGE_KEY, JSON.stringify(capped)); } catch { }
    return capped;
  };

  const [undoStack, setUndoStack] = useState<any[]>([]); // Siempre [] en SSR
  const [isMounted, setIsMounted] = useState(false);

  // Vista Menú - estado de candado
  const [isLocked, setIsLocked] = useState(false);
  const MENU_PIN = '2350';

  // Cargar undoStack desde localStorage SOLO en cliente (evita error de hidratación)
  useEffect(() => {
    setIsMounted(true);
    try {
      const raw = localStorage.getItem(UNDO_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as any[];
      const todayStr = new Date().toISOString().split('T')[0];
      const filtered = parsed.filter((entry: any) => entry._timestamp?.startsWith(todayStr));
      if (filtered.length !== parsed.length) {
        localStorage.setItem(UNDO_STORAGE_KEY, JSON.stringify(filtered));
      }
      setUndoStack(filtered);
    } catch { /* ignorar errores de storage */ }
  }, []);

  // Helper: push a la pila con timestamp y persistencia
  const pushUndo = (entry: any) => {
    const stamped = { ...entry, _timestamp: new Date().toISOString() };
    setUndoStack(prev => {
      const next = [...prev, stamped];
      return saveUndoStack(next);
    });
  };

  // Helper: pop de la pila con persistencia
  const popUndo = () => {
    setUndoStack(prev => {
      const next = prev.slice(0, -1);
      saveUndoStack(next);
      return next;
    });
  };

  // Funciones de Undo / Revertir local (con persistencia localStorage)
  const handleUndoLastAction = async () => {
    if (undoStack.length === 0) return;

    setIsLoading(true);
    const lastAction = undoStack[undoStack.length - 1];

    try {
      let error: any = null;

      if (lastAction.id_asignacion) {
        // Ruta A: Undo por id_asignacion (AssignVacant)
        const res = await supabase.from('menu')
          .update({
            id_dispositivo: Number(lastAction.old_id_dispositivo),
            id_agente: lastAction.old_id_agente
          })
          .eq('fecha_asignacion', lastAction.fecha_asignacion)
          .eq('id_asignacion', lastAction.id_asignacion);
        error = res.error;
      } else {
        // Ruta B: Undo por filtros directos (Remove, Swap, Quitar-inline)
        const res = await supabase.from('menu')
          .update({
            id_dispositivo: Number(lastAction.old_id_dispositivo),
            id_agente: lastAction.old_id_agente
          })
          .eq('id_agente', lastAction.old_id_agente)
          .eq('fecha_asignacion', lastAction.fecha_asignacion);
        error = res.error;
      }

      if (error) {
        alert("Error restaurando la acción: " + error.message);
      } else {
        popUndo();
        window.location.reload();
      }
    } catch (e) {
      console.error(e);
    }
    setIsLoading(false);
  };  // Real DB Fetching logic
  useEffect(() => {
    async function loadInitialData() {
      setIsLoading(true);
      try {
        // Fetch Dispositivos
        const { data: dispoData, error: dispoErr } = await supabase
          .from('dispositivos')
          .select('id_dispositivo, nombre_dispositivo, piso_dispositivo, cupo_minimo, cupo_optimo')
          .eq('activo', true)
          .neq('id_dispositivo', 999)
          .order('piso_dispositivo', { ascending: true });

        if (dispoData && dispoData.length > 0) {
          const mappedDevices = dispoData.map(d => ({
            id: String(d.id_dispositivo),
            name: `(P${d.piso_dispositivo || '?'}) ${d.nombre_dispositivo}`,
            min: d.cupo_minimo || 1,
            max: d.cupo_optimo || 1
          }));
          setDbDevices(mappedDevices);
        }

        // Fetch Residentes (Padron)
        const { data: resiData } = await supabase
          .from('datos_personales')
          .select('id_agente, nombre, apellido, cohorte')
          .eq('activo', true)
          .eq('cohorte', 2026);

        if (resiData) setDbResidents(resiData);

        // Fetch preliminar de las capacitaciones para agrupar IDs
        const capsRep = await supabase.from('capacitaciones').select('id_cap, id_dia, grupo');
        const capData = capsRep.data || [];
        const diaIds = Array.from(new Set(capData.map(c => c.id_dia).filter(Boolean)));

        // Fetch de los demas catalogos aplicando el filtro IN en dias
        const [partsRes, dispoCapsRes, diasRes] = await Promise.all([
          supabase.from('capacitaciones_participantes').select('id_cap, id_agente, asistio').eq('asistio', true).limit(3000),
          supabase.from('capacitaciones_dispositivos').select('id_cap, id_dispositivo').limit(2000),
          supabase.from('dias').select('id_dia, fecha').in('id_dia', diaIds)
        ]);

        if (resiData && capData.length && partsRes.data && dispoCapsRes.data && diasRes.data) {

          // Mapear Fechas reales de la tabla de dias
          const diasDict: Record<number, string> = {};
          diasRes.data.forEach(d => {
            if (d.fecha) diasDict[d.id_dia] = d.fecha.substring(0, 10);
          });

          // Mapear Fechas de Cap
          const capDates: Record<number, string> = {};
          const capGroups: Record<number, string> = {};
          capData.forEach(c => {
            const realDate = diasDict[c.id_dia];
            if (realDate) capDates[c.id_cap] = realDate;
            if (c.grupo) capGroups[c.id_cap] = c.grupo;
          });

          // Mapear id_cap -> array of id_dispositivo
          const capDispos: Record<number, number[]> = {};
          dispoCapsRes.data.forEach(cd => {
            if (!capDispos[cd.id_cap]) capDispos[cd.id_cap] = [];
            capDispos[cd.id_cap].push(cd.id_dispositivo);
          });

          // Armar el ALL_RESIDENTS_DB (nombre y sus caps)
          const residentsMap: Record<number, { id: number, name: string, caps: Record<string, string> }> = {};
          resiData.forEach(r => {
            residentsMap[r.id_agente] = {
              id: r.id_agente,
              name: `${r.apellido} ${r.nombre}`,
              caps: {}
            };
          });

          // Asignar participaciones
          const gruposAgenteMap: Record<string, Set<string>> = {};
          partsRes.data.forEach(p => {
            const agId = p.id_agente;
            const cId = p.id_cap;
            const cDate = capDates[cId];
            const dispos = capDispos[cId] || [];

            if (capGroups[cId]) {
              if (!gruposAgenteMap[agId]) gruposAgenteMap[agId] = new Set();
              gruposAgenteMap[agId].add(capGroups[cId]);
            }

            if (residentsMap[agId] && cDate) {
              dispos.forEach(dId => {
                const dKey = String(dId);
                if (!residentsMap[agId].caps[dKey] || residentsMap[agId].caps[dKey] < cDate) {
                  residentsMap[agId].caps[dKey] = cDate;
                }
              });
            }
          });
          const gruposAgenteFinal: Record<string, string> = {};
          Object.keys(gruposAgenteMap).forEach(k => {
            // Si el agente está en más de un grupo en DB, preferimos A predeterminado.
            const grps = Array.from(gruposAgenteMap[k]);
            gruposAgenteFinal[k] = grps.includes('A') ? 'A' : grps[0];
          });
          setAgentGroups(gruposAgenteFinal);

          setAllResidentsDb(Object.values(residentsMap));
        }

        // Fetch Asignaciones para construir la Matriz (DAMA Menu Table)
        const { data: menuData, error: menuErr } = await supabase
          .from('menu')
          .select('id_agente, id_dispositivo, fecha_asignacion, estado_ejecucion, orden');
        // Ya no filtramos por "planificado" para poder traernos tambien a los "descanso" y contarlos.

        if (menuData && resiData) {
          const matrix: Record<string, Record<string, { id: number, name: string, score: number }[]>> = {};
          const convocadosCount: Record<string, number> = {};
          const convocadosList: Record<string, number[]> = {};

          // Helper dict para sacar rápido los nombres
          const nameDict: Record<number, string> = {};
          resiData.forEach(r => nameDict[r.id_agente] = `${r.apellido} ${r.nombre}`);

          menuData.forEach(a => {
            if (!a.fecha_asignacion) return;

            // Convert '2026-03-07' -> '07/03' to match UI behavior
            const dateParts = a.fecha_asignacion.split("-");
            if (dateParts.length === 3) {
              const [y, m, d] = dateParts;
              const uiDate = `${d}/${m}`;

              // Todos ingresan al conteo base de 'convocados' el dia de la fecha
              convocadosCount[uiDate] = (convocadosCount[uiDate] || 0) + 1;
              if (!convocadosList[uiDate]) convocadosList[uiDate] = [];
              convocadosList[uiDate].push(a.id_agente);

              if (a.id_dispositivo && a.id_dispositivo !== 999) {
                const dId = String(a.id_dispositivo);

                if (!matrix[uiDate]) matrix[uiDate] = {};
                if (!matrix[uiDate][dId]) matrix[uiDate][dId] = [];

                matrix[uiDate][dId].push({
                  id: a.id_agente,
                  name: nameDict[a.id_agente] || "Desconocido",
                  score: a.orden || 1000 // Usamos el Score almacenado en el backend o su default
                });
              }
            }
          });

          setConvocadosCountDb(convocadosCount);
          setConvocadosDb(convocadosList);

          // Llenar calendarDb dinámico con lo inyectado en Matrix
          const newCalendarDb: Record<string, Record<string, number>> = {};
          Object.keys(matrix).forEach(uid => {
            newCalendarDb[uid] = {};
            Object.keys(matrix[uid]).forEach(did => {
              newCalendarDb[uid][did] = matrix[uid][did].length;
            });
          });
          setCalendarDb(newCalendarDb);

          setAssignmentsDb(matrix);

          // Compute sorted dynamic dates from matrix keys
          const unsortedDates = Object.keys(matrix);
          const sorted = unsortedDates.sort((a, b) => {
            const [dayA, monthA] = a.split("/").map(Number);
            const [dayB, monthB] = b.split("/").map(Number);
            if (monthA !== monthB) return monthA - monthB;
            return dayA - dayB;
          });
          setActiveDates(sorted);

          // Initialize Exec Tab with first available date if not set
          if (sorted.length > 0) setExecDate(sorted[0]);

        } else if (menuErr) {
          console.error("Error cargando tabla menu:", menuErr)
        }

      } catch (err) {
        console.error("Error cargando Supabase:", err);
      }
      setIsLoading(false);
    }

    loadInitialData();
  }, []);

  // States for Execution Tab
  const [execDate, setExecDate] = useState("07/03");
  const [absentResidents, setAbsentResidents] = useState<string[]>([]);
  const [showRestingModal, setShowRestingModal] = useState(false);
  const [showDevicesMenu, setShowDevicesMenu] = useState(false);
  const [expandedDeviceForAssignment, setExpandedDeviceForAssignment] = useState<string | null>(null);

  const getScoreColor = (score: number) => {
    if (score >= 900) return "bg-emerald-100 text-emerald-800 border-emerald-300";
    if (score >= 600) return "bg-amber-100 text-amber-800 border-amber-300";
    return "bg-rose-100 text-rose-800 border-rose-300";
  };

  const getFloorColor = (deviceName: string) => {
    if (deviceName.includes("(P1)")) return "bg-cyan-50 border border-cyan-200 text-cyan-800";
    if (deviceName.includes("(P2)")) return "bg-rose-50 border border-rose-200 text-rose-800";
    if (deviceName.includes("(P3)")) return "bg-amber-50 border border-amber-200 text-amber-800";
    return "bg-slate-50 border border-slate-200 text-slate-800";
  };

  const getFloorColorBadge = (deviceName: string) => {
    if (deviceName.includes("(P1)")) return "bg-cyan-100 text-cyan-800";
    if (deviceName.includes("(P2)")) return "bg-rose-100 text-rose-800";
    if (deviceName.includes("(P3)")) return "bg-amber-100 text-amber-800";
    return "bg-slate-100 text-slate-800";
  };

  const toggleAbsent = async (name: string, deviceName: string) => {
    // Buscar id del residente y del dispositivo
    const resNameMatch = name.toLowerCase();
    const dbRes = dbResidents.find(r => r.apellido.toLowerCase().includes(resNameMatch) || r.nombre.toLowerCase().includes(resNameMatch));
    const dbDisp = dbDevices.find(d => d.name === deviceName);

    if (dbRes && dbDisp) {
      const [d, mStr] = execDate.split("/");
      const yyyy = selectedMonth.split(" ")[1] || "2026";
      const fechaDB = `${yyyy}-${mStr}-${d}`;

      try {
        setIsLoading(true);
        // Si estaba en la grilla y apretaron que faltó, lo borramos de la asignación 
        // (En DAMA marcaríamos 'ausente_aviso', para borrarlo de UI lo pasamos a inactivo rápido)
        const { error } = await supabase
          .from('menu')
          .delete()
          .eq('id_agente', dbRes.id_agente)
          .eq('id_dispositivo', dbDisp.id)
          .eq('fecha_asignacion', fechaDB);

        if (!error) {
          window.location.reload();
        } else {
          alert("Error Supabase: " + error.message);
          setIsLoading(false);
        }
      } catch (e: any) {
        alert("Excepción: " + e.message);
        setIsLoading(false);
      }
    }
  };

  // Mutación: Asignar residente huérfano (P0) a un dispositivo con vacante
  const handleAssignFromPool = async (residentName: string) => {
    const resNameMatch = residentName.toLowerCase();
    const dbRes = dbResidents.find(r => r.apellido.toLowerCase().includes(resNameMatch) || r.nombre.toLowerCase().includes(resNameMatch));

    // Buscar el primer dispositivo que tenga espacio
    const dispList = dbDevices;
    let targetDisp = null;

    for (const d of dispList) {
      const assigs = assignmentsDb[execDate]?.[d.id] || [];
      if (assigs.length < d.max) { // Si hay lugar físico respecto al cupo optimo/maximo
        targetDisp = d;
        break;
      }
    }

    if (!targetDisp) {
      alert("Actualmente consideramos que el Centro está saturado (No hay dispositivos con cupo libre asignable automáticamente). Busca un reemplazo manual.");
      return;
    }

    if (dbRes) {
      const [day, mStr] = execDate.split("/");
      const yyyy = selectedMonth.split(" ")[1] || "2026";
      const fechaDB = `${yyyy}-${mStr}-${day}`;

      // FIXME: Requiere id_turno. Como es UI reactiva hardcodearemos turno 1,
      // La solución final requiere la UI seleccionando el turno Activo (Mañana/Tarde)
      try {
        setIsLoading(true);
        const { error } = await supabase
          .from('menu')
          .insert([{
            id_agente: dbRes.id_agente,
            id_dispositivo: Number(targetDisp.id),
            fecha_asignacion: fechaDB,
            estado_ejecucion: 'planificado'
          }]);

        if (!error) {
          window.location.reload();
        } else {
          alert("Error Inserción: " + error.message);
          setIsLoading(false);
        }
      } catch (e: any) {
        alert("Exception: " + e.message);
        setIsLoading(false);
      }
    }
  };

  // Mutación: Forzar asignación a un dispositivo puntual (Usado para Abrir un dispositivo on-the-fly)
  const handleAssignToDevice = async (residentName: string, deviceId: string) => {
    const resNameMatch = residentName.toLowerCase();
    const dbRes = dbResidents.find(r => r.apellido.toLowerCase().includes(resNameMatch) || r.nombre.toLowerCase().includes(resNameMatch));

    if (dbRes) {
      const [day, mStr] = execDate.split("/");
      const yyyy = selectedMonth.split(" ")[1] || "2026";
      const fechaDB = `${yyyy}-${mStr}-${day}`;

      try {
        setIsLoading(true);
        const { error } = await supabase
          .from('menu')
          .insert([{
            id_agente: dbRes.id_agente,
            id_dispositivo: Number(deviceId),
            fecha_asignacion: fechaDB,
            estado_ejecucion: 'planificado'
          }]);

        if (!error) {
          window.location.reload();
        } else {
          alert("Error Inserción: " + error.message);
          setIsLoading(false);
        }
      } catch (e: any) {
        alert("Exception: " + e.message);
        setIsLoading(false);
      }
    }
  };

  // Mutación: Cambiar a un residente por otro en la BBDD
  const handleSwapResident = async (newResId: number) => {
    if (!selectedResident) return;

    // 1. Buscar IDs numéricos
    const oldResId = selectedResident.id;

    const oldRes = dbResidents.find(r => r.id_agente === oldResId);
    const newRes = dbResidents.find(r => r.id_agente === newResId);

    const disp = dbDevices.find(d => d.name === selectedResident.device);

    if (oldRes && newRes && disp) {
      // En Supabase guardamos "YYYY-MM-DD". En la UI tenemos date = "07/03"
      const [d, mStr] = selectedResident.date.split("/");
      const yyyy = selectedMonth.split(" ")[1] || "2026";
      const fechaDB = `${yyyy}-${mStr.padStart(2, '0')}-${d.padStart(2, '0')}`; // Asumiendo YYYY-MM-DD

      try {
        setIsLoading(true);
        // UndoStack: guardamos el estado previo antes del swap
        pushUndo({
          fecha_asignacion: fechaDB,
          old_id_agente: oldRes.id_agente,
          old_id_dispositivo: disp.id,
          action_type: 'swap'
        });

        const { error } = await supabase
          .from('menu')
          .update({ id_agente: newRes.id_agente })
          .eq('id_agente', oldRes.id_agente)
          .eq('id_dispositivo', disp.id)
          .eq('fecha_asignacion', fechaDB);

        if (!error) {
          setSelectedResident(null);
          window.location.reload();
        } else {
          alert("Error Supabase: " + error.message);
          setIsLoading(false);
        }
      } catch (e: any) {
        alert("Excepción: " + e.message);
        setIsLoading(false);
      }
    } else {
      alert("Atención: No se encontraron los IDs numéricos para realizar el cruce en base al nombre Mock.");
    }
  };

  // Mutación: Enviar residente a "Sin Asignar" (Vacantes)
  const handleRemoveResident = async () => {
    if (!selectedResident) return;

    try {
      if (!confirm(`¿Estás seguro de quitar a ${selectedResident.name} de este dispositivo? Pasará a la lista de Vacantes.`)) return;

      setIsLoading(true);
      const yyyy = selectedMonth.split(" ")[1] || "2026";
      const [d, mStr] = selectedResident.date.split("/");
      const fechaDB = `${yyyy}-${mStr.padStart(2, '0')}-${d.padStart(2, '0')}`; // YYYY-MM-DD

      const { error } = await supabase.from('menu')
        .update({ id_dispositivo: 999, estado_ejecucion: 'planificado' })
        .eq('id_agente', selectedResident.id)
        .eq('fecha_asignacion', fechaDB);

      if (error) {
        alert("Error de DB al quitar la asignación: " + error.message);
        setIsLoading(false);
      } else {
        // Find existing device to push to UndoStack
        const deviceOfRes = dbDevices.find(d => d.name === selectedResident.device);
        if (deviceOfRes) {
          pushUndo({
            fecha_asignacion: fechaDB,
            old_id_agente: selectedResident.id,
            old_id_dispositivo: deviceOfRes.id,
            action_type: 'remove'
          });
        }

        setSelectedResident(null);
        window.location.reload();
      }
    } catch (e: any) {
      alert("Error al quitar: " + e.message);
      setIsLoading(false);
    }
  };

  // Mutación: Invocar IA de Supabase remotamente
  const handleRunAI = async () => {
    try {
      if (!confirm("¿Ejecutar Inteligencia Artificial? Esto re-calculará las asignaciones desde hoy hacia el final del mes, respetando tus parámetros.")) return;

      setIsLoading(true);
      const today = new Date().toISOString().split('T')[0]; // "2026-03-16"

      const res = await fetch('/api/run-engine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ startDate: today })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error);

      alert("✅ IA Ejecutada con éxito.");
      window.location.reload();
    } catch (e: any) {
      alert("Error en Motor IA: " + e.message);
      setIsLoading(false);
    }
  };

  // Mutación: Asignar a un residente Vacante a un Dispositivo en la UI
  const handleAssignVacant = async (deviceId: string) => {
    if (!selectedVacant) return;

    try {
      const yyyy = selectedMonth.split(" ")[1] || "2026";
      const [d, mStr] = selectedVacant.date.split("/");
      const fechaDB = `${yyyy}-${mStr.padStart(2, '0')}-${d.padStart(2, '0')}`; // YYYY-MM-DD

      const cupo = calendarDb[selectedVacant.date]?.[deviceId] || 0;
      const currentAssigned = assignmentsDb[selectedVacant.date]?.[deviceId]?.length || 0;

      let updateCupo = false;
      if (currentAssigned >= cupo) {
        if (!confirm(`El dispositivo está actualmente sin plazas (ocupación: ${currentAssigned} de ${cupo}). ¿Deseas ampliar el cupo a ${currentAssigned + 1} lugares y forzar la asignación de todos modos?`)) {
          return;
        }
        updateCupo = true;
      }

      setIsLoading(true);

      if (updateCupo) {
        await supabase.from('calendario_dispositivos').upsert({
          id_dispositivo: parseInt(deviceId),
          fecha: fechaDB,
          cupo_habilitado: currentAssigned + 1
        });
      }

      const { data: existingMenu } = await supabase.from('menu')
        .select('id_asignacion')
        .eq('id_agente', selectedVacant.id)
        .eq('fecha_asignacion', fechaDB)
        .maybeSingle();

      if (existingMenu) {
        pushUndo({
          fecha_asignacion: fechaDB,
          id_asignacion: existingMenu.id_asignacion,
          old_id_agente: selectedVacant.id,
          old_id_dispositivo: 999,
          action_type: 'assign_vacant'
        });

        // Update
        await supabase.from('menu')
          .update({ id_dispositivo: parseInt(deviceId), estado_ejecucion: 'planificado' })
          .eq('id_asignacion', existingMenu.id_asignacion);
      } else {
        // Fallback Insert
        await supabase.from('menu').insert([{
          id_dispositivo: parseInt(deviceId),
          id_agente: selectedVacant.id,
          fecha_asignacion: fechaDB,
          estado_ejecucion: 'planificado',
          id_convocatoria: 0 // Mock fallback si no tiene conv.
        }]);
      }

      setSelectedVacant(null);
      window.location.reload();
    } catch (e: any) {
      alert("Excepción al asignar vacante: " + e.message);
      setIsLoading(false);
    }
  };

  // Render Componente Sidebar (Vacantes)
  const renderVacantsSidebar = () => {
    if (!showVacantsSidebar) return null;
    return (
      <div className={`w-96 bg-white border-r border-slate-200 shadow-2xl transition-all duration-300 flex flex-col absolute left-0 h-full z-50 overflow-hidden`}>
        <div className="h-full flex flex-col">
          <div className="p-6 border-b border-rose-100 bg-rose-50 transition-colors">
            <div className="flex justify-between items-start mb-4">
              <div>
                <span className="text-[10px] items-center flex gap-1 font-bold tracking-wider uppercase mb-1 block text-rose-600">
                  <AlertCircle className="w-3 h-3" /> Atención Requerida
                </span>
                <h3 className="text-2xl font-bold text-rose-900">Residentes Vacantes</h3>
              </div>
              <button onClick={() => setShowVacantsSidebar(false)} className="opacity-70 text-rose-800 hover:text-rose-900 hover:opacity-100 bg-white p-1 rounded-md border border-rose-200">
                ✕
              </button>
            </div>
            <p className="text-xs text-rose-700 font-medium">
              Estos residentes están **Convocados** para apertura al público, pero no tienen ningún dispositivo asignado en el tablero debido a reemplazos manuales.
            </p>
          </div>

          <div className="p-4 flex-1 overflow-y-auto bg-white space-y-4">
            {activeDates.map((date, idx) => {
              const assignedIds = new Set();
              Object.values(assignmentsDb[date] || {}).forEach(arr => {
                arr.forEach((r: any) => assignedIds.add(r.id));
              });

              const convocados = convocadosDb[date] || [];
              const vacantes = convocados.filter(id => !assignedIds.has(id));

              if (vacantes.length === 0) return null;

              return (
                <div key={idx} className="border border-slate-200 rounded-xl overflow-hidden">
                  <div className="bg-slate-50 px-3 py-2 border-b border-slate-200 font-bold text-sm text-slate-800 flex justify-between items-center">
                    {date}
                    <span className="bg-rose-100 text-rose-700 px-2 py-0.5 rounded-full text-xs shadow-sm">{vacantes.length} sueltos</span>
                  </div>
                  <div className="p-2 space-y-2 bg-white">
                    {vacantes.map(vid => {
                      const res = allResidentsDb.find(r => r.id === vid);
                      if (!res) return null;

                      const yyyy = selectedMonth.split(" ")[1] || "2026";
                      const [dDay, mStr] = date.split("/");
                      const fechaDB = `${yyyy}-${mStr.padStart(2, '0')}-${dDay.padStart(2, '0')}`;

                      const pisosCap: Record<string, number> = {};
                      Object.keys(res.caps).forEach(dId => {
                        const capDate = res.caps[dId] as string;
                        if (capDate > fechaDB) return; // not ready yet

                        const dObj = dbDevices.find((dev: any) => dev.id === dId);
                        if (dObj) {
                          const matchPiso = dObj.name.match(/\(P\d+\)/);
                          const pisoName = matchPiso ? matchPiso[0].replace('(', '').replace(')', '') : 'P?';
                          pisosCap[pisoName] = (pisosCap[pisoName] || 0) + 1;
                        }
                      });

                      return (
                        <button
                          key={vid}
                          onClick={() => { setSelectedVacant({ id: res.id, name: res.name, date }); setSelectedDevice(null); setSelectedResident(null); }}
                          className={`w-full text-left p-3 rounded-xl border transition-all shadow-sm ${selectedVacant?.id === res.id && selectedVacant?.date === date ? 'border-indigo-500 ring-2 ring-indigo-200 bg-indigo-50/80 scale-[1.02]' : 'border-slate-200 bg-white hover:border-indigo-400 hover:shadow-md'}`}
                        >
                          <div className="font-bold text-sm text-slate-800 mb-1.5 flex items-center justify-between">
                            {res.name}
                            <ArrowRightLeft className="w-3 h-3 text-slate-300" />
                          </div>

                          <div className="flex flex-wrap gap-1 mt-0.5">
                            {Object.keys(pisosCap).length === 0 ? (
                              <span className="bg-slate-100 text-rose-600 px-1.5 py-0.5 text-[9px] rounded font-bold border border-rose-200 shadow-sm">Sin capacitaciones (Día Base)</span>
                            ) : (
                              Object.entries(pisosCap).map(([piso, count]) => {
                                // Paleta Ux por piso:
                                let colorClass = 'bg-slate-50 text-slate-800 border-slate-200';
                                if (piso === 'P1') colorClass = 'bg-cyan-50 text-cyan-800 border-cyan-200';
                                else if (piso === 'P2') colorClass = 'bg-rose-50 text-rose-800 border-rose-200';
                                else if (piso === 'P3') colorClass = 'bg-amber-50 text-amber-800 border-amber-200';

                                return (
                                  <span key={piso} className={`${colorClass} shadow-sm px-1.5 py-0.5 text-[9px] rounded font-bold border`}>
                                    {piso}: {count} Disp.
                                  </span>
                                )
                              })
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  // Render Componente Sidebar (Resident)
  const renderResidentSidebar = () => {
    if (!selectedResident) return null;

    const disp = dbDevices.find(d => d.name === selectedResident.device);
    const deviceId = disp?.id;
    const date = selectedResident.date;

    // Diccionario de ocupaciones para saber donde estna
    const occupancies: Record<number, string> = {};
    Object.values(assignmentsDb[date] || {}).forEach((arr, idx, array) => {
      const devNameKeys = Object.keys(assignmentsDb[date] || {});
      const devIdStr = devNameKeys[idx];
      const devObj = dbDevices.find(d => d.id === devIdStr);
      arr.forEach((r: any) => occupancies[r.id] = devObj ? devObj.name : 'Otro');
    });

    const convocados = new Set(convocadosDb[date] || []);

    const tier1: any[] = [];
    const tier2: any[] = [];
    const tier3: any[] = [];
    const tier4: any[] = [];

    allResidentsDb.forEach(res => {
      if (res.id === selectedResident.id) return;


      const isConvocado = convocados.has(res.id);
      const isCapacitado = deviceId ? !!res.caps[deviceId] : false;
      const currentLocation = occupancies[res.id];

      const alt = {
        name: res.name,
        id: res.id,
        reason: isConvocado ? (currentLocation ? `Ocupado en: ${currentLocation}` : "Libre hoy") : "Descanso",
        isBusy: !!currentLocation
      };

      if (isCapacitado && isConvocado) tier1.push({ ...alt, type: "Capacitado" });
      else if (!isCapacitado && isConvocado) tier2.push({ ...alt, type: "NO Capacitado" });
      else if (isCapacitado && !isConvocado) tier3.push({ ...alt, type: "Cap. en Descanso" });
      else tier4.push({ ...alt, type: "No Cap. y en Descanso" });
    });

    return (
      <div className={`w-96 bg-white border-l border-slate-200 shadow-2xl transition-all duration-300 flex flex-col absolute right-0 h-full z-50 overflow-hidden`}>
        <div className="h-full flex flex-col">
          <div className={`p-6 border-b ${getFloorColor(selectedResident.device)} transition-colors`}>
            <div className="flex justify-between items-start mb-4">
              <div>
                <span className="text-[10px] font-bold tracking-wider uppercase mb-1 block opacity-80">Modificar Asignación</span>
                <h3 className="text-2xl font-bold">{selectedResident.name}</h3>
              </div>
              <div className="flex gap-2">
                <button onClick={handleRemoveResident} className="opacity-90 hover:opacity-100 bg-rose-500 hover:bg-rose-600 text-white font-bold p-1 px-3 rounded text-xs shadow-sm transition-colors cursor-pointer flex items-center gap-1">
                  <UserMinus className="w-3 h-3" /> Quitar
                </button>
                <button onClick={() => setSelectedResident(null)} className="opacity-70 hover:opacity-100 bg-white/20 p-1.5 rounded-md border border-white/30 backdrop-blur-sm cursor-pointer">
                  ✕
                </button>
              </div>
            </div>

            <div className="flex items-center gap-2 text-sm bg-white/40 border border-white/50 px-3 py-2 rounded-lg shadow-sm font-medium">
              <Calendar className="w-4 h-4" />
              <span>{selectedResident.date}</span>
              <span className="opacity-50">|</span>
              <span className="truncate">{selectedResident.device}</span>
            </div>
          </div>

          <div className="p-6 flex-1 overflow-y-auto bg-white">
            {/* Score Breakdown */}
            <div className="bg-slate-50 rounded-xl p-4 mb-6 border border-slate-200">
              <h4 className="text-sm font-semibold text-slate-600 mb-2 flex items-center gap-2">
                <Activity className="w-4 h-4 text-slate-400" /> Rendimiento de Motor
              </h4>
              <div className="flex items-baseline gap-2 mb-3">
                <span className={`text-3xl font-bold ${selectedResident.score < 1000 ? 'text-amber-600' : 'text-emerald-600'}`}>
                  {selectedResident.score} <span className="text-sm font-normal text-slate-500">pts</span>
                </span>
              </div>
              <div className="text-xs text-slate-500 space-y-1">
                <div className="flex justify-between"><span>Score Base</span><span>1000</span></div>
                {selectedResident.score < 1000 && (
                  <div className="flex justify-between text-rose-600 font-medium">
                    <span>Penalidad Global/Rutina</span>
                    <span>-{1000 - selectedResident.score}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Manual Swap Hierarchical Action */}
            <div className="mt-2">
              <h4 className="text-sm font-semibold text-slate-900 mb-3 border-b border-slate-100 pb-2 flex items-center gap-2">
                <ArrowRightLeft className="w-4 h-4 text-indigo-500" /> Alternativas de Reemplazo
              </h4>

              {/* TIER 1: Capitados y Convocados */}
              <div className="mb-4">
                <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <Check className="w-3 h-3" /> 1. Capacitados y Convocados ({tier1.length})
                </span>
                <div className="space-y-2">
                  {tier1.map((alt, i) => (
                    <button key={i} onClick={() => handleSwapResident(alt.id)} className={`w-full text-left p-3 rounded-lg border-2 transition-all flex justify-between items-center group
                      ${alt.isBusy ? 'border-slate-200 bg-slate-50 cursor-not-allowed opacity-75' : 'border-emerald-200 bg-emerald-50 hover:border-emerald-400'}`}>
                      <div>
                        <div className={`font-bold text-sm ${alt.isBusy ? 'text-slate-600' : 'text-emerald-900'}`}>{alt.name}</div>
                        <div className={`text-[10px] font-medium mt-0.5 ${alt.isBusy ? 'text-rose-500' : 'text-emerald-700'}`}>{alt.reason}</div>
                      </div>
                      {alt.isBusy && <span className="text-xs bg-rose-100 text-rose-700 p-1 px-2 rounded-md border border-rose-200 shadow-sm">Bloqueado 🔒</span>}
                    </button>
                  ))}
                </div>
              </div>

              {/* TIER 2: NO Capitados y Convocados */}
              <div className="mb-4">
                <span className="text-[10px] font-bold text-amber-600 uppercase tracking-wider mb-1.5 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" /> 2. No Capacitados & Convocados ({tier2.length})
                </span>
                <div className="space-y-1.5 opacity-90 transition-opacity hover:opacity-100">
                  {tier2.map((alt, i) => (
                    <button key={i} onClick={() => handleSwapResident(alt.id)} className={`w-full text-left p-2.5 rounded-md border transition-all flex justify-between items-center group
                      ${alt.isBusy ? 'border-slate-200 bg-slate-50 opacity-70 cursor-not-allowed' : 'border-amber-200 bg-amber-50 hover:bg-amber-100'}`}>
                      <div>
                        <div className={`font-semibold text-xs ${alt.isBusy ? 'text-slate-500' : 'text-amber-900'}`}>{alt.name}</div>
                        <div className={`text-[9px] leading-tight mt-0.5 ${alt.isBusy ? 'text-rose-400 font-bold' : 'text-amber-700'}`}>{alt.reason}</div>
                      </div>
                      {alt.isBusy && <span className="text-[10px] bg-rose-50 text-rose-600 p-0.5 px-1.5 rounded border border-rose-100">🔒</span>}
                    </button>
                  ))}
                </div>
              </div>

              {/* TIER 3: Capitados y DESCANSOS */}
              <div className="mb-4">
                <span className="text-[9px] font-bold text-rose-500 uppercase tracking-wider mb-1 block">
                  3. Capacitados & Descanso ({tier3.length})
                </span>
                <div className="space-y-1 opacity-75 hover:opacity-100 transition-opacity">
                  {tier3.map((alt, i) => (
                    <button key={i} onClick={() => handleSwapResident(alt.id)} className="w-full text-left p-2 rounded border border-rose-200 hover:bg-rose-50 flex justify-between items-center">
                      <div>
                        <div className="font-medium text-[11px] text-rose-800">{alt.name} <span className="text-[9px] text-rose-500 ml-1">({alt.reason})</span></div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* TIER 4: NO Capitados y DESCANSOS */}
              <div className="mb-2">
                <span className="text-[8px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">
                  4. No Capacitados & Descanso (Último Recurso) ({tier4.length})
                </span>
                <div className="space-y-1 opacity-50 hover:opacity-100 transition-opacity">
                  {tier4.map((alt, i) => (
                    <button key={i} onClick={() => handleSwapResident(alt.id)} className="w-full text-left p-1.5 rounded border border-slate-200 hover:bg-slate-100 flex justify-between items-center">
                      <div className="font-medium text-[10px] text-slate-600">{alt.name}</div>
                    </button>
                  ))}
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>
    );
  };

  // Render Componente de Opciones para Vacante Seleccionado
  const renderVacantActionSidebar = () => {
    if (!selectedVacant) return null;

    const resDb = allResidentsDb.find(r => r.id === selectedVacant.id);
    const date = selectedVacant.date;
    const cuposDelDia = calendarDb[date] || {};

    // Obtener los asignados
    const assignmentsOfDate = assignmentsDb[date] || {};

    // Separar en dos tiers: Capacitado vs No Capacitado, usando directamente todos los dispositivos
    const yyyy = selectedMonth.split(" ")[1] || "2026";
    const [d, mStr] = selectedVacant.date.split("/");
    const fechaDB = `${yyyy}-${mStr}-${d}`;

    const devCapacitados = dbDevices.filter(d => resDb?.caps[d.id] && resDb.caps[d.id] <= fechaDB);
    const devNoCapacitados = dbDevices.filter(d => !resDb?.caps[d.id] || resDb.caps[d.id] > fechaDB);

    return (
      <div className="w-[450px] overflow-hidden bg-white border-l border-slate-200 shadow-2xl transition-all duration-300 flex flex-col absolute right-0 h-full z-40">
        <div className="h-full flex flex-col">
          <div className="p-6 border-b border-indigo-100 bg-indigo-50 transition-colors">
            <div className="flex justify-between items-start mb-2 relative z-10">
              <div>
                <span className="text-[10px] font-bold tracking-wider uppercase mb-1 block opacity-70 text-indigo-800">Ubicación de Vacante</span>
                <h3 className="text-2xl font-bold text-indigo-900 tracking-tight">{selectedVacant.name}</h3>
              </div>
              <button onClick={() => setSelectedVacant(null)} className="opacity-60 hover:opacity-100 text-indigo-900 bg-white p-1.5 rounded-md mix-blend-multiply cursor-pointer">
                ✕
              </button>
            </div>
            <div className="mt-2 text-xs text-indigo-800">
              Fechas a ubicar: <span className="font-bold">{selectedVacant.date}</span>
            </div>
          </div>

          <div className="p-0 flex-1 overflow-y-auto bg-slate-50">
            <div className="px-6 py-4">
              <h4 className="text-sm font-semibold text-slate-800 mb-3 border-b border-slate-200 pb-2">Posibles Dispositivos con Huecos</h4>

              {/* Tier 1: Capacitados */}
              <div className="mb-6">
                <span className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <Check className="w-3 h-3" /> 1. Está Capacitado
                </span>
                {devCapacitados.length === 0 ? (
                  <div className="text-xs text-slate-500 italic p-2">Ningún cupo vacío donde tenga capacitación.</div>
                ) : (
                  <div className="space-y-2">
                    {devCapacitados.map(d => {
                      const floorColors = getFloorColor(d.name).replace('border', 'border-2');
                      return (
                        <button
                          key={d.id}
                          onClick={() => handleAssignVacant(d.id)}
                          className={`w-full text-left p-3 rounded-lg transition-all flex justify-between items-center hover:opacity-80 shadow-sm ${floorColors}`}
                        >
                          <div>
                            <div className="font-bold text-sm leading-tight">{d.name}</div>
                            <div className="text-[10px] font-medium mt-1 opacity-80">Ocupación: {assignmentsOfDate[d.id]?.length || 0} de {cuposDelDia[d.id]}</div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Tier 2: No Capacitado */}
              <div className="mb-4">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" /> 2. NO Está Capacitado
                </span>
                {devNoCapacitados.length === 0 ? (
                  <div className="text-xs text-slate-400 italic p-2">Ningún cupo vacío adicional.</div>
                ) : (
                  <div className="space-y-1.5">
                    {devNoCapacitados.map(d => (
                      <button
                        key={d.id}
                        onClick={() => handleAssignVacant(d.id)}
                        className="w-full text-left p-2.5 rounded-md border border-slate-200 bg-slate-50 hover:bg-slate-100 transition-all flex justify-between items-center"
                      >
                        <div>
                          <div className="font-medium text-xs text-slate-700">{d.name}</div>
                          <div className="text-[9px] text-slate-500 mt-0.5">Ocupación: {assignmentsOfDate[d.id]?.length || 0} de {cuposDelDia[d.id]}</div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans selection:bg-indigo-100 flex flex-col relative overflow-hidden">

      {/* HEADER — oculto en modo candado */}
      {!(isLocked && activeTab === 'menu') && (
        <>
          <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between sticky top-0 z-20 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="bg-indigo-600 p-2 rounded-lg text-white shadow-sm">
                <Calendar className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-xl font-bold text-slate-900 tracking-tight leading-tight">Asignaciones</h1>
                  <select
                    className="bg-slate-100 border border-slate-200 rounded-md px-2 py-0.5 text-xs font-bold text-slate-700 outline-none hover:bg-slate-200 cursor-pointer"
                    value={selectedMonth}
                    onChange={(e) => setSelectedMonth(e.target.value)}
                  >
                    {MOCK_MONTHS.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
              </div>
            </div>

            {/* Toggle Mode */}
            <div className="flex bg-slate-100 p-1 rounded-lg border border-slate-200 shadow-inner">
              <button
                onClick={() => { setActiveTab('plan'); setSelectedResident(null); setSelectedDevice(null) }}
                className={`px-4 py-1.5 text-sm font-bold rounded-md transition-all ${activeTab === 'plan' ? 'bg-white shadow-sm text-indigo-700 border border-slate-200/50' : 'text-slate-500 hover:text-slate-700'}`}
              >
                Matriz de Planificación
              </button>
              <button
                onClick={() => { setActiveTab('exec'); setSelectedResident(null); setSelectedDevice(null) }}
                className={`px-4 py-1.5 text-sm font-bold rounded-md transition-all ${activeTab === 'exec' ? 'bg-white shadow-sm text-rose-600 border border-slate-200/50' : 'text-slate-500 hover:text-slate-700'}`}
              >
                Apertura / Inasistencias
              </button>
              <button
                onClick={() => { setActiveTab('devices'); setSelectedResident(null); setSelectedDevice(null) }}
                className={`px-4 py-1.5 text-sm font-bold rounded-md transition-all ${activeTab === 'devices' ? 'bg-white shadow-sm text-indigo-700 border border-slate-200/50' : 'text-slate-500 hover:text-slate-700'}`}
              >
                Dispositivos
              </button>
            </div>

            {/* Global Save Actions */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => { setActiveTab(activeTab === 'menu' ? 'plan' : 'menu'); setSelectedResident(null); setSelectedDevice(null); }}
                className={`w-10 h-10 flex items-center justify-center bg-gradient-to-b ${activeTab === 'menu' ? 'from-amber-200 to-yellow-300 border-amber-500 ring-2 ring-amber-300' : 'from-amber-50 to-yellow-100 border-amber-300'} border-2 text-amber-700 hover:from-yellow-100 hover:to-amber-200 hover:border-amber-400 hover:text-amber-800 rounded-full transition-all shadow-[0_0_15px_rgba(251,191,36,0.4)] tooltip-trigger relative group`}
                title="Menú Visual de Asignaciones (El Molino)"
              >
                {/* Vista Aérea Múltiples Paraboloides Interconectados (Bóvedas Amancio) */}
                <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 opacity-90 drop-shadow-sm">
                  {/* Bóveda 1 (Arriba Izquierda) */}
                  <circle cx="7" cy="7" r="4.5" fillOpacity="0.8" />
                  <circle cx="7" cy="7" r="1.5" fill="white" fillOpacity="0.5" />
                  {/* Bóveda 2 (Arriba Derecha) */}
                  <circle cx="17" cy="7" r="4.5" fillOpacity="0.8" />
                  <circle cx="17" cy="7" r="1.5" fill="white" fillOpacity="0.5" />
                  {/* Bóveda 3 (Abajo Izquierda) */}
                  <circle cx="7" cy="17" r="4.5" fillOpacity="0.8" />
                  <circle cx="7" cy="17" r="1.5" fill="white" fillOpacity="0.5" />
                  {/* Bóveda 4 (Abajo Derecha) */}
                  <circle cx="17" cy="17" r="4.5" fillOpacity="0.8" />
                  <circle cx="17" cy="17" r="1.5" fill="white" fillOpacity="0.5" />

                  {/* Conexiones de la Losa Nervada Central */}
                  <path d="M7 11.5 v1 M17 11.5 v1 M11.5 7 h1 M11.5 17 h1" stroke="white" strokeWidth="1" strokeLinecap="round" />
                </svg>
              </button>
              <button
                onClick={() => {
                  if (undoStack.length === 0) {
                    alert("No hay acciones recientes para deshacer en esta sesión.");
                    return;
                  }
                  handleUndoLastAction();
                }}
                className={`font-bold px-4 py-1.5 rounded-xl transition-colors shadow-sm text-sm border-2 flex items-center gap-1.5
              ${undoStack.length > 0 ? 'bg-white border-indigo-300 text-indigo-700 hover:bg-indigo-50' : 'bg-slate-50 border-slate-200 text-slate-400 cursor-not-allowed'}
            `}
              >
                <Undo2 className="w-4 h-4" /> Deshacer ({undoStack.length})
              </button>
              <button
                onClick={handleRunAI}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-4 py-1.5 rounded-xl transition-colors shadow-md text-sm flex items-center gap-2"
              >
                🔮 Generar
              </button>
            </div>
          </header>
        </>
      )}

      <div className="flex flex-1 relative overflow-hidden">
        {renderResidentSidebar()}
        {renderVacantActionSidebar()}
        {renderVacantsSidebar()}

        {/* ======================= */}
        {/* DEVICES MENU SIDEBAR    */}
        {/* ======================= */}
        {showDevicesMenu && (
          <div className="w-[450px] bg-white border-l border-slate-200 shadow-2xl transition-all duration-300 flex flex-col absolute right-0 h-full z-[60] overflow-hidden">
            <div className="h-full flex flex-col">
              <div className="p-5 border-b border-indigo-100 bg-indigo-50/50 flex justify-between items-center">
                <div>
                  <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                    <Settings className="w-5 h-5 text-indigo-600" /> Panel de Dispositivos
                  </h3>
                  <p className="text-xs text-slate-500 font-medium mt-1">Habilita dispositivos cerrados o baja los activos al pool.</p>
                </div>
                <button onClick={() => setShowDevicesMenu(false)} className="bg-white hover:bg-slate-100 text-slate-500 p-1.5 rounded-lg border border-slate-200 transition-colors">
                  ✕
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50">
                {dbDevices.map(device => {
                  const assignmentsToday = assignmentsDb[execDate]?.[device.id] || [];
                  const isOpen = assignmentsToday.length > 0;
                  const isExpanded = expandedDeviceForAssignment === device.id;

                  // Find unassigned residents for the dropdown
                  const unassignedResidents = dbResidents.filter(r => {
                    let isAss = false;
                    Object.values(assignmentsDb[execDate] || {}).forEach(arr => {
                      if (arr.find(a => a.name.includes(r.apellido) || a.name.includes(r.nombre))) isAss = true;
                    });
                    return !isAss;
                  });

                  if (isOpen) {
                    return (
                      <div key={device.id} className={`border border-slate-200 rounded-xl overflow-hidden shadow-sm ${getFloorColor(device.name)}`}>
                        <div className="px-4 py-3 border-b border-slate-200/50 flex justify-between items-center">
                          <div>
                            <h4 className="font-bold text-sm text-slate-900">{device.name}</h4>
                            <span className="text-[10px] font-bold uppercase tracking-wide opacity-70">Operativo</span>
                          </div>
                          <span className="bg-white/50 text-xs font-bold px-2 py-1 rounded shadow-sm border border-slate-200/50">{assignmentsToday.length} Asignado/s</span>
                        </div>
                        <div className="p-3 bg-white space-y-2">
                          {assignmentsToday.map((a, i) => (
                            <div key={i} className="flex items-center justify-between text-sm font-medium text-slate-700 bg-slate-50 p-2 rounded border border-slate-100">
                              <span>{a.name}</span>
                              <button
                                onClick={() => toggleAbsent(a.name, device.name)}
                                className="text-[10px] text-rose-600 hover:text-white hover:bg-rose-500 border border-rose-200 px-2 py-1 rounded transition-colors"
                              >
                                Cerrar y Bajar
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  } else {
                    return (
                      <div key={device.id} className="border border-slate-200 bg-white rounded-xl overflow-hidden shadow-sm opacity-80 hover:opacity-100 transition-opacity">
                        <div
                          className="px-4 py-3 flex justify-between items-center cursor-pointer hover:bg-slate-50"
                          onClick={() => setExpandedDeviceForAssignment(isExpanded ? null : String(device.id))}
                        >
                          <div>
                            <h4 className="font-bold text-sm text-slate-500">{device.name}</h4>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Inactivo / Cerrado</span>
                          </div>
                          <button className="text-xs bg-slate-100 text-slate-600 border border-slate-200 font-bold px-3 py-1.5 rounded hover:bg-indigo-50 hover:text-indigo-700 hover:border-indigo-300 transition-colors">
                            {isExpanded ? 'Ocultar' : 'Abrir +'}
                          </button>
                        </div>

                        {isExpanded && (
                          <div className="p-3 bg-slate-50 border-t border-slate-100 space-y-1 max-h-48 overflow-y-auto">
                            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Residentes Sin Asignar:</div>
                            {unassignedResidents.length === 0 ? (
                              <div className="text-xs text-slate-500 italic p-2 text-center">No hay residentes libres para asignar.</div>
                            ) : (
                              unassignedResidents.map((ur, idx) => (
                                <button
                                  key={idx}
                                  onClick={() => handleAssignToDevice(ur.apellido, device.id)}
                                  className="w-full text-left p-2 rounded text-xs border border-slate-200 bg-white hover:border-indigo-400 hover:bg-indigo-50 flex justify-between items-center group transition-colors"
                                >
                                  <span className="font-bold text-slate-700 group-hover:text-indigo-800">{ur.apellido}, {ur.nombre}</span>
                                  <span className="text-[9px] text-slate-400 group-hover:text-indigo-500">Asignar aquí →</span>
                                </button>
                              ))
                            )}
                          </div>
                        )}
                      </div>
                    );
                  }
                })}
              </div>
            </div>
          </div>
        )}

        {/* ======================= */}
        {/* PLANIFICATION TAB       */}
        {/* ======================= */}
        {activeTab === 'plan' && (
          <main className="flex w-full absolute inset-0 overflow-hidden">
            {/* MAIN GRID */}
            <div className="flex-1 overflow-auto p-6 bg-slate-50/50">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-2xl font-semibold text-slate-800 tracking-tight">Matriz Mensual </h2>
                  <p className="text-slate-500 text-sm mt-1">Haz clic en dispositivos o residentes para reasignar y ver tableros detallados.</p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setShowVacantsSidebar(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg hover:bg-rose-100 transition-colors shadow-sm font-bold text-sm relative"
                  >
                    <UserMinus className="w-4 h-4" />
                    Ver Vacantes / Sin Asignar
                  </button>
                </div>
              </div>



              <div className="bg-white border border-slate-200 rounded-xl shadow-md overflow-x-auto w-full pb-2 scroll-smooth">
                <table className="w-full text-left border-collapse min-w-max">
                  <thead>
                    <tr className="bg-slate-100 border-b border-slate-200">
                      <th className="font-bold text-slate-700 px-4 py-3 border-r border-slate-200 w-48 break-words text-xs whitespace-normal">Dispositivo</th>
                      {activeDates.map(d => {
                        const assignedIds = new Set();
                        Object.values(assignmentsDb[d] || {}).forEach(arr => {
                          arr.forEach((r: any) => assignedIds.add(r.id));
                        });
                        const totalConvocados = (convocadosDb[d] || []).length;
                        const libres = totalConvocados - assignedIds.size;

                        let totalPlaces = 0;
                        dbDevices.forEach(device => {
                          const cap = calendarDb[d]?.[device.id] || 0;
                          totalPlaces += cap;
                        });
                        const emptySeats = totalPlaces - assignedIds.size;

                        return (
                          <th
                            key={d}
                            onClick={() => selectedDevice && setSelectedDateFilter(selectedDateFilter === d ? null : d)}
                            className={`font-bold px-4 py-3 text-center border-r border-slate-200 transition-colors
                              ${selectedDevice ? 'cursor-pointer hover:bg-indigo-100 hover:text-indigo-800' : 'text-slate-700'}
                              ${selectedDateFilter === d ? 'bg-indigo-600 text-white border-b-4 border-b-indigo-800' : ''}
                            `}
                          >
                            <div className="flex flex-col items-center justify-center">
                              <span>{d}</span>
                              <div className="flex items-center gap-2 mt-1.5">
                                <div className={`px-1.5 py-0.5 rounded shadow-sm text-[9px] font-black tracking-widest flex items-center gap-1 ${libres > 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-700'}`}>
                                  <User className="w-2.5 h-2.5" />
                                  <span>{libres} LIBR.</span>
                                </div>
                                <div className="px-1.5 py-0.5 bg-slate-200 text-slate-700 rounded shadow-sm text-[9px] font-black tracking-widest flex items-center gap-1">
                                  <MonitorSmartphone className="w-2.5 h-2.5" />
                                  <span>{emptySeats} VAC.</span>
                                </div>
                              </div>
                            </div>
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody>
                    {dbDevices.map(device => (
                      <tr key={device.id} className="border-b border-slate-100 hover:bg-slate-50/80 transition-colors group">
                        <td
                          onClick={() => { setSelectedDevice(device); setSelectedResident(null); }}
                          className={`px-4 py-3 border-r border-slate-200 cursor-pointer transition-colors whitespace-normal break-words text-xs ${getFloorColor(device.name)} ${selectedDevice?.id === device.id ? 'ring-2 ring-inset ring-indigo-500 font-bold' : 'font-semibold'}`}
                        >
                          {device.name}
                          <div className="text-[9px] font-mono text-slate-500 mt-1 uppercase tracking-widest opacity-80">Rango: {device.min}-{device.max}</div>
                        </td>

                        {activeDates.map((date, dateIdx) => {
                          const assignments = assignmentsDb[date]?.[device.id] || [];
                          const min = device.min;
                          const max = device.max;
                          const current = assignments.length;
                          const isUnderMin = current < min;
                          const isOverMax = current > max;

                          let statusClass = '';
                          if (isUnderMin) {
                            statusClass = 'bg-rose-50 border-rose-200';
                          } else if (isOverMax) {
                            statusClass = 'bg-amber-50 border-amber-200';
                          } else if (current > 0) {
                            statusClass = 'bg-emerald-50 border-emerald-200';
                          } else {
                            statusClass = 'bg-slate-50 border-slate-200';
                          }

                          return (
                            <td key={date} className="px-1.5 py-1.5 border-r border-slate-200 align-top">
                              <div
                                onClick={() => { setSelectedDevice(device); setSelectedDateFilter(date); setSelectedResident(null); }}
                                className={`flex flex-col gap-1.5 p-1 rounded-md cursor-pointer hover:ring-2 hover:ring-indigo-300 transition-all min-h-[4rem] h-full ${statusClass}`}
                              >
                                {assignments.length === 0 ? (
                                  <div className="text-center text-slate-300 text-sm font-mono mt-2">—</div>
                                ) : (
                                  assignments.map((res: any, idx: number) => (
                                    <button
                                      key={idx}
                                      onClick={(e) => { e.stopPropagation(); setSelectedResident({ id: res.id, name: res.name, score: res.score, device: device.name, date }); setSelectedDevice(null); }}
                                      className={`text-left px-2 py-1.5 rounded border text-sm flex justify-between items-center transition-all 
                                        ${getScoreColor(res.score)}
                                        ${selectedResident && selectedResident.name === res.name && selectedResident.date === date ? 'ring-2 ring-indigo-500 shadow-md scale-[1.03] z-10 font-bold' : 'hover:scale-[1.02] hover:shadow-sm'}`
                                      }
                                    >
                                      <span className={`font-bold truncate max-w-[120px] text-xs ${agentGroups[res.id] === 'A' ? 'text-indigo-900 border-b-2 border-indigo-400' : agentGroups[res.id] === 'B' ? 'text-rose-900 border-b-2 border-rose-400' : 'text-slate-800'}`}>
                                        {res.name}
                                      </span>
                                    </button>
                                  ))
                                )}
                              </div>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* SIDEBAR: DEVICE VIEW */}
            <div className={`w-[450px] overflow-hidden bg-white border-l border-slate-200 shadow-2xl transition-all duration-300 flex flex-col absolute right-0 h-full z-40 ${selectedDevice ? 'translate-x-0' : 'translate-x-[100%]'}`}>
              {selectedDevice && (
                <div className="h-full flex flex-col">
                  <div className={`p-6 border-b border-slate-100 ${getFloorColor(selectedDevice.name)} relative overflow-hidden transition-colors`}>
                    <div className="flex justify-between items-start mb-2 relative z-10">
                      <div>
                        <span className="text-[10px] font-bold tracking-wider uppercase mb-1 block opacity-70">Estado del Dispositivo</span>
                        <h3 className="text-2xl font-bold tracking-tight">{selectedDevice.name}</h3>
                      </div>
                      <button onClick={() => { setSelectedDevice(null); setSelectedDateFilter(null); }} className="opacity-60 hover:opacity-100 bg-white/30 p-1.5 rounded-md mix-blend-multiply">
                        ✕
                      </button>
                    </div>

                    {selectedDateFilter ? (
                      <div className="mt-4 bg-white/50 backdrop-blur-sm px-3 py-2 rounded border border-white/60 text-sm flex justify-between items-center shadow-sm">
                        <span className="font-semibold opacity-80">Mostrando filtros para el día:</span>
                        <span className="font-bold bg-white px-2 py-0.5 rounded shadow-sm opacity-90">{selectedDateFilter}</span>
                      </div>
                    ) : (
                      <div className="mt-4 bg-white/40 px-3 py-2 rounded text-xs opacity-80 border border-white/50 font-medium">
                        💡 <b>Tip:</b> Clickea una fecha en la cabecera de la tabla para ver quién está de Descanso o Convocado ese día puntual.
                      </div>
                    )}
                  </div>

                  <div className="p-0 flex-1 overflow-y-auto bg-slate-50">
                    <div className="px-6 py-4 border-b border-slate-200 bg-white sticky top-0 z-10">
                      <h4 className="text-sm font-bold text-slate-800">Padrones Generales</h4>
                      <p className="text-xs text-slate-500 font-medium">Listado de los 36 residentes</p>
                    </div>

                    <div className="p-4 space-y-2">
                      {(() => {
                        const yyyy = selectedMonth.split(" ")[1] || "2026";
                        const formattedSelectedDate = selectedDateFilter ? `${yyyy}-${selectedDateFilter.split("/")[1]}-${selectedDateFilter.split("/")[0]}` : null;

                        const convocadosHoy = selectedDateFilter ? new Set(convocadosDb[selectedDateFilter] || []) : null;

                        // Clonamos y ordenamos el padrón
                        const sortedResidents = [...allResidentsDb].sort((a, b) => {
                          // Extract capabilities based on date
                          const getCap = (res: any) => {
                            const capDateStr = res.caps[selectedDevice.id];
                            if (!capDateStr) return 0;
                            if (formattedSelectedDate && capDateStr > formattedSelectedDate) return 0;
                            return 1;
                          };
                          const capA = getCap(a);
                          const capB = getCap(b);

                          // Extract status
                          const isConvA = convocadosHoy ? (convocadosHoy.has(a.id) ? 1 : 0) : 1;
                          const isConvB = convocadosHoy ? (convocadosHoy.has(b.id) ? 1 : 0) : 1;
                          const isDescA = convocadosHoy ? (convocadosHoy.has(a.id) ? 0 : 1) : 0;
                          const isDescB = convocadosHoy ? (convocadosHoy.has(b.id) ? 0 : 1) : 0;

                          // Reglas de ordenamiento (Mayor a menor)
                          const getScore = (conv: number, desc: number, cap: number) => {
                            if (conv && cap) return 4;
                            if (conv && !cap) return 3;
                            if (desc && cap) return 2;
                            if (desc && !cap) return 1;
                            return 0; // No convocado
                          };

                          const pA = getScore(isConvA, isDescA, capA);
                          const pB = getScore(isConvB, isDescB, capB);

                          // Ordenar por Puntaje descendente, si hay empate por abecedario
                          if (pA !== pB) return pB - pA;
                          return a.name.localeCompare(b.name);
                        });

                        return sortedResidents.map((res, i) => {
                          let capDate = res.caps[selectedDevice.id] as string | undefined;
                          if (capDate && formattedSelectedDate && capDate > formattedSelectedDate) {
                            capDate = undefined; // Actua como no capacitado p/ esta fecha
                          }

                          const isConvocado = convocadosHoy ? convocadosHoy.has(res.id) : null;
                          const isNotCalled = isConvocado === false;

                          // Si seleccionó fecha y no está convocado ni operando, no lo mostramos (manteniendo UI limpia)
                          if (selectedDateFilter && isNotCalled) return null;

                          return (
                            <div key={i} className={`p-3 rounded-xl border ${capDate ? 'bg-white border-slate-300 shadow-sm' : 'bg-slate-100/50 border-slate-200/50 opacity-70'} flex items-center justify-between`}>
                              <div>
                                <div className="font-bold text-sm text-slate-800">{res.name}</div>
                                <div className="flex items-center gap-2 mt-1">
                                  {capDate ? (
                                    <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100/80 px-1.5 py-0.5 rounded flex items-center gap-1 border border-emerald-200">
                                      <Check className="w-3 h-3" /> Capacitado ({capDate})
                                    </span>
                                  ) : (
                                    <span className="text-[10px] font-bold text-slate-500 bg-slate-200/80 px-1.5 py-0.5 rounded flex items-center gap-1 border border-slate-300">
                                      <XCircle className="w-3 h-3" /> No capacitado para fecha
                                    </span>
                                  )}
                                </div>
                              </div>

                              {/* Visibility of Date Context */}
                              {selectedDateFilter && (
                                <div className="text-right">
                                  {isConvocado && (
                                    <div className="text-[10px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-1 rounded shadow-sm">
                                      🟢 CONVOCADO
                                    </div>
                                  )}
                                  {!isConvocado && (
                                    <div className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-1 rounded shadow-sm">
                                      🟠 DESCANSO
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        });
                      })()}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </main>
        )}

        {/* ======================= */}
        {/* EXECUTION (DAILY) TAB   */}
        {/* ======================= */}
        {activeTab === 'exec' && (
          <main className="flex-1 overflow-auto p-6 bg-slate-100 absolute inset-0">
            <div className="max-w-6xl mx-auto pb-20">

              <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                <div>
                  <h2 className="text-3xl font-bold text-slate-900 tracking-tight flex items-center gap-3">
                    Movimientos
                  </h2>
                </div>

                <div className="flex bg-indigo-50 border border-indigo-100 p-2.5 rounded-xl gap-3">
                  <div>
                    <label className="block text-[10px] font-bold text-indigo-800 uppercase tracking-wider mb-1.5 px-1 flex items-center gap-1">
                      <Calendar className="w-3 h-3" /> Fecha a operar
                    </label>
                    <select
                      className="w-full md:w-56 bg-white border border-indigo-200 rounded-lg px-3 py-2 text-sm font-bold text-indigo-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500 shadow-sm"
                      value={execDate}
                      onChange={(e) => setExecDate(e.target.value)}
                    >
                      {activeDates.map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </div>
                  <div className="flex items-end">
                    <button
                      onClick={() => setShowDevicesMenu(true)}
                      className="h-[38px] px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg text-sm transition-colors flex items-center gap-2 shadow-sm"
                    >
                      Menú
                    </button>
                  </div>
                </div>
              </div>

              {/* Inasistencia Tracker */}
              {absentResidents.length > 0 && (
                <div className="mb-6 bg-rose-50 border border-rose-200 rounded-2xl p-6 shadow-sm">
                  <div className="flex items-start gap-4">
                    <div className="bg-rose-100 p-3 rounded-full mt-1 border border-rose-200">
                      <AlertCircle className="w-6 h-6 text-rose-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-bold text-rose-900 text-xl">({absentResidents.length}) Residente(s) Ausente(s) Declarado(s)</h3>
                      <p className="text-sm font-medium text-rose-700 mb-5 mt-1">Acabas de bajar residentes de la grilla. Se generaron agujeros descubiertos en los cupos previstos.</p>

                      <div className="flex gap-4">
                        <button className="bg-rose-600 hover:bg-rose-700 text-white text-sm font-bold px-5 py-2.5 rounded-xl transition-colors shadow flex items-center gap-2 border border-rose-800">
                          ⚙️ Reasignación Automática
                        </button>
                        <button className="bg-white border-2 border-rose-200 text-rose-700 hover:bg-rose-50 hover:border-rose-300 text-sm font-bold px-5 py-2.5 rounded-xl transition-colors shadow-sm">
                          🔄 Sugerir Intercambios Clave (1x1)
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Daily Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">

                {/* P0: SIN ASIGNAR (Residentes Convocados) */}
                <div className="bg-amber-50 border-2 border-amber-300 rounded-2xl shadow-sm overflow-hidden flex flex-col hover:shadow-md transition-shadow relative">
                  <div className="absolute top-0 right-0 w-24 h-24 bg-amber-200/50 rounded-bl-full -z-0"></div>
                  <div className="px-4 py-3 border-b border-amber-300 flex items-center justify-between bg-amber-200/50 relative z-10">
                    <h4 className="font-bold text-amber-900 text-sm truncate flex-1 leading-snug flex items-center gap-2">
                      Sin Asignar
                    </h4>
                  </div>
                  <div className="p-4 flex-1 flex flex-col gap-3 relative z-10">

                    {/* Dynamic Residents */}
                    {(() => {
                      const date = execDate || activeDates[0];
                      if (!date) return null;

                      // Extract who is working today
                      const assignedIds = new Set();
                      Object.values(assignmentsDb[date] || {}).forEach((arr: any) => {
                        arr.forEach((r: any) => assignedIds.add(r.id));
                      });

                      const yyyy = selectedMonth.split(" ")[1] || "2026";
                      const formattedDate = date ? `${yyyy}-${date.split("/")[1]}-${date.split("/")[0]}` : null;

                      const convocados = new Set(convocadosDb[date] || []);
                      const freeRes = allResidentsDb.filter(r => convocados.has(r.id) && !assignedIds.has(r.id));

                      return freeRes.map(res => {
                        // Resumen de pisos:
                        const pisosCap: Record<string, number> = {};
                        Object.keys(res.caps).forEach(dId => {
                          // check date
                          const capDate = res.caps[dId];
                          if (formattedDate && capDate > formattedDate) return;

                          const dObj = dbDevices.find(dev => dev.id === dId);
                          if (dObj) {
                            const pisoName = dObj.name.substring(1, 3); // extract P1, P2
                            pisosCap[pisoName] = (pisosCap[pisoName] || 0) + 1;
                          }
                        });

                        return (
                          <div key={res.id} onClick={() => { setSelectedVacant({ id: res.id, name: res.name, date }); setShowVacantsSidebar(true); }} className="flex flex-col gap-2 p-3 rounded-xl border bg-white border-amber-300 shadow-sm hover:shadow transition-all group cursor-pointer hover:border-indigo-400">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-sm text-slate-900">{res.name}</span>
                            </div>
                            <div className="text-[10px] font-bold text-slate-500 uppercase mt-1">Capacitaciones resumidas:</div>
                            <div className="flex flex-wrap gap-1 mt-0.5">
                              {Object.keys(pisosCap).length === 0 ? (
                                <span className="bg-slate-100 text-rose-600 px-1.5 py-0.5 text-[9px] rounded font-bold border border-rose-200">Sin capacitaciones</span>
                              ) : (
                                Object.entries(pisosCap).map(([piso, count]) => {
                                  // Paleta Ux por piso:
                                  let colorClass = 'bg-slate-50 text-slate-800 border-slate-200';
                                  if (piso === 'P1') colorClass = 'bg-cyan-50 text-cyan-800 border-cyan-200';
                                  else if (piso === 'P2') colorClass = 'bg-rose-50 text-rose-800 border-rose-200';
                                  else if (piso === 'P3') colorClass = 'bg-amber-50 text-amber-800 border-amber-200';

                                  return (
                                    <span key={piso} className={`px-1.5 py-0.5 text-[9px] rounded font-bold border ${colorClass}`}>
                                      {piso}: {count} Disp.
                                    </span>
                                  )
                                })
                              )}
                            </div>
                            <button className="mt-2 w-full flex items-center justify-center gap-1.5 bg-amber-100 border border-amber-300 text-amber-800 group-hover:text-white group-hover:border-indigo-500 group-hover:bg-indigo-600 text-[10px] uppercase tracking-wider font-bold py-1.5 rounded-lg transition-colors shadow-sm">
                              Asignar
                            </button>
                          </div>
                        )
                      });
                    })()}


                    {/* Emergency Desacansos Button */}
                    <div className="mt-auto pt-4 border-t border-amber-200/50">
                      <button
                        onClick={() => setShowRestingModal(true)}
                        className="w-full flex items-center justify-center gap-2 bg-white border-2 border-slate-300 text-slate-600 hover:border-indigo-400 hover:bg-indigo-50 hover:text-indigo-700 text-xs font-bold py-2 rounded-xl transition-colors shadow-sm"
                      >
                        <UserPlus className="w-4 h-4" /> Buscar en "Descansos"
                      </button>
                    </div>
                  </div>
                </div>

                {dbDevices.map(device => {
                  const assignments = assignmentsDb[execDate]?.[device.id] || [];
                  if (assignments.length === 0) return null; // No abrir dispositivo vacío hoy

                  return (
                    <div key={device.id} className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden flex flex-col hover:shadow-md transition-shadow">
                      <div className={`px-4 py-3 border-b border-slate-200 flex items-center justify-between ${getFloorColor(device.name)}`}>
                        <h4 className="font-bold text-sm truncate flex-1 leading-snug">{device.name}</h4>
                      </div>
                      <div className="p-4 flex-1 flex flex-col gap-3">
                        {assignments.map((res: any, i: number) => {
                          const isAbsent = absentResidents.includes(res.name);
                          return (
                            <div key={i} className={`flex flex-col gap-2 p-3 rounded-xl border transition-colors ${isAbsent ? 'bg-rose-50 border-rose-200 border-dashed' : 'bg-slate-50 border-slate-200'}`}>

                              <div className="flex items-center justify-between">
                                <div className="flex flex-col">
                                  <span className={`font-bold text-sm ${isAbsent ? 'text-rose-700 line-through opacity-60' : 'text-slate-900'}`}>{res.name}</span>
                                  {isAbsent && <span className="text-[10px] text-rose-600 font-bold mt-0.5">MARCADO AUSENTE</span>}
                                </div>
                                <button
                                  onClick={async () => {
                                    if (confirm(`¿Quitar definitivamente a ${res.name} de este dispositivo para la fecha ${execDate}?`)) {
                                      setIsLoading(true);
                                      const yyyy = selectedMonth.split(" ")[1] || "2026";
                                      const [d, mStr] = execDate.split("/");
                                      const fechaDB = `${yyyy}-${mStr}-${d}`; // YYYY-MM-DD

                                      const { error } = await supabase.from('menu')
                                        .update({ id_dispositivo: 999, estado_ejecucion: 'planificado' })
                                        .eq('id_agente', res.id)
                                        .eq('fecha_asignacion', fechaDB);

                                      if (error) {
                                        alert("Error de base de datos: " + error.message);
                                        setIsLoading(false);
                                      } else {
                                        // UndoStack: registrar la acción para poder deshacerla
                                        pushUndo({
                                          fecha_asignacion: fechaDB,
                                          old_id_agente: res.id,
                                          old_id_dispositivo: device.id,
                                          action_type: 'quitar_inline'
                                        });
                                        window.location.reload();
                                      }
                                    }
                                  }}
                                  className={`text-[10px] px-2 py-1 rounded-md font-bold transition-colors border ${isAbsent ? 'bg-white text-rose-700 border-rose-300 hover:bg-rose-50' : 'bg-white text-slate-500 border-slate-300 hover:text-rose-600 hover:border-rose-400 shadow-sm'}`}
                                >
                                  Quitar
                                </button>
                              </div>

                              {/* Action Switch Device */}
                              {!isAbsent && (
                                <button
                                  onClick={() => { setSelectedResident({ id: res.id, name: res.name, score: res.score, device: device.name, date: execDate }); }}
                                  className="mt-1 w-full flex items-center justify-center gap-1.5 bg-white border border-slate-200 text-slate-600 hover:text-indigo-600 hover:border-indigo-300 hover:bg-indigo-50 text-[10px] uppercase tracking-wider font-bold py-1.5 rounded-lg transition-colors shadow-sm"
                                >
                                  <ArrowRightLeft className="w-3 h-3" /> Cambiar Residente
                                </button>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )
                })}
              </div>

            </div>
          </main>
        )}

        {/* ======================= */}
        {/* DISPOSITIVOS (CALENDAR) */}
        {/* ======================= */}
        {activeTab === 'devices' && (
          <main className="flex-1 overflow-auto p-6 bg-slate-100 absolute inset-0">
            <div className="max-w-7xl mx-auto pb-20">
              <div className="mb-6 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                <h2 className="text-3xl font-bold text-slate-900 tracking-tight flex items-center gap-3">
                  <Settings className="w-8 h-8 text-indigo-600" />
                  Matriz de Dispositivos (Mes)
                </h2>
                <p className="text-sm text-slate-500 mt-2 font-medium">Configura qué dispositivos abren y con cuántos residentes cada día del mes. El sistema alertará si hay desbalances respecto a los residentes convocados.</p>
              </div>

              {/* Daily Status and Metrics (Top Row) */}
              <div className="mb-6 flex gap-4 overflow-x-auto pb-2 px-2 snap-x">
                {activeDates.map(date => {
                  const count = convocadosCountDb[date] || 0;
                  const dCount = dbDevices.length;
                  // Metrics for vacancia
                  let totalPlaces = 0;
                  dbDevices.forEach(device => {
                    totalPlaces += calendarDb[date]?.[device.id] || 0;
                  });
                  const asignedTotal = (() => {
                    let total = 0;
                    Object.values(assignmentsDb[date] || {}).forEach((arr: any) => total += arr.length);
                    return total;
                  })();
                  const libres = count - asignedTotal;
                  const huecos = totalPlaces - asignedTotal;

                  return (
                    <div key={date + "-metric"} className="min-w-[200px] snap-center p-3 bg-white border border-slate-200 shadow-sm rounded-lg flex items-center justify-between">
                      <div>
                        <div className="font-bold text-slate-800 flex items-center gap-1.5">
                          <span className="bg-indigo-100 text-indigo-800 text-xs px-1.5 rounded">{date}</span>
                        </div>
                        <div className="text-xs text-slate-500 mt-1 font-medium">Convocados: <span className="text-slate-800">{count}</span></div>
                        <div className="text-[10px] font-bold uppercase text-indigo-600 mt-0.5 tracking-wider">Disp. Abiertos: {dCount}</div>
                      </div>
                      <div className={`flex flex-col gap-1 items-end`}>
                        {libres > 0 && <span className="bg-rose-50 text-rose-600 border border-rose-200 text-[9px] px-1.5 py-0.5 rounded font-bold shadow-sm">{libres} LIBR.</span>}
                        {huecos > 0 && <span className="bg-emerald-50 text-emerald-600 border border-emerald-200 text-[9px] px-1.5 py-0.5 rounded font-bold shadow-sm">{huecos} VAC.</span>}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr>
                        <th className="sticky left-0 bg-slate-100 p-3 border-b border-r border-slate-200 font-bold text-sm text-slate-700 min-w-[200px] z-20 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]">
                          Dispositivo
                        </th>
                        {activeDates.map(date => (
                          <th key={date} className="p-3 border-b border-r border-slate-200 font-bold text-xs text-center text-slate-600 min-w-[80px]">
                            {date}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {dbDevices.map(device => (
                        <tr key={device.id} className="hover:bg-slate-50 transition-colors group">
                          <td className="sticky left-0 bg-white group-hover:bg-slate-50 p-3 border-b border-r border-slate-200 z-10 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]">
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="font-bold text-sm text-slate-800">{device.name}</div>
                                <div className="text-[10px] text-slate-500 font-medium">Opt: {device.max}</div>
                              </div>
                              <div className="flex flex-col gap-1 opacity-10 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                                <button
                                  onClick={() => {
                                    const newDb = { ...calendarDb };
                                    activeDates.forEach(d => {
                                      if (!newDb[d]) newDb[d] = {};
                                      newDb[d][device.id] = 1;
                                    });
                                    setCalendarDb(newDb);
                                  }}
                                  className="text-[9px] bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold px-2 py-0.5 rounded border border-indigo-200 whitespace-nowrap"
                                >
                                  Mes (1)
                                </button>
                                <button
                                  onClick={() => {
                                    const newDb = { ...calendarDb };
                                    activeDates.forEach(d => {
                                      if (!newDb[d]) newDb[d] = {};
                                      newDb[d][device.id] = 0;
                                    });
                                    setCalendarDb(newDb);
                                  }}
                                  className="text-[9px] bg-slate-50 hover:bg-slate-200 text-slate-500 font-bold px-2 py-0.5 rounded border border-slate-200 whitespace-nowrap"
                                >
                                  Mes (0)
                                </button>
                              </div>
                            </div>
                          </td>
                          {activeDates.map(date => {
                            const cupo = calendarDb[date]?.[device.id] || 0;
                            return (
                              <td key={date} className="p-2 border-b border-r border-slate-200 text-center">
                                <input
                                  type="number"
                                  min={0}
                                  max={10}
                                  className={`w-full text-center text-sm font-bold p-1 rounded border outline-none transition-colors ${cupo > 0 ? 'bg-indigo-50 border-indigo-300 text-indigo-800' : 'bg-slate-50 border-slate-200 text-slate-400 hover:bg-slate-100'}`}
                                  value={cupo === 0 ? '' : cupo}
                                  placeholder="0"
                                  onChange={(e) => {
                                    const val = parseInt(e.target.value) || 0;
                                    const dateSet = calendarDb[date] || {};
                                    setCalendarDb({ ...calendarDb, [date]: { ...dateSet, [device.id]: val } });
                                  }}
                                />
                              </td>
                            )
                          })}
                        </tr>
                      ))}
                    </tbody>

                    {/* Bottom Dashboard / Balanceo */}
                    <tfoot className="bg-slate-100 sticky bottom-0 z-20 shadow-[0_-2px_10px_-2px_rgba(0,0,0,0.1)]">
                      <tr>
                        <td className="sticky left-0 bg-slate-100 p-3 border-t border-r border-slate-300 font-bold text-sm text-slate-800 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]">
                          Total Convocados
                        </td>
                        {activeDates.map(date => (
                          <td key={date} className="p-3 border-t border-r border-slate-300 font-bold text-center text-slate-800">
                            {convocadosCountDb[date] || 0}
                          </td>
                        ))}
                      </tr>
                      <tr>
                        <td className="sticky left-0 bg-slate-100 p-3 border-t border-r border-slate-300 font-bold text-sm text-slate-800 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)] bg-indigo-50">
                          Dispositivos Abiertos
                        </td>
                        {activeDates.map(date => {
                          let abiertos = 0;
                          if (calendarDb[date]) {
                            abiertos = Object.values(calendarDb[date]).filter(c => c > 0).length;
                          }
                          return (
                            <td key={date} className="p-3 border-t border-r border-slate-300 font-bold text-center text-indigo-900 bg-indigo-50/50">
                              {abiertos}
                            </td>
                          )
                        })}
                      </tr>
                      <tr>
                        <td className="sticky left-0 bg-slate-100 p-3 border-t border-r border-slate-300 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]">
                          <div className="font-bold text-sm text-slate-900">Métricas de Vacancia</div>
                          <div className="text-[10px] text-slate-500 font-medium leading-tight">Residentes libres vs Cupos vacíos</div>
                        </td>
                        {activeDates.map(date => {
                          const convocados = convocadosCountDb[date] || 0;
                          let asignados = 0;

                          // Sum records assigned from Matrix data
                          Object.values(assignmentsDb[date] || {}).forEach(arr => {
                            asignados += arr.length;
                          });

                          let cuposTotales = 0;
                          if (calendarDb[date]) {
                            cuposTotales = Object.values(calendarDb[date]).reduce((acc, curr) => acc + curr, 0);
                          }

                          const residentesVacantes = convocados - asignados;
                          const dispositivosVacantes = cuposTotales - asignados;

                          let rcClass = residentesVacantes > 0 ? 'bg-rose-100 text-rose-800 border-rose-300' : 'bg-emerald-50 text-emerald-800 border-emerald-200';
                          let dcClass = dispositivosVacantes > 0 ? 'bg-amber-100 text-amber-800 border-amber-300' : 'bg-slate-50 text-slate-500 border-slate-200';

                          if (cuposTotales === 0) return <td key={date} className="border-t border-r border-slate-300 p-2 text-center bg-slate-50 font-mono text-slate-300">-</td>;

                          return (
                            <td key={date} className="p-2 border-t border-r border-slate-300 text-center bg-white align-middle">
                              <div className="flex flex-col gap-1 w-full max-w-[4rem] mx-auto">
                                <div className={`flex items-center justify-between px-1.5 py-0.5 rounded text-[10px] font-bold border shadow-sm ${rcClass}`} title="Residentes Vacantes">
                                  <span>👤</span> <span>{residentesVacantes}</span>
                                </div>
                                <div className={`flex items-center justify-between px-1.5 py-0.5 rounded text-[10px] font-bold border shadow-sm ${dcClass}`} title="Cupos libres en Dispositivos">
                                  <span>🧩</span> <span>{dispositivosVacantes}</span>
                                </div>
                              </div>
                            </td>
                          )
                        })}
                      </tr>
                    </tfoot>
                  </table>
                </div>


              </div>
            </div>
          </main>
        )}

        {/* ======================= */}
        {/* MENÚ VISUAL (EL MOLINO) */}
        {/* ======================= */}
        {activeTab === 'menu' && (
          <main className="flex-1 overflow-auto bg-gradient-to-b from-stone-50 to-stone-100 absolute inset-0">
            {(() => {
              const menuDate = selectedDateFilter || activeDates[0] || '';
              const assignments = assignmentsDb[menuDate] || {};
              const convocadosHoy = new Set(convocadosDb[menuDate] || []);

              // Agrupar dispositivos por piso
              const pisos: Record<string, { device: typeof dbDevices[0], residents: any[] }[]> = { '1': [], '2': [], '3': [] };
              dbDevices.forEach(device => {
                const pisoMatch = device.name.match(/\(P(\d)\)/);
                const piso = pisoMatch ? pisoMatch[1] : '1';
                const deviceAssignments = assignments[device.id] || [];
                const cupo = calendarDb[menuDate]?.[device.id] || 0;
                if (cupo > 0 || deviceAssignments.length > 0) {
                  pisos[piso]?.push({ device, residents: deviceAssignments });
                }
              });

              // Residentes sin asignar (convocados sin mesa)
              const assignedIds = new Set<number>();
              Object.values(assignments).forEach((arr: any) => arr.forEach((r: any) => assignedIds.add(r.id)));
              const sinAsignar = allResidentsDb.filter(r => convocadosHoy.has(r.id) && !assignedIds.has(r.id));

              // Residentes en descanso (no convocados)
              const enDescanso = allResidentsDb.filter(r => !convocadosHoy.has(r.id));

              const pisoLabels: Record<string, { name: string, bg: string, text: string, border: string, accent: string }> = {
                '1': { name: 'PAPEL', bg: 'bg-cyan-50', text: 'text-cyan-900', border: 'border-cyan-200', accent: 'bg-cyan-600' },
                '2': { name: 'MADERA', bg: 'bg-rose-50', text: 'text-rose-900', border: 'border-rose-200', accent: 'bg-rose-600' },
                '3': { name: 'TEXTIL', bg: 'bg-amber-50', text: 'text-amber-900', border: 'border-amber-200', accent: 'bg-amber-600' },
              };

              return (
                <div className="max-w-4xl mx-auto px-6 py-8">
                  {/* Encabezado Institucional */}
                  <div className="text-center mb-8 relative">
                    {/* Botón candado */}
                    <button
                      onClick={() => setIsLocked(true)}
                      className="absolute right-0 top-0 w-8 h-8 flex items-center justify-center rounded-full bg-white/80 border border-stone-200 text-stone-400 hover:bg-stone-100 hover:text-stone-600 transition-all shadow-sm"
                      title="Bloquear vista"
                    >
                      <LockKeyhole className="w-3.5 h-3.5" />
                    </button>
                    <div className="inline-flex items-center gap-3 mb-3">
                      <div className="w-10 h-10 flex items-center justify-center bg-gradient-to-b from-amber-100 to-yellow-200 border-2 border-amber-300 rounded-full shadow-[0_0_12px_rgba(251,191,36,0.3)]">
                        <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 text-amber-700 opacity-90">
                          <circle cx="7" cy="7" r="4.5" fillOpacity="0.8" />
                          <circle cx="7" cy="7" r="1.5" fill="white" fillOpacity="0.5" />
                          <circle cx="17" cy="7" r="4.5" fillOpacity="0.8" />
                          <circle cx="17" cy="7" r="1.5" fill="white" fillOpacity="0.5" />
                          <circle cx="7" cy="17" r="4.5" fillOpacity="0.8" />
                          <circle cx="7" cy="17" r="1.5" fill="white" fillOpacity="0.5" />
                          <circle cx="17" cy="17" r="4.5" fillOpacity="0.8" />
                          <circle cx="17" cy="17" r="1.5" fill="white" fillOpacity="0.5" />
                          <path d="M7 11.5 v1 M17 11.5 v1 M11.5 7 h1 M11.5 17 h1" stroke="white" strokeWidth="1" strokeLinecap="round" />
                        </svg>
                      </div>
                      <h1 className="text-3xl font-black tracking-tight text-stone-800" style={{ fontFamily: "'Inter', sans-serif" }}>
                        El Molino Fábrica Cultural
                      </h1>
                    </div>
                    <div className="w-24 h-0.5 bg-gradient-to-r from-transparent via-amber-400 to-transparent mx-auto mb-4" />
                  </div>

                  {/* Selector de Fecha y Turno */}
                  <div className="bg-white rounded-2xl shadow-sm border border-stone-200 p-5 mb-6">
                    <div className="flex flex-col sm:flex-row items-center gap-4">
                      <div className="flex-1 w-full">
                        <label className="block text-[10px] uppercase tracking-wider font-bold text-stone-500 mb-1.5">Fecha</label>
                        <select
                          value={menuDate}
                          onChange={(e) => setSelectedDateFilter(e.target.value)}
                          className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm font-bold text-stone-800 focus:ring-2 focus:ring-amber-300 focus:border-amber-400 transition-all"
                        >
                          {activeDates.map(d => {
                            const [day, month] = d.split('/');
                            const dayNames = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
                            const yyyy = selectedMonth.split(' ')[1] || '2026';
                            const dateObj = new Date(parseInt(yyyy), parseInt(month) - 1, parseInt(day));
                            const dayName = dayNames[dateObj.getDay()];
                            return <option key={d} value={d}>{dayName} {d}</option>;
                          })}
                        </select>
                      </div>
                      <div className="flex-1 w-full">
                        <label className="block text-[10px] uppercase tracking-wider font-bold text-stone-500 mb-1.5">Tipo de Turno</label>
                        <select className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm font-bold text-stone-800 focus:ring-2 focus:ring-amber-300 focus:border-amber-400 transition-all">
                          <option>Apertura al Público</option>
                        </select>
                      </div>
                      <div className="flex flex-col items-center pt-4">
                        <span className="text-2xl font-black text-stone-700">{(convocadosCountDb[menuDate] || 0)}</span>
                        <span className="text-[9px] uppercase tracking-wider font-bold text-stone-400">Convocados</span>
                      </div>
                    </div>
                  </div>

                  {/* Dispositivos por Piso */}
                  {['1', '2', '3'].map(pisoNum => {
                    const pisoDevices = pisos[pisoNum] || [];
                    if (pisoDevices.length === 0) return null;
                    const style = pisoLabels[pisoNum];

                    return (
                      <div key={pisoNum} className="mb-6">
                        <div className={`flex items-center gap-2 mb-3`}>
                          <div className={`w-2 h-8 rounded-full ${style.accent}`} />
                          <h2 className={`text-lg font-black ${style.text} tracking-tight`}>{style.name}</h2>
                          <span className="text-xs font-bold text-stone-400 ml-1">({pisoDevices.length} dispositivos)</span>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {pisoDevices.map(({ device, residents }) => (
                            <div key={device.id} className={`${style.bg} ${style.border} border rounded-xl p-4 transition-all hover:shadow-md`}>
                              <div className="flex items-center justify-between mb-2">
                                <h3 className={`text-sm font-black ${style.text} truncate`}>
                                  {device.name.replace(/\(P\d\)\s*/, '')}
                                </h3>
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${style.accent} text-white`}>
                                  {residents.length}
                                </span>
                              </div>
                              {residents.length > 0 ? (
                                <div className="space-y-1.5">
                                  {residents.map((res: any, i: number) => (
                                    <div key={i} className="flex items-center gap-2 bg-white/70 rounded-lg px-3 py-2 border border-white/50">
                                      <User className="w-3.5 h-3.5 text-stone-400" />
                                      <span className="text-sm font-bold text-stone-800">{res.name}</span>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <div className="text-xs italic text-stone-400 py-2">Sin asignar</div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}

                  {/* Separador */}
                  <div className="w-full h-px bg-gradient-to-r from-transparent via-stone-300 to-transparent my-8" />

                  {/* Inasistencias */}
                  {sinAsignar.length > 0 && (
                    <div className="mb-6">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-2 h-8 rounded-full bg-rose-500" />
                        <h2 className="text-lg font-black text-rose-800 tracking-tight">Sin Asignar</h2>
                        <span className="text-xs font-bold text-stone-400 ml-1">({sinAsignar.length} residentes)</span>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {sinAsignar.map(res => (
                          <div key={res.id} className="bg-rose-50 border border-rose-200 rounded-xl px-3 py-2.5 flex items-center gap-2">
                            <AlertCircle className="w-3.5 h-3.5 text-rose-500" />
                            <span className="text-sm font-bold text-rose-800">{res.name}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Descansos */}
                  {enDescanso.length > 0 && (
                    <div className="mb-6">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-2 h-8 rounded-full bg-slate-400" />
                        <h2 className="text-lg font-black text-slate-600 tracking-tight">Descanso</h2>
                        <span className="text-xs font-bold text-stone-400 ml-1">({enDescanso.length} residentes)</span>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {enDescanso.map(res => (
                          <div key={res.id} className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 flex items-center gap-2">
                            <FileBox className="w-3.5 h-3.5 text-slate-400" />
                            <span className="text-sm font-bold text-slate-500">{res.name}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Botón de retorno (solo SVG paraboloide, sin texto) */}
                  <div className="text-center mt-10 mb-6">
                    <button
                      onClick={() => {
                        if (isLocked) {
                          const pin = window.prompt('Ingresá el código para volver a gestión:');
                          if (pin === MENU_PIN) {
                            setIsLocked(false);
                            setActiveTab('plan');
                          } else if (pin !== null) {
                            alert('❌ Código incorrecto.');
                          }
                          return;
                        }
                        setActiveTab('plan');
                      }}
                      className="inline-flex items-center justify-center w-12 h-12 bg-gradient-to-b from-amber-50 to-yellow-100 border-2 border-amber-300 text-amber-800 rounded-full hover:from-yellow-100 hover:to-amber-200 hover:border-amber-400 transition-all shadow-[0_0_15px_rgba(251,191,36,0.3)]"
                      title={isLocked ? 'Ingresar código para desbloquear' : 'Volver a Gestión'}
                    >
                      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 opacity-80">
                        <circle cx="7" cy="7" r="4.5" fillOpacity="0.8" />
                        <circle cx="17" cy="7" r="4.5" fillOpacity="0.8" />
                        <circle cx="7" cy="17" r="4.5" fillOpacity="0.8" />
                        <circle cx="17" cy="17" r="4.5" fillOpacity="0.8" />
                      </svg>
                    </button>
                  </div>
                </div>
              );
            })()}
          </main>
        )}

        {/* ======================= */}
        {/* MODAL: RESIDENTES EN DESCANSO */}
        {/* ======================= */}
        {showRestingModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
            <div className="bg-white rounded-2xl shadow-2xl w-[500px] max-w-full overflow-hidden flex flex-col border border-slate-200">
              <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                <div>
                  <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                    <UserPlus className="w-5 h-5 text-indigo-600" /> Plantilla en Descanso
                  </h3>
                  <p className="text-xs text-slate-500 font-medium mt-1">Convocados a descansar hoy. Solo usar en emergencias.</p>
                </div>
                <button onClick={() => setShowRestingModal(false)} className="bg-white hover:bg-slate-100 text-slate-500 p-1.5 rounded-lg border border-slate-200 transition-colors">
                  ✕
                </button>
              </div>
              <div className="p-5 overflow-y-auto max-h-[60vh] space-y-3 bg-slate-50/50">
                {(() => {
                  const date = execDate || activeDates[0];
                  if (!date) return <div className="text-xs text-slate-400 italic p-3">Seleccioná una fecha.</div>;

                  const convocadosHoy = new Set(convocadosDb[date] || []);
                  const assignedIds = new Set<number>();
                  Object.values(assignmentsDb[date] || {}).forEach((arr: any) => {
                    arr.forEach((r: any) => assignedIds.add(r.id));
                  });

                  // Residentes en descanso: los que NO están convocados hoy pero sí existen en el padrón
                  const restingResidents = allResidentsDb.filter(r => !convocadosHoy.has(r.id));

                  if (restingResidents.length === 0) return <div className="text-xs text-slate-400 italic p-3">No hay residentes en descanso para esta fecha.</div>;

                  return restingResidents.map(res => {
                    // Capacitaciones resumidas para display
                    const capNames = Object.keys(res.caps).map(dId => {
                      const dev = dbDevices.find(d => d.id === dId);
                      return dev ? dev.name.replace(/\(P\d+\)\s*/, '') : null;
                    }).filter(Boolean).slice(0, 3);

                    return (
                      <div key={res.id} className="p-3 bg-white border border-slate-200 rounded-xl shadow-sm hover:border-indigo-300 transition-all flex justify-between items-center group">
                        <div>
                          <div className="font-bold text-slate-800 text-sm">{res.name}</div>
                          <div className="text-[10px] font-medium text-slate-500 mt-1">
                            {capNames.length > 0 ? `Capacitado: ${capNames.join(', ')}` : 'Sin capacitaciones registradas'}
                          </div>
                        </div>
                        <button
                          onClick={() => handleAssignFromPool(res.name.split(' ')[0])}
                          className="bg-slate-100 text-indigo-700 hover:bg-indigo-600 hover:text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-colors border border-slate-200 hover:border-indigo-700"
                        >
                          Llamar y Asignar
                        </button>
                      </div>
                    );
                  });
                })()}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
