---
name: "brainteasers-quant-notes"
description: "Redacta, amplía y revisa los apuntes del taller Brainteasers Quant en su versión más reciente, con castellano natural, fundamentos explícitos, detección de repeticiones y revisión matemática y TikZ. Úsala para capítulos, secciones y explicaciones del manual; las presentaciones asíncronas tienen su propia skill."
---

# BrainTeasersQuantNotes

Construye apuntes que permitan entender la pregunta, reconocer los objetos,
reconstruir el argumento y resolver una variación sin memorizar la solución.
La voz aprobada es la de V12; la arquitectura ontológica se calibra con la
nota de fundamentos financieros indicada en [criterio editorial](references/editorial.md).
Conserva lo que funciona y corrige sus lagunas. «La mejor explicación» es una
exigencia de trabajo y revisión, no una superioridad que debas proclamar.

## Encontrar el destino en cada encargo

El proyecto está en `05_Projects/Brainteasers_Quant/`, dentro de OmarOS.
Resuelve la versión **en cada petición**, también tras una continuación que
cambie el destino. No fijes V12 como versión perpetua ni uses la fecha de un PDF.

Usa el lanzador verificado del dispositivo y fija `CURSO` a la raíz real del
curso. Por ejemplo, para ubicar el manual desde cualquier directorio:

```sh
"${CODEX_HOME:-$HOME/.codex}/constellation/run" cli skill-run brainteasers-quant-notes context --root "$CURSO"
```

El helper de solo lectura compara números de versión, distingue el manual de
los repositorios de problemas y sigue sus `input`/`include` literales en orden.
Devuelve entrada, fuentes, capítulos, etiquetas, dependencias ausentes y avisos.
Su índice describe fuentes; **no calcula números impresos ni ejecuta TeX**.
Una carpeta nueva de apuntes sin entrada reconocible o dos variantes empatadas
requieren examinar los candidatos; no vuelvas silenciosamente a una edición anterior.
Lee el README local y verifica la entrada devuelta antes de escribir. El índice
maestro del proyecto puede estar desactualizado: contrástalo con fuentes reales.

Un archivo o una versión indicados por Omar prevalecen sobre el máximo numérico.
Para fijar una carpeta: `context.py --version RUTA`; para una entrada concreta:
`context.py --version RUTA --entry latex/main.tex`. Si cambia la organización,
localiza la entrada real con `rg --files`, léela y pásala explícitamente.
No inventes una estructura por conveniencia del script. Ante una ambigüedad
material sin evidencia suficiente, pregunta solo por esa elección y sigue
trabajando en la lectura y el diagnóstico independientes.

El destino editable es la **fuente integrada** que contiene el pasaje, no el
PDF, una copia exportada por capítulos ni un archivo TeX huérfano. Distingue
capítulo impreso, tema del syllabus y episodio: sus números pueden diferir.
Verifica título, etiqueta e inclusión; no asignes «tema 3» por el prefijo `03`.
Amplía el archivo existente cuando continúe su pregunta. Crea una sección o
capítulo nuevo solo si aporta una función independiente; intégralo en la entrada.
No abras una nueva versión salvo que Omar lo pida. Preserva cambios concurrentes.

## Leer el contexto y cuestionar la propuesta

Antes de redactar, lee el recorrido del manual, el capítulo afectado y sus
vecinos conceptuales. Consulta programa, syllabus, práctica y problemas cuando
determinen lo que se enseña o se presupone. Amplía la lectura a los pasajes que
introducen o usan la misma idea. No cargues todo el banco ni todas las ediciones
por sistema; las antiguas son antecedentes y calibración, no cobertura vigente.

Busca vocabulario, sinónimos, formulaciones equivalentes, ejemplos y resultados:

```sh
"${CODEX_HOME:-$HOME/.codex}/constellation/run" cli skill-run brainteasers-quant-notes context --root "$CURSO" --query 'equivalencia' --query 'mismo objeto' --query 'fibra'
```

Las coincidencias traen archivo, línea y contexto. El helper busca texto literal
sin distinguir tildes o mayúsculas; **no decide duplicaciones semánticas**.
Comprueba sus avisos y amplía con `rg -n` a las fuentes pertinentes. Lee los
pasajes encontrados completos y compara pregunta, mecanismo, prueba y capacidad
que construyen. Ausencia de coincidencias no prueba ausencia de cobertura.

