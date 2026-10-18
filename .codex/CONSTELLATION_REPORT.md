# Constellation 1.1: consolidación y verificación

Fecha: 2026-10-18. El encargo «Constellation 2.0» se implementa como actualización
incremental 1.1. Codex conserva la ejecución nativa; Constellation concentra
coordinación, evidencia, revisión y publicación. Aprendizaje personalizable y
progreso persistente utilizan las capacidades y los almacenes existentes.
Este informe fija implementación y pruebas. Los workflows y el diario de OmarOS
conservan las revisiones, publicaciones y siguientes hitos del cierre.

## Auditoría y responsabilidades

El inventario contiene 21 registros en GitHub: hub, 19 hijos nativos y ruflo
externo. OmarOS es otro dueño Git. Al iniciar había un plugin 1.0 y una migración
1.1 sin publicar. Se continuó ese trabajo autorizado, preservando cambios e
índices ajenos. Conversaciones, credenciales y logs privados no son entregables.

| Responsabilidad | Autoridad |
| --- | --- |
| Modelos, herramientas, agentes, sesiones, permisos y descubrimiento | Codex y las capacidades expuestas por cada cliente |
| Coordinación, reparto, revisión y publicación Git | `.codex/ecosystem/runtime/`, con adaptadores pequeños |
| Selección y composición de skills | Modelo y metadatos nativos, sin clasificador paralelo |
| Evidencia matemática/editorial persistente | Núcleo portable cuando el objetivo requiere esas garantías |
| Dominio, datos y pruebas | Cada proyecto; adaptador especializado de OmarOS |
| Personalización y continuidad | Perfil local privado; estado operativo existente y diario curado |

Los cinco motores del hub tienen una implementación compartida distribuible.
OmarOS consume recursos fijados por hash y conserva privacidad, metadatos,
renombrados, delegados y publicación propia. Sus copias vendorizadas son
artefactos derivados. Claude y sus validadores utilizados permanecen; ruflo no
se modificó. No se introdujo otro runtime de agentes ni base de datos.

Se retiraron 19 TOML que repetían el límite 64 y el TOML del hub que imponía
contexto 1.000.000/900.000. `config/read` resolvió 64 en cada hijo; no se probó
saturación. Los 19 AGENTS pasan de 49.655 a 37.262 bytes conservando sus prefijos
de dominio; 18 PROJECT corrigen referencias. Se eliminaron seis perfiles
heredados, conservando ocho especializados. Los marcadores contra proyección
Claude siguen teniendo consumidor. Las entradas de las tres skills bajan de
11.692 bytes en la migración recibida a 9.355; HEAD tenía 9.421. Sus descripciones
no cambiaron; las referencias extensas se consultan por necesidad.

## Comportamiento y garantías

Investigación, aprendizaje e ingeniería se componen por intención y prioridades
explícitas. Una explicación breve no abre un contrato; una corrección local
pequeña usa comprobación enfocada. Investigación distingue hipótesis, pruebas,
observaciones y aproximaciones. Agentes y hashes no demuestran teoremas,
convergencia ni validez económica.

La revisión mantiene Quick=1, Standard=3 y Deep=3 de corrección más 2 de seguridad,
por archivo y foco, con tres rondas máximas. Código acotado de bajo riesgo puede
usar Quick con justificación anterior a la primera ronda cuando la política lo
permita. Queda ligada al snapshot; cambios la invalidan. No reduce Deep,
mínimos retenidos ni restricciones receptoras.

Se corrigieron registros anidados que desactivaban revisión, rebajas indebidas
de políticas, mínimos receptores ignorados, atribución incorrecta de commits
recibidos al sincronizar y discrepancias entre constructor y validador. OmarOS
reparó actualización de locks, cierre obsoleto al cambiar destino, escrituras
con sincronización bloqueada y reintentos de checkpoints. Su CI incorpora los
dos JSON canónicos que necesitan las pruebas del receptor. Las reparaciones
relevantes tienen regresiones y verificación independiente.

