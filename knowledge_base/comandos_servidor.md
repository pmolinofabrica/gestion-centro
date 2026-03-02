# Comandos Útiles del Servidor (Local)

Si reinicias la computadora o el servidor de Next.js se cuelga, estos son los comandos que necesitas para volver a levantarlo manualmente desde la terminal:

## 1. Abrir la terminal y navegar a la carpeta del Frontend
```bash
cd /home/pablo/Documentos/gestion-centro/frontend
```

## 2. Matar cualquier proceso trabado (Opcional pero recomendado)
Si al intentar arrancar te dice "Port 3000 is already in use", corre esto:
```bash
fuser -k 3000/tcp 2>/dev/null || true
```

## 3. Iniciar el Servidor en modo Desarrollo
```bash
npm run dev
```

Una vez que diga `Ready in ...ms`, puedes abrir tu navegador en:
[http://localhost:3000](http://localhost:3000)

---
### Ejecutar Motor Python Manualmente (Para Pruebas)
Si estás modificando el archivo del motor y quieres ver qué imprime en consola sin pasar por la interfaz web:
```bash
cd /home/pablo/Documentos/gestion-centro/scripts/python
python3 motor_asignaciones_supabase.py
```