Clasifica el material como fundamento ya desarrollado, recuerdo necesario,
profundización nueva, variante con transferencia o duplicación prescindible.
Si Omar propone repetir, explica la evidencia con naturalidad: «Omar, esta
construcción ya está desarrollada en [archivo/sección]. Aquí falta justificar
este paso; voy a integrarlo allí y dejar una recuperación breve en el capítulo».
Nunca inventes esa objeción para parecer crítico. Una insistencia explícita en
repetir o separar cambia la decisión editorial y debe respetarse.

Detectar solapamiento debe producir una mejora concreta, no paralizar el encargo.
Integra o remite con contexto cuando la decisión sea rutinaria; si sustituir
todo un capítulo altera materialmente la intención, presenta la alternativa
y solicita esa elección. «Esto aparece antes» no cubre una laguna del pasaje actual.

## Escribir desde los fundamentos

Lee [criterio editorial y calibración](references/editorial.md) al redactar o
reescribir. Identifica qué pregunta abre el pasaje, qué prerrequisitos necesita
y qué capacidad nueva deja. Presenta pronto el marco general pertinente en
lenguaje accesible; haz tangible cada capa con un ejemplo que evolucione.

Cada transición explica qué dificultad queda y por qué el siguiente objeto,
representación o hipótesis permite resolverla. Establece universos, elementos,
igualdad, mapas, información que se conserva y supuestos antes de usarlos.
Da la idea de la prueba y justifica sus pasos esenciales. Define y desarrolla
los prerrequisitos que realmente sostienen el argumento; una remisión puede
complementar, pero no sustituir su contenido indispensable.

Escribe prosa conectada en español natural. La densidad consiste en aportar
estructura y razones por párrafo, no en comprimir la explicación. No impongas
rótulos de «ontología», «intuición» y «formalización», cuotas de páginas ni una
plantilla idéntica a todos los capítulos. No confundas rigor con maquinaria
innecesaria ni accesibilidad con ocultar la hipótesis decisiva.

Si una figura permite ver una relación o prueba que el texto deja difícil,
usa TikZ y lee [diseño y revisión de figuras](references/tikz.md). Integra la
figura con su explicación; no la añadas por cuota ni como adorno.

## Revisar el resultado que existe

Relee como un alumno con los prerrequisitos declarados y como un matemático
que busca una hipótesis falsa. Intenta reconstruir la solución usando solo lo
escrito. Busca conceptos sin explicar, cambios de objeto, razones ausentes,
casos frontera, contraejemplos y repeticiones. Comprueba la continuidad de
entrada y salida y repite el contraste de cobertura después de editar.
Corrige los defectos dentro del encargo; informa los que dependan de cambios
externos al alcance. La revisión adversarial puede hacerse en esta sesión;
una delegación no es requisito para cada texto.

Para LaTeX, usa el compilador **de la versión elegida**, inspecciona sus opciones
y recompila el documento afectado y las salidas dependientes pertinentes.
Revisa referencias, glifos y desbordamientos; renderiza y lee las páginas
modificadas, todas las figuras afectadas y sus transiciones. No recompiles una
edición antigua por un comando grabado en esta skill. Si no puedes compilar o
ver el resultado, conserva la fuente y declara esa verificación pendiente.

Cierra conforme a `AGENTS.md` y `.codex/README.md`: evidencia por requisito,
informe breve en el destino previsto, commits del encargo y publicación.
Entrega enlace al resultado, cambios esenciales y límites reales. No marques
un texto completo con una laguna conocida ni equipares compilación con comprensión.

## Frontera con las asíncronas

Esta skill gobierna apuntes y su exposición matemática. Si Omar pide diapositivas,
Beamer, guiones de locución o producción de vídeos, usa la skill disponible
`brainteasers-quant` para sus entregables y contratos audiovisuales. Si el encargo
incluye ambos, aplica cada contrato a su superficie. No traslades al libro sus
duraciones, número de páginas, punto rojo ni composición de diapositivas.
