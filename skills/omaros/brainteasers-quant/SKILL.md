---
name: brainteasers-quant
description: "Produce y revisa las sesiones asíncronas de Brainteasers Quant para Hespérides: currículo V12, Beamer y TikZ estáticos y autocontenidos, teleprompter y 30–36 minutos por sesión. Úsala para su syllabus y sus vídeos dentro de Brainteasers_Quant."
---

# Brainteasers Quant · Asíncronas Hespérides

La unidad de producción es la sesión completa de **30–36 minutos**, repartida
en vídeos por dependencias conceptuales. Conserva los modos y entregables del
curso; una actualización del syllabus no equivale a producir sus vídeos.

## Fuentes y entregables

Las rutas siguientes parten de `OmarOS/05_Projects/Brainteasers_Quant`:

- Currículo: `V12_Apuntes_Definitivos/` — manual, cuaderno de 36 problemas y
  banco de 340. Lee la ficha AF2 en
  `ApuntesDefinitivos/03_Syllabus_Asincronas_Definitivo.md` y su entrada en
  `V12_Apuntes_Definitivos/programa/plan_sesiones_v12.json`. Deben concordar.
  AF2.n, capítulo n y prefijo del TeX no son equivalentes: comprueba títulos,
  etiquetas, enunciados y soluciones reales antes de seleccionar problemas.
- Lee el README y los materiales actuales de la sesión. La decisión vigente
  conserva contenido y división de las sesiones 1, 2 y 4; la 3 se reformula
  desde V12. V8–V11 son recursos históricos. Una nueva instrucción de Omar
  puede cambiar estas decisiones.
- Produce en `asincronas/sesion-NN/video-MM-slug/`, con dos cifras y
  `production_directory` concordante. **No uses `asincronas/v12/`**.
  Reutiliza las carpetas existentes y preserva sus versiones y trabajo previo.
- Cada vídeo producido incluye `presentacion/main.tex` y sus entradas,
  `guion-teleprompter.md` y `justificacion-pedagogica.md`. PDF, páginas
  renderizadas, registros de compilación y evidencia de revisión van en
  `build/`. El README de sesión mantiene objetivos, fuentes, duración,
  continuidad y estado real.
- Reutiliza `brainteasers-asincronas/_sistema` mediante los recursos de esta
  skill. Lee el [protocolo de producción](references/production_protocol.md)
  para formatos, comandos y estados; el
  [contrato visual](references/visual_contract.md) para generar o cambiar
  composición, geometría, color o TikZ. Leer referencias no autoriza editar
  otras sesiones ni el motor.

## Regla permanente de autonomía docente

El PDF debe permitir que un docente con los prerrequisitos declarados explique
el argumento sin conocer el teleprompter ni el banco. Incluye el enunciado
completo, objetos e hipótesis, significado de símbolos, pasos esenciales con
sus razones y conclusión interpretada. Un ID, una fórmula final o una remisión
externa no sustituyen esa explicación. La práctica diferida declara su tarea
completa sin fingir que ya está resuelta.

La autonomía corresponde al recorrido: una continuación identifica el problema
y retiene lo necesario, sin repetir toda la prueba. Al recuperar un caso de otro
vídeo, repón brevemente el enunciado y resultado usados. Repara las dependencias
y remisiones cuando retires material.

El teleprompter aporta locución, ritmo y ampliaciones opcionales. Toda
justificación necesaria también debe estar visible en el PDF.

## Equilibrio entre texto, figura y explicación

Cada frame tiene una idea reconocible, las frases necesarias para reconstruirla
y una figura o cuenta que haga trabajo explicativo. Conserva el paso difícil;
elimina paráfrasis y redistribuye antes de reducir tipografía. Evita tanto
páginas de apuntes como paredes de fórmulas o etiquetas sin argumento. No
impongas cuotas de palabras ni cajas introductorias y conclusivas idénticas.

La **sesión 05 revisada** es el modelo principal aprobado de composición, texto
y TikZ; la sesión 03 original es apoyo secundario. El vídeo 1 de la sesión 03
V12 no es modelo aprobado. La **paleta obligatoria es la de la sesión 02**.
El contrato visual identifica PDF, versiones, huellas y páginas de calibración:
contrasta los PDF reales, sin copiar defectos históricos.

Cada TikZ debe explicar una relación, construcción, distinción o prueba, con
geometría coherente, etiquetas legibles y conexiones inequívocas. Inspecciona
cada figura, incluso cuando varias comparten página. Una compilación limpia
no acredita significado, acabado ni legibilidad.

