# 1. ¿Cómo abrir el Vault en Obsidian correctamente?

1. Abre **Obsidian**.
2. Seguramente te abrió el "otro proyecto" que tenías vinculado por defecto. 
3. En la barra izquierda, abajo del todo (o arriba según el tema), verás un icono de **"Open another vault" (Abrir otra bóveda)** o un ícono que parece una bóveda de caja fuerte. Haz clic ahí.
4. Se abrirá una ventana emergente. Selecciona la opción **"Open folder as vault" (Abrir carpeta como bóveda)**.
5. Usa el explorador de archivos para ir a `/home/pablo/Documentos/gestion-centro/knowledge_base` (o selecciona toda la carpeta `gestion-centro` si prefieres tener todo el código visible en Obsidian).
6. ¡Listo! Ahora verás el archivo `Home.md` y `matriz_rotacion.md`.

Allí podrás ver la tabla con comodidad, ya que Obsidian la renderizará gigante y sin saltos de línea molestos. 

# 2. Análisis del Motor

Si lograste abrir la matriz, notarás en **`matriz_rotacion.md`** cómo en los fines de semana (ej. 28/03 y 29/03) el sistema prefiere asignar distintos residentes a los dispositivos en vez de usar al mismo el sábado y el domingo (bajándoles el score a los que ya trabajaron). 

También verás que el 07/03 y el 08/03 hay huecos o dispositivos con el candado **🔒 (Cerrado)** porque esos dispositivos aún no habían sido capacitados esa fecha (ej: si FÁBRICA DE PAPEL se capacitó el 10/03, esos primeros días del mes estará cerrado).

¿Pudiste abrirla bien? Si lo verificas y te parece correcto, el siguiente paso táctico es integrar esto con tu Google Apps Script.
