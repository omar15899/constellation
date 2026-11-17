# OmarOS

Raíz: `/Users/omarkhalil/OmarOS`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Elegir el destino

La función determina el dominio, no la longitud o el formalismo de una nota.

| Función | Dominio |
|---|---|
| Entrada pendiente | `00` inbox |
| Vida y reflexión | `01_Daily_Life` |
| Tareas y ejecución | `02_Tasks_and_Execution` |
| Trabajo | `03_Work` |
| Investigación abierta | `04_Research` |
| Proyectos | `05_Projects` |
| Conocimiento establecido | `06_Knowledge_Base` |
| IA y agentes | `07_AI_and_Agents` |
| Infraestructura | `08_Systems_and_Infrastructure` |
| Entradas raw | `09_Data_Sources` |
| Transformaciones | `10_Ingestion_and_Transformation` |
| Informes | `11_Documents_and_Reports` |
| Finanzas, salud, medios, lecturas y relaciones | Dominios `12` a `16`, respectivamente |
| Dashboards, plantillas, metadatos y gobierno | Dominios `17` a `20`, respectivamente |
| Adjuntos, staging y archivo | Dominios `90`, `95` y `99`, respectivamente |

Inspecciona los archivos pertinentes antes de elegir. Extiende uno existente
si la idea continúa su tema; crea otro si cumple una función o pregunta
independiente. `06_Knowledge_Base` exige
`<subdominio>/<area>/<archivo>.md`. Una derivación formal no es por ello
investigación abierta. Lecturas de papers van en
`15_Reading_and_Learning/Papers/`; reflexiones en `01_Daily_Life/Reflections/`.

Decide estructura, metadatos y enlaces antes de redactar, y verifica sus destinos.
No generes una nota, tarea o informe de conocimiento por una explicación pedida
en conversación. Una modificación no trivial deja una traza breve declarada en
`11_Documents_and_Reports/Execution_Traces/YYYY-MM-DD/`. Contiene objetivo,
cambios, evidencia y límites; nunca el prompt ni la conversación.

Una petición explícita de guardar aprendizaje profesional sobre ENGIE, pricing,
hedging u operativa activa `engie-learning`.
Busca antecedentes antes de escribir y conserva teoría general y fuentes en su
dominio. El conocimiento nuevo y sus síntesis diarias viven en
`06_Knowledge_Base/Mathematics/Finance/ENGIE/Private/`, con fechas de aprendizaje,
captura y actualización separadas. Ese prefijo queda excluido de Git, Quartz,
diarios personales y exportaciones por defecto. Guardar contenido corporativo
no autoriza publicarlo ni leer conversaciones, correos u otras fuentes privadas.
No se modifican proyecciones LaTeX para añadir aprendizajes. Las consultas que
solo piden explicar o localizar no escriben notas. No hace falta un hook nuevo
ni un servicio periódico: la captura ocurre en una sesión activa autorizada.
Una captura privada se registra y cierra localmente; sus rutas y contenidos quedan fuera de Git y del diario público.

## Metadatos, nombres y contenido

Las notas con contenido, fuera de fragmentos, llevan YAML: `title`, `note_type`,
`domain`, `subdomain`, `tags`, `status`, `created`, `updated`, `author`. Añade
`source`, `ai_generated`, `ai_reviewed`, prioridad y relaciones cuando proceda.
Respeta los enums de `19_Metadata_and_Schema/Status_Enums/enums.json`, los tipos
de `19_Metadata_and_Schema/Note_Types/note_types.json` y el esquema del área.
No inventes enums para cerrar una validación.

En `04_Research` y `06_Knowledge_Base` conserva `latex_pending: true` hasta
formalizar; no añadas ese campo a otros dominios. Markdown matemático usa
`$...$` y `$$...$$`. Fechas ISO y nombres temáticos descriptivos ASCII
snake_case. Conserva nombres existentes de proyectos externos y su normativa.
Un renombre archivístico del flujo conserva exactamente los bytes y declara
ambos extremos; no sirve para ocultar una baja o reescritura.

