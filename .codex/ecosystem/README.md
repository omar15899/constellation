# Constellation

Constellation coordina requisitos, evidencia, revisión y publicación sobre
Codex y Claude Code. Los clientes ejecutan modelos, herramientas y agentes;
cada proyecto conserva sus archivos, datos, permisos y dueño Git. Una sola
distribución reúne cuatro skills y ocho roles canónicos, con entradas nativas
para ambos clientes.

El coordinador parte del resultado pedido, consulta el catálogo de su sesión y
carga las capacidades pertinentes. Descubrir una herramienta no prueba acceso
ni ejecución; una capacidad ausente se comunica o se sustituye por una alternativa
comprobada. La [arquitectura](docs/architecture.md) explica estas responsabilidades
y la [evaluación](docs/evaluation.md) define cómo contrastarlas.

## Elegir el flujo

| Trabajo | Ejecución |
| --- | --- |
| Pregunta breve | Respuesta directa y comprobación pertinente. |
| Cambio en un repositorio | Un contrato del receptor, pruebas, revisión y publicación por su dueño Git. |
| Investigación o documento con evidencia persistida | Núcleo portable, aunque no haya repositorio ni publicación. |
| Trabajo mixto | Capacidades y dependencias según sus obligaciones; sin registrar dos veces la misma entrega. |

Cuando están disponibles y respetan las instrucciones del receptor, las skills
`constellation:coding`, `constellation:mathematics`, `constellation:quant-research`
y `constellation:writter` cubren ingeniería, argumentos matemáticos, investigación
sistemática y escritura sustantivas. Un diagnóstico de ingeniería sin editar
archivos o una demostración no trivial también requieren su método pertinente.
Las preguntas breves, la aritmética simple y las traducciones cortas no necesitan
ese flujo. En Codex se pueden invocar con `$constellation:nombre`; en Claude,
con `/constellation:nombre`. Nombrar una skill no carga sus instrucciones.

`UserPromptSubmit` aporta un recordatorio estático para consultar el catálogo,
aunque no haya contrato. No consulta ni clasifica el texto del prompt ni lo
almacena; tampoco inicia una tarea. Los controles de alcance y cierre siguen
actuando sobre contratos activos. La selección efectiva requiere observación,
no se acredita por la presencia del recordatorio. Los formatos y conectores
permanecen en sus proveedores; el módulo cuantitativo no activa órdenes reales.

Los [criterios de trabajo por responsabilidad](docs/architecture.md#criterios-de-trabajo-por-responsabilidad)
concretan la explicación didáctica, el diseño de código pedido y la investigación
adversarial. Sus [ensayos dirigidos](docs/evaluation.md#ensayos-dirigidos-de-las-instrucciones)
comprueban la aplicación del método; se distinguen de la selección automática.

## Estructura

| Ubicación en las fuentes | Responsabilidad |
| --- | --- |
| `.codex/skills/` | Cuerpo canónico de cada skill y sus referencias específicas. |
| `.codex/ecosystem/runtime/` | Workflow Git, coordinación, reparto, revisión y progreso compartidos. |
| `.codex/ecosystem/core.py`, `storage.py`, `cli.py` | Evidencia portable, persistencia local y entrada pública. |
| `.codex/ecosystem/manifests/` | Fuentes de los manifiestos nativos de plugins y hooks. |
| `.codex/ecosystem/agents/` | Ocho roles canónicos; el constructor proyecta el formato de Claude. |
| `.codex/ecosystem/references/` | Protocolo y fundamentos metodológicos usados por las skills. |
| `.codex/ecosystem/docs/` | Arquitectura, instalación, progreso, compatibilidad y evaluación mantenidas. |
| `.codex/ecosystem/tests/`, `evals/` | Pruebas de comportamiento y casos de evaluación. |
| `docs/history/`, `evals/results/`, dentro de `ecosystem/` | Informes y resultados históricos conservados sólo en las fuentes. |

Los módulos `build.py`, `install.py`, `native.py`, `claude.py` y los adaptadores de
hooks mantienen sus entradas públicas. En el paquete, `skills/` y los manifiestos
nativos se proyectan desde esas fuentes. Los dos archivos distribuidos de hooks
conservan sus rutas porque participan en su identidad nativa; no son copias
fuente adicionales. Mantener una ruta no conserva ni concede confianza: el
cliente puede exigir una nueva aprobación. Los archivos privados de ejecución
y configuración personal quedan fuera de la distribución.

## Instalar y actualizar

Se requiere Python 3.11+ y el cliente elegido; Git se usa para publicación.
El destino predeterminado conserva macOS/Linux. El candidato 1.4.0-rc.1 añade
el destino nativo de Claude en Windows, cuya aceptación real en Windows sigue
pendiente. Consulta [su guía](docs/windows.md); construir el paquete no acredita
esa ejecución. Para el destino POSIX, usa fuentes publicadas y un destino nuevo:

```sh
python3 .codex/ecosystem/build.py --output /tmp/constellation-1.4.0-rc.1 \
  --archive /tmp/constellation-1.4.0-rc.1.zip
shasum -a 256 /tmp/constellation-1.4.0-rc.1.zip
```

La edición inglesa se construye desde la misma fuente añadiendo `--language en`.
Traduce instrucciones, roles, guías, evaluaciones y las cadenas de presentación
del diario; conserva módulos, políticas, lógica y los instaladores. La edición
predeterminada sigue en español. Ambas usan el mismo identificador y versión:
instala una edición por cliente, sin activar dos copias. Las
reglas de `ecosystem/locales/README.md` en las fuentes describen su inventario y límites.

Copia el paquete por un canal autorizado y comprueba el hash. La
[guía de instalación](docs/migrations.md#instalar-y-actualizar) contiene los
comandos de ambos clientes, comprobación previa, actualización y recuperación.
No copies los directorios personales completos de Codex o Claude. Cada portátil
conserva sus cuentas, datos, conectores y políticas locales.

La reorganización 1.3.1 mantiene las interfaces nativas y separa las guías de la
evidencia histórica. Su aceptación exige verificar la actualización desde 1.3.0,
además de una instalación nueva. Consulta el
[estado observado](docs/compatibility.md); un número de versión no acredita
instalación, confianza ni ejecución. Abre sesiones nuevas después de actualizar.

## Trabajar y comprobar

En el hub, usa `.codex/ecosystem/cli.py git --session ID` o
`.codex/ecosystem/cli.py workspace --session ID`. Los lanzadores antiguos
de la raíz se han retirado; las sesiones abiertas deben cargar los cambios según
su cliente. En un paquete independiente:

```sh
python3 /ruta/al/paquete/ecosystem/cli.py git --root /ruta/proyecto --session ID begin
python3 /ruta/al/paquete/ecosystem/cli.py git --root /ruta/proyecto --session ID plan < contrato.json
```

En Claude, el ciclo usa `claude-<session_id>`; los autores y revisores conservan
sus IDs nativos. El [protocolo](references/protocol.md) distingue ciclos Git y
portable, comprobaciones, revisión y límites. El trabajo sustancial conserva
[progreso recuperable](docs/progress.md) en su almacén existente.

El [comando completo de diagnóstico de Codex](docs/migrations.md#diagnóstico-de-codex)
consulta un proceso nuevo del CLI; no representa automáticamente este chat.
Para Claude, `claude.py verify` comprueba la integridad de la instalación.
Comprueba después catálogo, confianza y eventos en el cliente real. La
[matriz de compatibilidad](docs/compatibility.md) separa esas evidencias de los
tests y de la calidad de las respuestas del modelo.
