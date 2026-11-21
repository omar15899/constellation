# Contrato de captura local

El agente decide el significado y redacta. `learning.py` comprueba identidad,
rutas, precondiciones de edición y persistencia. El motor no determina si un
procedimiento financiero es correcto ni si una fuente respalda una afirmación.

## Preparar el contenido

La entrada es una síntesis curada de lo aportado, nunca el prompt, una
transcripción o un archivo de conversación. No hay búsqueda ni extracción de
conversaciones históricas. El agente busca antecedentes con Fast Finder y lee
los candidatos antes de elegir los enlaces. El área privada se consulta mediante
el propio motor porque Fast Finder respeta las exclusiones Git.

Cada tema representa una pregunta estable, no una jornada. `slug` es un nombre
ASCII snake_case y conserva su identidad aunque mejore `title`. Un mismo evento
puede tratar varios temas. Dos capturas distintas del día generan dos eventos y
un solo archivo diario. Revisar el mismo tema otro día genera otro evento sobre
la misma nota temática.

`body` contiene la explicación vigente completa: integra el contenido anterior
pertinente con lo nuevo y conserva las dudas o discrepancias no resueltas. Lee
primero la nota temática actual. No envíes solo un fragmento nuevo que haría
desaparecer el contexto de la entrada vigente. El motor señala la aportación más
reciente como entrada de lectura y conserva las anteriores en el mismo archivo
como historia. El diario nunca copia esas explicaciones completas.

«Completa» se refiere a la pregunta profesional privada que desarrolla esa
nota. Si una nota general o pública ya explica sus fundamentos, conserva esa
nota como canónica y enlázala desde la ampliación privada. No copies su cuerpo
para fabricar otra explicación canónica de la misma teoría.

`event_id` es un UUID y se decide antes de `prepare`. Si el cliente ofrece una
identidad estable del mensaje, puede derivarse mediante UUID5; si no, conserva
el UUID elegido con el recibo de la operación. Al reintentar utiliza ese UUID y
la misma entrada. No reutilices uno antiguo para una nueva captura ni cambies
el contenido para sortear un conflicto de identidad. Para corregir, usa otro
UUID y `correction_of` con la identidad de la captura corregida.

Este ejemplo es ficticio y describe el formato, no un procedimiento de ENGIE:

```json
{
  "event_id": "f042495e-258c-41f3-84f2-2d2af3a0dc28",
  "learned_on": "2026-10-26",
  "captured_at": "2026-10-26T18:15:00+00:00",
  "summary": "He distinguido los datos de prueba de los criterios de aceptación del pricer ficticio.",
  "topics": [
    {
      "slug": "onboarding_pricer_ficticio",
      "title": "Qué verificar al incorporar el pricer ficticio",
      "body": "Ejemplo ficticio. El relato distingue el juego de prueba de los criterios para aceptar su resultado. No se ha descrito quién aprueba el paso siguiente.",
      "provenance": [{"kind": "user", "reference": "Relato expresamente aportado en esta captura ficticia"}],
      "antecedents": [],
      "conditions": ["Solo describe el ejemplo ficticio recibido"],
      "examples": [],
      "questions": ["Falta identificar al responsable de aprobación"],
      "contradictions": []
    }
  ]
}
```

`learned_on` es obligatorio y admite una fecha ISO o `null`. `captured_at` lleva
zona horaria y conserva la primera captura. `created` y `updated` pertenecen a
los archivos y usan la fecha UTC real de creación o escritura, independiente de
`captured_at`; no demuestran cuándo ocurrió el aprendizaje. Una fecha anterior
se registra como tal sin alterar la fecha real de captura. Las fechas de
aprendizaje desconocidas se agrupan en `Daily/unknown.md`.

Cada atribución tiene `kind: user`, `source` o `ai_proposal`, y una referencia
comprensible. El agente diferencia dentro de `body` qué afirmación pertenece a
cada origen cuando se mezclan. `source` exige haber leído la fuente pertinente;
un título o un resultado de búsqueda no bastan. Una inferencia o propuesta IA
no adquiere autoridad por aparecer en una nota.

`antecedents` contiene rutas relativas existentes de `06_Knowledge_Base`. Una
referencia laboral autorizada puede describirse en la procedencia sin mover el
original ni leer otras fuentes por extensión. Las citas preservan restricciones.
Un procedimiento incompleto explica sus pasos conocidos y sus lagunas en
`questions`. `contradictions` identifica la afirmación, su fuente y qué entra en
conflicto. No se elimina la versión estable sin resolución respaldada.

## Ejecución