En investigación cuantitativa, OmarOS recibe conocimiento y documentación.
El laboratorio dueño realiza la simulación y conserva los datos y sus
pruebas. Una conclusión con evidencia insuficiente queda en HOLD con las
obligaciones pendientes. Investigar, simular, hacer paper trading y emitir
órdenes reales tienen alcances distintos. Pasar a cada fase requiere la
autorización correspondiente; una comprobación de investigación nunca activa
órdenes como efecto lateral.

`writter` guía la redacción y `teach-from-first-principles` el aprendizaje que
requiere reconstrucción o práctica; `mathematics` cubre las demostraciones. Establece
objetos, estructuras, hipótesis y cuantificadores; distingue una función de su
valor, un proceso de una trayectoria y un operador de su matriz. Introduce
formalismo con su significado y justifica los pasos esenciales. Un ejemplo
confirma el mecanismo; una prueba explica la conclusión. Para LaTeX, lee el
capítulo, preámbulo, macros y bibliografía, integra el estilo y compila.

Cuando sea útil calibrar una explicación, consulta el pasaje pertinente de
`06_Knowledge_Base/Mathematics/Finance/Matematicas_Financieras.MD` o de
`06_Knowledge_Base/Mathematics/Functional_Analysis/vectores_coordenadas_y_dual_pairing.md`.
La primera referencia desarrolla configuraciones, observables, información y
ley; la segunda, el emparejamiento y su representación en una base. Son ejemplos
del vault, no prerrequisitos de toda respuesta ni autorización para guardar
preferencias nuevas. Si un material falta, usa el método disponible y declara
el límite cuando afecte al encargo.

Para documentación de QuantOS, lee `05_Projects/QuantOS/Documentation/index.md`,
`ai_reading_order.md` y `current_vs_target.md`, además de la doctrina pertinente
y el código actual del laboratorio dueño. Conserva la distinción entre
implementado, parcial, declarado y contradictorio. Cubre la pregunta, el contenido
matemático, su realización, invariantes, fallos protegidos y pendientes, evidencia
existente, extensiones y referencias; integra esas funciones en la estructura
del capítulo sin repetir lo que ya es canónico. Enlaza código y fuentes reales,
actualiza los índices afectados dentro del alcance y no inventes ejecución de tests.
Una consulta no autoriza crear un capítulo, modificar la doctrina ni publicar.

Los métodos propios del vault viven en `Constellation/skills/omaros/`:
`fast-finder`, `engie-learning`, `brainteasers-quant` y
`brainteasers-quant-notes` conservan sus recursos y alcances específicos.
Las automatizaciones conectadas se mantienen aparte de la selección de skills;
su presencia no autoriza ejecutarlas ni demuestra que estén activas.

## Recuperación, privacidad y preservación

`fast-finder` es la entrada mantenida de
búsqueda. Sus límites parciales no justifican conclusiones exhaustivas. Los raw,
el archivo, salud y relaciones requieren alcance pertinente; conversaciones,
logs y estados privados no son contexto incidental. Las asíncronas y el manual
de Brainteasers conservan sus skills y contratos propios.

No publiques transcripciones, archivos o manifests de conversación, estados de
sincronización ni logs de daemons sin que Omar nombre datos exactos y destino.
No leas secretos ni actives Memories, feedback, telemetría u OTel. Tampoco
instales o reactives plugins y skills globales por rutina. El perfil versionado
no prueba la configuración efectiva, confianza de hooks ni controles de cuenta.

Cada raíz Git externa mantiene su propio encargo; una
ruta del vault no puede representar un archivo externo. Preserva cambios e
índices ajenos, incluidos los generados por daemons. No alteres historias,
confianza o permisos para superar una puerta.