## Formato estático e identidad visual

- **Un frame produce una página física.** Todo contenido, color y resaltado
  permanece visible y fijo desde el inicio. Usa Beamer `handout` sin overlays,
  animaciones, revelados, cambios de opacidad ni variantes que los simulen.
  Evita `\only`, `\uncover`, `\visible`, `\onslide`, `\pause` y etapas;
  convertir material histórico a `handout` exige resolver variantes superpuestas.
- Cada vídeo abre con portada independiente; la primera página de contenido
  sitúa su pregunta. Narra situación, datos, reglas y pregunta de cada problema
  antes de resolverlo. La introducción también consume el presupuesto de tiempo.
- Numeración visible consecutiva desde la portada = 1. Número, `SLIDE` del
  guion y página física coinciden. Solo la última página lleva el punto rojo
  fijo de cierre; no añadas una página vacía para alojarlo.
- Reutiliza exactamente tema, tipografías por función, paleta, márgenes,
  títulos, figuras, numeración y cierre en todos los vídeos. Registra en el
  README la referencia y versión o huella utilizadas.

## Continuidad y complementariedad entre vídeos

Lee presentaciones y guiones de los vecinos inmediatos, también entre sesiones,
y las introducciones o usos de conceptos que dependan de ellos. Contrasta las
grabaciones si existen. Si el siguiente vídeo solo está planificado, declara
provisional esa continuidad.

Mantén en el README un mapa breve: qué recupera cada vídeo, qué capacidad nueva
construye, con qué problema o representación y qué pregunta prepara. La apertura
repone lo necesario; el cierre interpreta el resultado sin anticipar la clase
siguiente. El último vídeo cierra el curso sin inventar un sucesor.

Tras editar, recorre anterior → actual → posterior: busca duplicaciones,
prerrequisitos ocultos, notación incompatible y remisiones rotas. Registra los
archivos y páginas contrastados y la aportación propia de cada vídeo.
Documenta los ajustes de vecinos que queden fuera del encargo, sin ejecutarlos.

## Producción y revisión

1. Fija en el README capacidades, prerrequisitos, fuentes V12, identificadores
   de banco o cuaderno, continuidad y presupuesto conjunto de 30–36 minutos.
   Selecciona práctica por mecanismo y dificultad, sin imponer cuatro vídeos.
2. Diseña diapositivas y discurso juntos: problema accesible, objetos generales,
   mecanismo, caso, prueba y transferencia. Explicita qué cuenta como resultado,
   equivalencia y ley probabilística cuando sean necesarios. Una ampliación
   externa no cubre un prerrequisito oculto.
3. Usa `constellation.py skill-run omaros brainteasers-quant scripts/production.py init`
   solo cuando haga falta crear desde un plan; la plantilla aún requiere
   contenido. El protocolo documenta también `scripts/course_engine.py`,
   `audit` y `accept`.
4. Compila y renderiza la sesión; inspecciona **todas las páginas físicas**
   a resolución legible y cada TikZ. Una hoja de contacto solo orienta.
   Contrasta paleta, identidad, portada, numeración y cierre con la referencia.
5. Lee primero el PDF sin guion y reconstruye los problemas con lo visible.
   Después compara el teleprompter: integra información esencial ausente,
   elimina redundancias y revisa densidad y transiciones a tamaño de exposición.
   Registra las páginas de planteamiento y razonamiento de cada problema.
6. Repite compilación y revisión después de corregir. `accept` vincula la
   evidencia de cada página y `checks.palette` / `checks.tikz_quality` al
   material vigente. Defectos matemáticos, visuales, de autonomía o continuidad
   impiden dar la revisión por cerrada.

El teleprompter usa frases pronunciables, símbolos expresados oralmente,
referencias inequívocas y pausas reales. Modo A: exposición sobre página fija;
C: pausa con la misma página; B: escritura manual **solo si Omar la pide**.
Avanza únicamente al cambiar de página física. Una respuesta visible desde
el inicio permite reconstrucción, no un intento ciego.

Entrega los materiales y su estado real. `accept` acredita integridad de una
revisión declarada; no demuestra verdad matemática ni calidad por sí solo.
`artifacts_reviewed` y `recording_ready` son estados distintos: el segundo
requiere además las validaciones de entrega y un ensayo oral real confirmado,
no una estimación por palabras. La publicación sigue el contrato del proyecto.
Una auditoría sin cambios usa una copia si necesita recompilar y conserva
fuentes y estados. No crees ni ejecutes tests de software sin petición expresa.
