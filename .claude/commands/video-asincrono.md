---
name: video-asincrono
description: Producir o revisar un subvídeo asíncrono de Brainteasers Quant con presentación Hespérides, guion oral y justificación pedagógica. Usa V8 para teoría y problemas, los Markdown definitivos para la estructura y una revisión adversaria de verdad y comprensión.
---

# /video-asincrono

Produce o revisa una píldora del curso Brainteasers Quant. El resultado sigue
siendo ligero: exactamente una presentación PDF, un guion de teleprompter y
una justificación pedagógica. La revisión adversaria queda documentada dentro
de la justificación, no como un cuarto entregable.

## Antes de escribir

1. Lee `~/GitHub/brainteasers-asincronas/CLAUDE.md`,
   `_sistema/convenciones.md` y `_sistema/README.md`. Ese repo contiene el
   contrato de producción; este comando es su puerta de entrada.
2. Resuelve la raíz del curso con `BRAINTEASERS_ROOT`, o usa por defecto
   `~/OmarOS/05_Projects/Brainteasers_Quant`.
3. Construye un expediente de fuentes con esta jerarquía, que no se puede
   invertir:

   | Pregunta | Autoridad |
   | --- | --- |
   | ¿Dónde encaja el vídeo y qué función cumple? | Los `.md` de `ApuntesDefinitivos/`, usados solo para estructura, secuencia, minutaje e hilos |
   | ¿Cuál es la finalidad y el alcance reales? | `V8_Apuntes_Definitivos_corregida/latex/frontmatter/prefacio.tex` y `frontmatter/como_usar.tex` |
   | ¿Qué teoría, demostración y notación son correctas? | `V8_Apuntes_Definitivos_corregida/latex/` |
   | ¿Qué problema y solución se enseñan? | `V8_Apuntes_Definitivos_corregida/problemas/` |
   | ¿Cómo se construye la presentación? | `hesperides-beamer-template/` y su copia vendorizada en `_sistema/hesperides/` |

Los Markdown de `ApuntesDefinitivos` no prueban afirmaciones matemáticas ni
afirmaciones sobre la finalidad del curso. V0, V7 y QuantProf son procedencia
histórica, no fuentes directas. Si el syllabus conserva un ID antiguo, se
resuelve con `_sistema/scripts/resolver_problema.py <ID>`, que exige un
`ref_origen` único en `problemas/manifest/manifiesto.yaml` y devuelve los
archivos V8 exactos de enunciado y solución. Si falta o hay más de una
coincidencia, se detiene la producción y se informa de la ambigüedad.

## Pipeline obligatorio

1. Lee la ficha completa de la sesión y el lugar del vídeo dentro del arco
   real. La estructura observada de una sesión ya producida prevalece sobre
   una generalización. La sesión 01 tiene cinco vídeos y no se fuerza al molde
   habitual de cuatro.
2. Para un vídeo de encuadre o finalidad, lee siempre el prefacio y la guía de
   uso de V8. Para cualquier otro, lee además el mapa, fundamento o capítulo
   pertinente. Localiza en V8 el enunciado y la solución exactos del problema.
3. Distingue antes de redactar cada afirmación importante como hecho de V8,
   dato estructural, resultado derivado, evidencia externa o inferencia. Una
   afirmación externa sin fuente se elimina o se presenta explícitamente como
   inferencia, nunca como hecho.
4. Diseña slides y guion como una sola pieza. Conserva los modos A, B y C, la
   escritura manual sobre la slide congelada, el cronometraje realista, la
   paleta semántica y el oficio TikZ del sistema. Hespérides manda sobre la
   composición, tipografía y configuración de grabación.
5. Crea o versiona el vídeo con los scripts del repo. Compila, renderiza e
   inspecciona visualmente todas las páginas. Lee el guion entero en voz alta y
   reescribe lo que suene rígido, traducido o artificioso.
6. Busca literatura primaria o revisiones sistemáticas relevantes para las
   decisiones educativas concretas del vídeo. Empieza por
   `_sistema/referencias/evidencia-educativa.md`, comprueba la fuente original
   y amplía la búsqueda cuando el problema educativo sea otro. Registra en la
   justificación la decisión que sustenta cada referencia y el límite de
   transferencia. Una cita decorativa no cuenta.
7. Ejecuta una revisión adversaria independiente. Cuando haya un revisor o
   subagente disponible, entrégale los tres artefactos y los punteros a las
   fuentes, pero no la defensa del autor ni el veredicto esperado. Debe intentar
   refutar la matemática, la fidelidad a la finalidad de V8, la comprensión
   del alumno y la naturalidad oral. Busca hipótesis ocultas, saltos,
   contraejemplos, ambigüedades y afirmaciones que la fuente no sostenga.
   Repara y repite la revisión hasta que las cuatro dimensiones queden
   superadas.
8. Registra esas cuatro revisiones en `justificacion-pedagogica.md`, marca en
   el frontmatter del guion las revisiones de verdad, comprensión, finalidad y
   lectura oral como `superada`, y ejecuta `validar.py` hasta obtener `OK`.
9. Entrega solo las tres rutas finales. No commitees ni publiques nada salvo
   petición expresa de Omar.

## Guardarraíles

- El vault es de solo lectura salvo la carpeta de salida autorizada para el
  vídeo. No se modifica ninguna fuente V8, ningún Markdown estructural ni la
  plantilla Hespérides canónica.
- Un vídeo con `estado: aprobado` no se sobrescribe. Se crea `versions/vNN`.
- No se conserva una afirmación solo porque aparezca en un vídeo anterior.
  También los materiales ya producidos se someten a la nueva jerarquía.
- No se entrega sin PDF renderizado e inspeccionado, guion leído en voz alta,
  revisión adversaria documentada y `validar.py` en `OK`.
- El castellano debe sonar a Omar explicando: preciso, directo y respirable.
  Se eliminan muletillas de texto generado, entusiasmo vacío y calcos del
  inglés.

## Aliases

`/video`, `/pildora`.
