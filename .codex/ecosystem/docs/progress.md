# Progreso recuperable y diario personal

El coordinador mantiene checkpoints curados para trabajo sustancial: objetivo,
estado actual, resultados, decisiones, hallazgos, evidencia, problemas abiertos
y siguientes pasos. Los registra al cambiar algo importante, antes de un handoff
o cierre y al retomar el trabajo. Una corrección pequeña no necesita otro ciclo.
La relevancia la decide el agente; el runtime valida estructura, identidad y
vigencia, no clasifica por sí solo el valor intelectual de un resultado.

## Tres responsabilidades

El estado operativo permanece en el almacén existente: JSON privado de Git o
SQLite del motor portable. `task_progress` pertenece a la tarea y sobrevive a
la replanificación. El historial fuente sigue en Git. OmarOS recibe una síntesis
legible y referencias; no sustituye el estado fuente ni copia conversaciones,
comandos, logs o resultados brutos. El conocimiento científico reutilizable se
conserva mediante las notas de dominio y el flujo propios de OmarOS, con enlaces
desde el diario; no hay otro sistema de conocimiento.

Una tarea recibe un UUID al guardar su primer checkpoint. Un nuevo encargo tiene
otro UUID aunque reutilice sesión. Los hitos tienen identidad y fecha estables:
repetir ID y contenido es idempotente; reutilizar el ID con otro contenido falla.
Una corrección se registra como otro hito, conservando la cronología. La narrativa
no aprueba checks, revisiones, publicaciones ni resultados científicos.

## Guardar primero en el origen

Desde un proyecto Git, usa el workflow receptor; desde el hub, añade `--repo` a
los comandos de `workspace.py`. Primero consulta:

```sh
python3 .codex/workspace.py progress-show --repo .
```

Devuelve `task_progress`, `expected_task_start` y `revision`. La primera
actualización usa el inicio observado y revisión cero, sin `task_uid`:

```json
{
  "expected_task_start": "INICIO_DEVUELTO_POR_PROGRESS_SHOW",
  "expected_revision": 0,
  "source_alias": "personal-project",
  "checkpoint": {
    "id": "first-result",
    "summary": "Primer resultado comprobado y siguiente decision",
    "visibility": "unknown",
    "snapshot": {
      "objectives": ["Resultado que debe conseguirse"],
      "current": "Estado y limites actuales",
      "completed": ["Trabajo efectivamente realizado"],
      "decisions": ["Decision y motivo"],
      "findings": ["Hallazgo con su alcance epistemico"],
      "verification": ["Comprobacion ejecutada y resultado"],
      "unresolved": ["Problema que permanece abierto"],
      "next_steps": ["Siguiente accion concreta"],
      "references": []
    }
  }
}
```

Envía ese objeto por stdin a `progress-update`. `source_alias` es opcional en el
primer checkpoint e inmutable después; debe coincidir con la autorización de
exportación cuando exista. En actualizaciones posteriores usa `task_uid` y la
revisión actual, sin `expected_task_start` ni `source_alias`. El reintento exacto
del primer checkpoint perdido conserva los hitos posteriores y no crea otro UUID.

Los campos son síntesis de texto plano, no bloques ejecutables, transclusiones o
URLs incrustadas. Las referencias usan objetos `{kind, label, value}` con tipos
`repository`, `commit`, `experiment` o `documentation`. Usa referencias precisas
al repositorio, revisión, resultado o documentación; no incluyas URLs con
credenciales, parámetros secretos ni rutas de conversaciones. Los límites de
formato no son un detector universal de secretos: la curación responsable sigue
siendo necesaria.

En el motor portable se usan las mismas operaciones `progress-show`,
`progress-update`, `progress-export` y `progress-ack` con `session_id`, `task_id`
y `agent_id`. Update y ack conservan `expected_revision` **global del motor** y
el replay mediante `request_id`; no usan `expected_task_start`. Consulta el
[protocolo](../references/protocol.md) para el contrato portable. No abras un segundo
contrato Git o portable para registrar el progreso del primero.

## Autorizar una síntesis personal