El plugin 1.1 está instalado. El inventario final contiene 57 recursos; SHA-256
de `bundle.json`: `9bf1541317829e0294e3a3fd992d37339d9694f9c6bcdbfe85a9b73dfab8ce78`.
Se verificaron tres exclusiones de fuentes sin nuevas escrituras, configuración
global intacta y cinco hooks nativos habilitados y confiados. Los hooks del hub
se retiraron. El plugin observa contratos activos: no inicia tareas, no hace
fetch por prompt ni publica. El guard de patches no intercepta cualquier
escritura shell/MCP; los commits manuales fuera del workflow no adquieren sus
garantías de revisión.

La sesión abierta conservó una ruta de `SubagentStop` 1.0 retirada durante la
actualización y produjo `Errno 2`. Procesos nuevos ejecutaron correctamente los
hooks 1.1. Abre una sesión nueva tras actualizar; no se reconstruyó la caché
antigua ni se alteró confianza para ocultar esta limitación del cliente.

Se conserva acceso completo/aprobación `never` previamente autorizado. No se
cambiaron permisos, confianza, modelo predeterminado, Memories, feedback ni
telemetría. La configuración local no acredita controles de cuenta.

La primera CI remota detectó una matriz antigua Python 3.9 y la ausencia de
configuración personal en el runner. La matriz del flujo Git pasa a 3.11/3.13;
una configuración temporal explícita permite comprobar herencia y coherencia
sin depender del equipo del usuario. Su nombre identifica que es una fixture,
no una prueba de ejecución de 64 agentes. La reproducción del fallo y los
controles positivos y negativos se verificaron independientemente. Los cuatro
jobs portables originales pasaron en Linux/macOS con Python 3.11/3.13.

## Aprendizaje, investigación y continuidad

`~/.codex/learning/PROFILE.md` es provisional, persistente, editable y privado.
La enseñanza distingue feedback reutilizable intencional de correcciones
puntuales, conserva procedencia y alcance, admite preferencias contextuales y
permite retirarlas. Los ejemplos futuros pueden refinarla; no se afirma un
perfil definitivo ni reentrenamiento. El perfil no forma parte de skills genéricas.

Ocho casos sintéticos pasaron 23 comprobaciones: feedback positivo/negativo,
prioridad actual, contexto, razonamiento propio, eliminación y recuperación en
agentes nuevos. Se observó adaptación del orden expositivo, sin demostrar
causalidad exclusiva o eficacia pedagógica. La revisión independiente contrastó
los artefactos y sus hashes. Las fixtures no se convirtieron en preferencias reales.

Dos procesos nativos nuevos, Astra Ultra y Sol 6.1 Ultra, recuperaron el mismo
perfil real sin modificar los archivos vigilados. Las ventanas efectivas fueron
258.400 y 475.000 tokens. La revisión detectó en Sol un salto de diferenciabilidad
puntual a campo global sin hipótesis adicional; Astra no presentó ese hallazgo.
Portabilidad y lectura del perfil no garantizan corrección matemática.

Los checkpoints guardan objetivos, estado, decisiones, hallazgos, evidencia,
pendientes y siguientes pasos en JSON Git o SQLite existentes. Sobreviven a
replanificaciones y permiten recuperar trabajo sin OmarOS. UUID, identidad de
hitos y revisiones evitan duplicaciones y actualizaciones obsoletas.

La sincronización exige raíz canónica y alias exactos autorizados en
`~/.codex/progress-journal.json`, destino fijado y checkpoint personal. Registrar
proyectos no autoriza exportaciones; fuentes desconocidas o restringidas quedan
excluidas. OmarOS recibe síntesis y referencias, preserva texto manual y recupera
escrituras interrumpidas. `RECEIVED_LOCAL` no significa publicación remota.
El receptor mantiene `17_Dashboards/Constellation.md` y una nota por tarea;
perfiles personales y logs no se copian allí. El agente selecciona los hitos
relevantes, sin un daemon adicional. Conocimiento científico y preferencias
pedagógicas siguen siendo contenidos distintos.

La guía cuantitativa reutiliza los laboratorios existentes. EODHD se investigó
con fuentes oficiales y 62 pruebas offline de adaptadores. No se verificaron
derechos de cuenta, cobertura real ni datos point-in-time; no se hicieron
llamadas pagadas ni órdenes. Un backtest rentable todavía exige causalidad,
costes, control de selección múltiple, OOS y justificación económica.

