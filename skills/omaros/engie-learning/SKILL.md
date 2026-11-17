---
name: "engie-learning"
description: "Guarda y organiza aprendizajes aportados expresamente sobre ENGIE, pricing, hedging y operativa en OmarOS, con notas temáticas privadas y registro por fecha. Úsala para capturar, corregir o recuperar estos aprendizajes. Una consulta que solo pide explicar no autoriza guardar."
---

# Aprendizaje ENGIE

Conduce una captura en la sesión activa cuando Omar pida guardar u organizar lo
aprendido. «Hoy he aprendido… guarda y organiza lo que te voy a contar» activa el
recorrido. Si todavía no ha aportado el contenido, espera su relato sin inventarlo.
«Explícame cómo se prepara un hedge» permite consultar y responder, sin escribir.
La solicitud de captura autoriza títulos, carpetas y enlaces rutinarios.

1. Lee el contenido expresamente aportado y determina la fecha de aprendizaje.
   «Hoy» se resuelve con la fecha local de la sesión. Sin dato, usa `learned_on:
   null`; nunca lo deduzcas de mtime. Mantén separadas captura y actualización.
2. Busca primero con Fast Finder en ENGIE y las áreas pertinentes de `06`.
   Consulta también `learning.py query` en el área privada. Lee los candidatos,
   amplía con sinónimos si hace falta y divide búsquedas parciales. No repitas el
   inventario global ni leas conversaciones, correos o fuentes externas sin alcance.
3. Identifica preguntas o procedimientos estables. Reutiliza el `slug` temático
   existente y mejora su título sin renombrar el archivo. Crea otro tema solo si
   responde una pregunta independiente. La teoría general conserva su hogar.
   Si una nota existente ya explica la teoría, conserva su autoridad y guarda
   solo la ampliación profesional privada enlazada a ella, sin copiar su cuerpo.
   Las proyecciones regenerables se enlazan, no se editan para añadir aprendizajes.
4. Redacta el contenido canónico con sus fundamentos, condiciones, ejemplos y
   límites según lo realmente aportado. `body` contiene la explicación vigente
   completa que integra lo anterior y el aprendizaje nuevo. Atribuye por separado relato del usuario,
   fuente leída y propuesta IA. Haz visibles dudas, pasos desconocidos y
   contradicciones. No conviertas una discrepancia en sustitución silenciosa.
5. Prepara una captura según el [contrato](references/capture_contract.md).
   Asigna un UUID de evento estable antes del primer intento y consérvalo al
   reintentar. Una nueva sesión de estudio tiene otro evento, aunque use el mismo
   tema. Una corrección lleva un UUID nuevo y `correction_of`.
6. Ejecuta `prepare` y `apply` mediante la entrada central
   `python3 /Users/omarkhalil/GitHub/Constellation/constellation.py skill-run omaros engie-learning scripts/learning.py` del [contrato](references/capture_contract.md).
   Declara los destinos exactos preparados en un encargo local antes de aplicar.
   La captura exige el vault registrado en ese dispositivo. Comprueba el resultado y
   lee los archivos persistidos. Ante error, conserva la identidad y usa `status`
   o `recover`; una versión ajena exige releer y conciliar, nunca sobrescribir.
7. Confirma con enlaces absolutos a las notas temáticas y al registro diario.
   Explica las dudas que siguen abiertas y cualquier guardado incompleto.

El motor escribe exclusivamente en
`06_Knowledge_Base/Mathematics/Finance/ENGIE/Private/`. El diario contiene síntesis
y enlaces, y la explicación completa vive por tema. Si solo se ha repasado un
concepto, registra qué se entendió mejor en la síntesis diaria y conserva la
explicación vigente completa en la nota temática.

Este contenido permanece restringido: no se envía a Git, Quartz, diarios
personales, memoria ni servicios externos. No ejecutes un commit de capturas
privadas ni una traza pública: usa `mode: "local"` y el cierre descrito en el
contrato. Conserva originales laborales y su función en `03_Work`. La skill no
añade un proceso periódico, otra API ni llamadas a modelos: funciona cuando hay
una sesión activa y una petición adecuada. La rutina humana está en
la guía del vault `06_Knowledge_Base/Mathematics/Finance/ENGIE/00_Guia_y_Organizacion/guia-de-apuntes-y-aprendizajes.md`.