El motor requiere macOS o Linux, Git y el intérprete registrado del dispositivo
con PyYAML. Define `CONSTELLATION_CHECKOUT` con la ruta a tu copia de
Constellation y ejecuta los ejemplos desde OmarOS o uno de sus subdirectorios.
Desde otra carpeta, añade `--root RUTA` antes de la operación para seleccionar
el vault inscrito. El CLI central selecciona el recurso y el intérprete
registrado. La captura comprueba que la raíz y su directorio Git conservan
las identidades registradas antes de leer o crear archivos privados. Usa entrada
estándar o archivos temporales privados para los datos de la captura.
Si se reemplaza el checkout o se prepara otro equipo, actualiza mediante el
contrato común su registro y la identidad del sistema de archivos en
`profiles/projects.json` de la fuente central, después de verificar el nuevo
propietario Git. El mapa local de rutas del instalador solo localiza proyectos.
La captura privada valida su propia inscripción y las identidades de la raíz
y del directorio Git.

```sh
python3 "$CONSTELLATION_CHECKOUT/constellation.py" skill-run omaros engie-learning scripts/learning.py prepare < captura.json
```

`prepare` devuelve `status: prepared` y un objeto `plan` que fija los cambios y
las versiones esperadas. Si hay una escritura pendiente, se detiene sin confirmar
otra captura hasta que se resuelva su estado. Si reconoce un evento ya persistido, devuelve
`already_applied`: comprueba las rutas devueltas sin añadir otra captura ni
pasar ese resultado a `apply`. Conserva el JSON preparado fuera de rutas publicables y
pásalo íntegro a `apply`, que acepta el envoltorio con `plan`. Antes de aplicar,
declara las rutas relativas exactas de `paths` como asignaciones de un encargo
con `mode: "local"`. El contrato del encargo lleva rutas y objetivo operativo.
Conserva la síntesis en el plan privado. Usa el mismo ID de encargo al comprobar,
revisar y cerrar:

```sh
python3 "$CONSTELLATION_CHECKOUT/constellation.py" --engie-learning begin ID < encargo.json
```

Aplica el plan tras abrir el encargo:

```sh
python3 "$CONSTELLATION_CHECKOUT/constellation.py" skill-run omaros engie-learning scripts/learning.py apply < preparado.json
```

No sustituyas este recorrido por escrituras ad hoc. El agente puede leer el plan
para verificar los destinos y títulos antes de aplicarlo sin volver a pedir
confirmación sobre elecciones ya autorizadas. Una captura idéntica conserva su
identidad y no se añade de nuevo. Una entrada distinta con un UUID ya utilizado
debe tratarse como conflicto, no como un nuevo aprendizaje implícito.

Los límites locales son 1 MiB por captura o nota, 2 MiB para el plan aplicado y
32 MiB para el estado operativo privado. `prepare` comprueba que su plan puede
aplicarse dentro del límite. Una saturación produce un error observable, nunca
una confirmación parcial de éxito.

Las consultas son acotadas al área privada:

```sh
python3 "$CONSTELLATION_CHECKOUT/constellation.py" skill-run omaros engie-learning scripts/learning.py query --date 2026-10-26
python3 "$CONSTELLATION_CHECKOUT/constellation.py" skill-run omaros engie-learning scripts/learning.py query --date unknown
python3 "$CONSTELLATION_CHECKOUT/constellation.py" skill-run omaros engie-learning scripts/learning.py query --topic onboarding_pricer_ficticio
python3 "$CONSTELLATION_CHECKOUT/constellation.py" skill-run omaros engie-learning scripts/learning.py query "criterios de aceptación"
python3 "$CONSTELLATION_CHECKOUT/constellation.py" skill-run omaros engie-learning scripts/learning.py query --related 06_Knowledge_Base/Mathematics/Finance/ENGIE/README.md
```

El último ejemplo solo produce coincidencias si ese antecedente fue enlazado.
No debe añadirse una relación artificial para forzar un resultado. `--root`
solo selecciona el vault cuyo dueño e identidad constan en el registro central;
no autoriza una carpeta temporal ni otro checkout.
`query` devuelve rutas y metadatos, no la explicación completa. Lee después el
archivo temático y sigue su enlace «Revisión vigente». Si comunica `pending` o
`partial: true`, advierte que hay una captura incompleta y no presentes esos
resultados como un guardado completo.

## Corregir y recuperar