La política es local al usuario, en `$CODEX_HOME/progress-journal.json`
(predeterminado `~/.codex/progress-journal.json`). Un `--policy` explícito sirve
para otra configuración autorizada o para fixtures aislados; nunca se elige a
partir del contenido de un checkpoint. Ejemplo ilustrativo:

```json
{
  "schema_version": 1,
  "target": {"root": "/ruta/absoluta/al/vault"},
  "sources": [
    {"root": "/ruta/absoluta/al/proyecto", "alias": "personal-project", "visibility": "personal"}
  ]
}
```

Se exige coincidencia exacta de raíz canónica y alias. Registrar un repositorio
como `native` no autoriza exportarlo; el permiso del padre tampoco se hereda por
un repositorio anidado. Una fuente desconocida o `restricted` queda excluida.
Además, el checkpoint más reciente debe declararse `personal` tras revisar su
contenido; los hitos anteriores no personales nunca se exportan. No deduzcas esa
clasificación del nombre del proyecto, del proveedor de datos o de su remoto.

El perfil de aprendizaje personal y sus ejemplos no se exportan automáticamente
al diario. Un hito puede informar de su mantenimiento sin copiar su contenido.
No se envían datos corporativos o restringidos al vault personal. Añadir una
fuente requiere autorización personal explícita para ese alcance; no copies todo
el registro de proyectos a la política.

## Entregar mediante el receptor OmarOS

Después de guardar el checkpoint, prepara la proyección:

```sh
python3 .codex/workspace.py progress-export --repo . --task-uid UUID
```

El resultado contiene `envelope`. Esta operación **no escribe en OmarOS**.
Conserva o transmite al receptor únicamente ese objeto curado, no el resultado
completo de `status`. El envelope fija UUID, historia personal, contenido, ruta
de nota y destino. Los hashes detectan cambios; no autentican al emisor.

Con el Python y la sesión del workflow de OmarOS, consulta `journal-paths
--source-root RUTA_CANONICA` pasando el envelope por stdin. Declara las dos rutas
devueltas en el plan del receptor, conservando un contrato activo si existe.
Después ejecuta `journal-import --source-root RUTA_CANONICA` con el mismo objeto.
La política se revalida en el receptor. La nota se ancla al día de creación bajo
`11_Documents_and_Reports/Execution_Traces/`; el índice humano es
`17_Dashboards/Constellation.md`.

El receptor valida propiedad Git, destino congelado, alcance y metadatos. Rechaza
regresiones de historia, sustitución de hitos, enlaces simbólicos, notas ajenas y
ediciones del segmento gestionado. El texto manual posterior al segmento se
conserva. No precrees el dashboard con un placeholder: deja que el receptor cree
el primer documento gestionado. Coordina centralmente escritores y publicación
del dashboard compartido; el bloqueo serializa importaciones, no crea una
transacción distribuida entre todos los proyectos.

La recepción prepara una intención recuperable en el directorio privado de Git
antes de cambiar nota o dashboard. Si se interrumpe, reenvía **el mismo envelope**
antes de otro hito. Los temporales permanecen en ese directorio privado. La
sustitución atómica exige que vault y estado Git estén en el mismo filesystem;
un fallo conserva el checkpoint fuente y no usa una escritura insegura alternativa.

`journal-import` devuelve un recibo `RECEIVED_LOCAL`. En el origen, envíalo a
`progress-ack` como `{task_uid, expected_revision, receipt}`. La política y el
envelope actuales se recomputan: un recibo antiguo, de otra nota o de otro destino
no confirma el checkpoint actual. La publicación remota sigue pasando por los
checks, revisión, commit y finish propios de OmarOS; el recibo local no la afirma.
El indicador de cierre procede del workflow vigente, no de una frase narrativa,
y tampoco convierte una hipótesis en un resultado demostrado.

## Recuperar sin el vault

`progress-show` permite continuar aunque OmarOS o su remoto estén indisponibles.
Lee los últimos resultados y pendientes, comprueba la evidencia que haya podido
cambiar y guarda el siguiente checkpoint cuando corresponda. La pérdida de una
respuesta se recupera por identidad/replay, no reiniciando el encargo ni borrando
rondas. Un fallo de entrega no borra progreso local. Reintenta el envío al
siguiente hito o reanudación, y comunica cualquier limitación que siga abierta.