## Evidencia reproducible

Baseline Git: `86ef3bdb1b5551b50d7f48dac8a7a9a6002576f8`; Codex CLI 0.163.0.
Con Python 3.11 pasaron **281 pruebas del flujo Git** en 357,649 s y **239 del
paquete** en 351,191 s. Estas últimas incluyen construir y ejecutar las cuatro
distribuciones: full/coding/mathematics/writter, 239 casos cada una con 1/10/9/8
omisiones explícitas. Inventarios y bundles permanecieron intactos. No son casos
únicos adicionales. También pasan 30 pruebas de seguridad de proyección.

La matriz encontró tres fixtures que suponían coding en distribuciones que no
lo incluían. Se corrigieron tres líneas de pruebas y se repitió la matriz entera.
El runtime y las instrucciones del ensayo nativo permanecieron byte a byte
idénticos en el bundle final; su única diferencia era `test_core.py`.

| Ensayo | Resultado y alcance |
| --- | --- |
| Corrección Python, plugin 1.0 | Artefacto correcto, 10/10 oracle; 180,047 s sin cierre, 3 subagentes y 26 comandos |
| Misma tarea, plugin 1.1 | Completada en 52,814 s; 0 subagentes, 6 comandos, 10/10 oracle y 2 pruebas propias |
| Verificación independiente Python | 6.560 contrastes por artefacto; mismo harness/modelo, caché distinta |
| Investigación numérica | Oracle exhaustivo, 19 pruebas, 16 mallas, tres revisiones y verificación de reparaciones; no prueba general de convergencia |
| Varios repositorios | Ensayo temporal: proveedor publicado, rechazo del consumidor y reintento sin commit extra; índices parcialmente staged preservados |
| Recuperación y OmarOS | Interrupciones, historia monotónica, autorización, destino y recibos: 29 pruebas de progreso y 57 del loader; cierre integrado registrado en su propio workflow |
| Proyecto mínimo | Descubrimiento sin scaffolding y Git standalone sin leer fuentes del hub |
| Selección | Diez casos con catálogos iguales: nueve inequívocos pertinentes; alternativa ausente ambigua, conservada como tal |
| Integraciones | Lectura web oficial comprobada; ningún navegador gráfico disponible en las superficies ensayadas |

El ensayo candidato observó `UserPromptSubmit`, `PreToolUse` y `Stop` nativos
completados, con 95/95/96 ms. La duración de tarea incluye arranque/cierre del
app-server, no es latencia pura del modelo. La comparación muestra menor
sobrecarga en esa muestra, sin estimar fiabilidad general ni ventaja causal de
velocidad, tokens o calidad. Los fallos y resultados históricos se conservan.

Reproducción principal desde la raíz:

```sh
python3 -B -m unittest discover -s .codex/tests -q
python3 -B -m unittest discover -s .codex/ecosystem/tests -q
python3 -B .codex/ecosystem/validate.py
```

La evidencia experimental reducida permanece local en el directorio Git privado,
bajo `constellation/evidence/01a14c66-0820-7403-aec3-cdb9448c9619/`; no incluye
transcripciones. La evaluación versionada distingue casos ejecutados de futuros
escenarios de regresión.

## Operación y cierre

Describe el objetivo; el catálogo de la sesión orienta las capacidades. Un
proyecto nuevo aporta contexto y validación propios; necesita registro sólo
para coordinación entre repositorios. No copies motores ni perfiles. Consulta
[README](ecosystem/README.md), [PROGRESS](ecosystem/PROGRESS.md) y
[QUANT_RESEARCH](QUANT_RESEARCH.md).

Al reanudar, lee el contrato y `progress-show`; no reinicies rondas para ocultar
fallos. Los workflows conservan evidencia vigente, destino congelado y cierre
remoto por dueño Git; el diario muestra hitos y pendientes. Este texto no
certifica publicación por anticipado. Tras actualizar Codex, comprueba esquema,
descubrimiento, hooks y casos reales; retira mecanismos propios cuando una
capacidad nativa suficiente los reemplace.