Una corrección es una captura nueva que referencia `correction_of`. El texto
anterior se conserva y se añade una corrección explícita que identifica su evento.
El agente explica qué cambia y por qué, y conserva las fechas originales del
evento corregido. Cambiar la fecha de aprendizaje exige conservar esa
procedencia: no se presenta una corrección de fecha como certeza retrospectiva.

Los archivos contienen zonas gestionadas y pueden conservar contenido manual.
No edites a mano los identificadores o marcadores que usa el motor. Ante una
edición concurrente, lee la versión actual, concilia el cambio y vuelve a
preparar la captura. No borres la edición ajena ni repitas ciegamente un plan
obsoleto.

```sh
python3 "$CONSTELLATION_CHECKOUT/constellation.py" skill-run omaros engie-learning scripts/learning.py status
python3 "$CONSTELLATION_CHECKOUT/constellation.py" skill-run omaros engie-learning scripts/learning.py recover
```

El estado operativo nuevo vive en `Private/.learning/capture/`. El motor
puede consultar los recibos que ya existen bajo `.git/omaros-learning` y respeta
su bloqueo. Si detecta una recuperación pendiente del formato anterior, termínala
con la versión anterior del motor en un entorno con acceso de escritura a esa
ruta. Para actualizar, deja que terminen las capturas anteriores y usa la misma
versión actual en todos los clientes del vault. Una versión anterior puede
ignorar una recuperación pendiente en la ubicación nueva.

Una operación interrumpida puede dejar varios archivos
en versiones distintas. La recuperación compara cada destino con las versiones
prevista y anterior. Una tercera versión exige conciliación, sin restauración
automática sobre ella. El bloqueo coordina escritores que lo respetan; un editor
externo puede escribir sin él. No equivale a una transacción universal del sistema
de archivos.

Cuando una tercera versión impida completar el plan y se decida abandonarlo,
`recover --abandon` conserva el journal en `Private/.learning/capture/recovery/` y deja
los archivos actuales disponibles para conciliar. Si hay un original desplazado
en un archivo `.swap` por una carrera de edición, rechaza el abandono hasta que
se concilien expresamente ambas versiones, conservándolas.
Devuelve `abandoned_partial` con `persisted: false`: no confirma una captura ni
deshace los cambios ya escritos. Después hace falta conciliación y una nueva
preparación. No uses esta opción como reintento ordinario.

Confirma el guardado después de un resultado persistido y de releer sus destinos.
Si falla la escritura o la verificación, comunica el estado concreto y los pasos
que faltan. Un plan preparado no es un guardado. Un archivo existente tampoco
prueba por sí solo que se hayan completado todos los cambios de una captura.

## Privacidad y mantenimiento

Los únicos destinos de nuevo conocimiento son `ENGIE/Private/Topics/*.md` y
`ENGIE/Private/Daily/`. La raíz completa es
`06_Knowledge_Base/Mathematics/Finance/ENGIE/Private/`. El motor exige exclusión
Git y rechaza archivos ya versionados. La palabra `Private` está además excluida
por la política del catálogo Quartz. Esas defensas no autorizan publicar, ni
garantizan el comportamiento de cualquier aplicación externa.

No copies resúmenes corporativos a trazas de ejecución, diarios personales,
memoria, informes compartidos o servicios externos. Los metadatos `publish` o
`classification` describen intención; no sustituyen los controles de destino.
Los originales laborales y las fuentes LaTeX conservan autoridad y ubicación.
Una ampliación propia vive en la nota privada y enlaza la representación o fuente
autorizada. Así sobrevive a la regeneración sin modificar el generador.

El encargo `--engie-learning` usa exclusivamente la raíz OmarOS inscrita,
`mode: "local"` y asignaciones para notas exactas de `Private/Topics/` y
`Private/Daily/`. Su ubicación fija es `Private/.learning/task-ledger/`. Es
parte del ciclo de revisión de Constellation y conserva solo objetivo
operativo, rutas, huellas y evidencia. Para comprobar y cerrar, usa
`--engie-learning check`, `--engie-learning review` y `--engie-learning finish`
con el mismo ID, tras releer los destinos. El recibo de `learning.py` da
evidencia de persistencia y la revisión independiente evalúa el contenido.
El ámbito privado se conserva para el encargo y su recibo.
Las consultas son de lectura y no completan una escritura pendiente de forma
implícita.

Las notas privadas contienen información única y necesitan una copia privada
autorizada para resistir la pérdida del disco. El estado de recuperación protege
operaciones concretas, no sustituye una copia de seguridad. Las consultas no
requieren un índice global, un daemon ni un modelo adicional. La captura habitual
usa búsqueda acotada, redacción de la sesión y una operación local.
