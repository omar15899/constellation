# Migraciones de Constellation

## Fase adaptativa 1.2

La revisión mantiene el algoritmo común, sus pisos de riesgo, independencia y
hallazgos acumulados. Sustituye el máximo universal de tres rondas por continuidad
justificada y presupuesto temporal explícito. Las políticas de esquema 1 siguen
siendo legibles y se normalizan sin `max_rounds`; el esquema 2 rechaza ese campo.
Replanificar o cambiar de política conserva los mínimos de riesgo y cobertura,
incluidos los más estrictos del receptor. `review-budget` registra cada plazo y ampliación;
`review-start` recibe una razón y acción siguiente cuando la detección de ciclos
o falta de progreso las exige. No se inventa un presupuesto de tokens a partir
del contexto disponible. Consulta el
[contrato compartido](references/protocol.md#review-continuity-and-budget).

El hook pasa del comando de un caché versionado a
`CODEX_HOME/constellation/hook.py`. El instalador mantiene la entrada y el recibo
de esquema 3; el hook verifica la distribución bajo un lock compartido, mientras
el instalador usa el mismo lock en exclusiva. El
[contrato de instalación](README.md#instalar-y-actualizar) especifica rechazos,
actualización desde recibos anteriores y límites de recuperación.

La primera transición requiere reabrir los hilos que retengan el comando antiguo.
No se editan hashes de confianza: si la nueva definición requiere una aprobación
del cliente, se realiza mediante su interfaz nativa. La entrada estable evita
depender de la ruta de un caché retirado en actualizaciones posteriores, pero no
demuestra recarga de skills ni despacho exitoso por sí sola.

El experimento nativo se prerregistra separando baseline de un agente, delegación
nativa y Constellation, con controles de capacidad y recuperación. Su diseño y
estado están en [EVALUATION.md](EVALUATION.md). Las pruebas deterministas del
motor y del instalador no sustituyen esa comparación. No se atribuyen mejoras de
calidad, latencia o coste antes de obtener y analizar los resultados.

## Inventario histórico 1.1

Auditoría inicial: 2026-10-18, Codex CLI 0.163.0. Se examinó la infraestructura
de los 21 repositorios registrados, OmarOS, configuración nativa y distribución
Constellation. No se usaron conversaciones, secretos o contenido personal como
contexto. Los resultados históricos de 1.0 no certifican esta migración.

| Componente previo | Evidencia inicial | Decisión |
| --- | --- | --- |
| Cinco módulos del hub | Implementaciones de workflow, workspace, dispatch, review y agent policy | Consolidar en `ecosystem/runtime`; conservar entradas pequeñas compatibles |
| Revisión portable | Ya importaba el mismo algoritmo del hub | Mantener un algoritmo y una política compartida en el paquete |
| Registro Git + registro portable obligatorio | La skill de ingeniería exigía ambos ciclos | Eliminar la obligación ritual; elegir ciclo por sus garantías y objetivo |
| Skills globales, locales y plugins | Descubrimiento nativo real, carga progresiva documentada | Retener mecanismos nativos, sin copiarlas todas a Constellation |
| Diagnóstico del plugin | Filtraba sólo Constellation e ignoraba `warnings` | Ampliar el adaptador nativo con estados y superficie explícitos |
| Hooks del hub | Cuatro eventos; Stop confiado pero deshabilitado | Retirar definiciones duplicadas; un adaptador del plugin para contratos activos |
| Hooks del plugin | Cinco eventos confiados y habilitados; sólo veían contratos portables | Integrar selección explícita del contrato activo sin autoiniciar trabajo |
| OmarOS | Motor especializado y copia casi idéntica del algoritmo de revisión | Consumir revisión compartida; retener semántica de dominio y publicación independiente |
| 19 hijos nativos | Cuatro archivos `.codex`, sin copias de motores/agentes/hooks | Conservar dominio y protección contra proyección; reducir overrides redundantes cuando se verifica herencia |
| `.claude` | Infraestructura paralela con consumidores reales, incluidos validadores Git | Aislar por cliente; no borrar validadores de dominio que siguen ejecutándose |
| `ruflo` externo | Hooks rechazados por `_generated_by`; timeouts obsoletos y auto-memory | Diagnosticar incompatibilidad; conservar propiedad externa y no ejecutar automatismos |
| Caché y catálogo instalado | Caché 1.0 válido; catálogo con cinco `.DS_Store` adicionales | Tratar como derivados; actualización validada desde fuentes, preservando extras |
| Contexto y agentes locales | Override de contexto 1.000.000/900.000 en el hub y seis perfiles heredados | Retirar override y perfiles duplicados; conservar ocho perfiles especializados y límites nativos por modelo |
| Aprendizaje personalizado | Preferencias explícitas del usuario; sin ejemplos suficientes para un perfil definitivo | Perfil local provisional y calibración en la skill de enseñanza; no datos personales en el paquete |
| Continuidad y diario | Estado operativo existente, Git y mecanismos propios de OmarOS | Añadir checkpoints al almacén existente y una proyección curada con autorización exacta; sin otro motor ni base de datos |
| Código pequeño | Clasificación ordinaria Standard aunque el cambio fuera acotado | Permitir Quick justificado antes de la primera ronda cuando ambas políticas lo admitan; conservar Deep y pisos de riesgo |

El inventario inicial del app-server encontró 21 skills/18 habilitadas en el
hub, 18/18 en Sweeplab, 120/22 en OmarOS y 191/191 en ruflo. OmarOS conserva
cuatro skills locales habilitadas y 98 exclusiones deliberadas. El listado de
plugins tenía 24 instalados y 23 habilitados; no equivale al catálogo de skills
de un proceso nuevo ni al de esta sesión.

Un directorio vacío sin Git descubrió 18 skills habilitadas, incluidas las tres
de Constellation, y seis hooks (uno global y cinco del plugin), sin crear
archivos en el directorio. Esto prueba integración nativa sin scaffolding para
descubrimiento; las pruebas de ejecución se registran por separado.

## Actualización reversible

La fuente es este checkout. El builder genera un bundle con inventario explícito;
el instalador verifica la distribución anterior y conserva configuración ajena.
No se edita el caché como fuente ni se modifica confianza para hacer pasar una
prueba. Una distribución nueva se instala usando las operaciones nativas.

Los estados de tareas existentes conservan sus formatos y ubicación privada.
Los adaptadores públicos preservan las invocaciones habituales. Los cambios de
evidencia o política invalidan la revisión correspondiente; una actualización
no concede aprobación a trabajo anterior. La recuperación de un intento
interrumpido es explícita y nunca fabrica un check exitoso.

`task_progress` se crea al primer hito sustancial, sin migración masiva de tareas
anteriores. Mantiene UUID y cronología al replanificar. La política personal del
diario no se genera desde el registro de repositorios: sólo permite raíces y
aliases explícitos. El receptor OmarOS actualiza su bundle fijado para consumir
progreso y revisión; la nota y el dashboard se crean mediante su propio workflow.
Su recibo local no acredita publicación. Consulta [PROGRESS.md](PROGRESS.md).

El perfil de aprendizaje y las instrucciones locales de calibración se conservan
fuera del bundle y de Git. La base inicial es provisional, derivada de requisitos
explícitos; los futuros ejemplos pueden refinarla o corregirla. Los ensayos
sintéticos usan perfiles ficticios aislados y no añaden preferencias reales.
Investigación, aprendizaje e ingeniería se componen por intención sin crear
motores independientes o selectores persistentes.

El instalador admite inventarios anteriores verificados al añadir recursos del
paquete, preservando estado privado y configuración ajena. Las pruebas cubren
actualizaciones desde recibos de esquemas 1 y 2 en hogares temporales. Esa
compatibilidad no autoriza archivos desconocidos ni demuestra por sí sola que
la instalación personal haya sido actualizada.

La restauración consiste en desplegar una distribución anterior verificada y
restaurar exclusivamente los archivos de configuración modificados, con revisión
del estado de tareas que corresponda. No requiere reset de historia, borrar
trabajo, habilitar plugins desactivados ni conceder confianza a hooks.

## Validación

La matriz vigente y sus límites se describen en [EVALUATION.md](EVALUATION.md).
Las suites automatizadas prueban controles y rechazos en repositorios y remotos
temporales. La selección real de skills y la ejecución de agentes se evalúan
como experimentos separados: los fixtures deterministas no las sustituyen.
