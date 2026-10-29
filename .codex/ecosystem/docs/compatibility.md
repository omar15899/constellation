# Compatibilidad y evidencia

La estructura activa corresponde a `1.4.0-rc.1`: cuatro skills, ocho roles y 82
recursos en la distribución completa. Los destinos son `posix` y
`windows-claude`. Un inventario válido no demuestra ejecución, confianza nativa
ni calidad de respuestas.

## Plataformas y límites

| Ámbito | Estado y límite |
| --- | --- |
| macOS/Linux | Destino POSIX, Python 3.11+, cliente compatible y filesystem con promoción exclusiva soportada. |
| Claude en Windows nativo | Adaptación candidata sin WSL; la ejecución real permanece pendiente y el usuario la ha diferido. |
| Codex en Windows nativo | Fuera del destino Windows de esta entrega. |
| Confianza de hooks | Revisión del cliente; no la concede la instalación ni la conservación de rutas. |
| OmarOS | Adaptador activo con cuatro recursos verificados fijados en 1.2.0; conserva su propio contrato. |

La [guía Windows](windows.md) distingue instalación, pruebas aisladas de backend,
replays directos, eventos en un cliente real, Git y PowerShell. Los últimos
ámbitos no se deducen del resultado de un replay. El probe tampoco impone
confinamiento de red al ejecutable nativo ni verifica controles de cuenta.

## Baseline publicado

El registro del coordinador para [fd824929](https://github.com/omar15899/constellation/commit/fd824929a50ad8e2473988107ae0b129213c1be7) es anterior a la
eliminación final de formatos y documentos retirados. Estos son sus resultados
observados, no recuentos anticipados de la limpieza actual:

| Comprobación | Resultado del baseline | Límite |
| --- | --- | --- |
| Suite compuesta de fuentes | 508 casos: 476 ejecutados y 32 omisiones de host. | Las omisiones no acreditan sus plataformas. |
| Hub | 429 de 429. | Corresponde a ese snapshot. |
| Cinco exportaciones inglesas POSIX | 491 casos por variante; ejecutados: completa 459, coding 447, mathematics 448, quant-research 441, writter 449; omisiones: 32/44/43/50/42. | Las variantes reutilizan pruebas; no son casos independientes sumables. |
| Cinco exportaciones con destino Windows Claude | 35 casos por variante: 30 ejecutados y 5 omitidos. | Se probaron formato y empaquetado desde macOS, no las API de Windows. |
| Diez bundles | Inventario y modos inmutables; reubicación, reconstrucción y ZIP reproducible. | Integridad y reconstrucción, no calidad semántica. |
| Codex inglés en macOS | Catálogo CLI 0.165.0: cuatro skills y cinco hooks sin confianza concedida. | Consulta de un proceso nuevo; no acredita ejecución en todos los chats. |
| Claude inglés | Schema nativo estricto, instalación nueva/repetida y cambios de idioma conservaron datos y ajustes ajenos. | Pruebas aisladas; no aceptación Windows. |

No se hicieron solicitudes nuevas a modelos para ese trabajo de adaptación.
Las comprobaciones posteriores de la limpieza se registran en el workflow del
dueño y su traza de ejecución. Esta tabla no las sustituye ni inventa resultados.

## Alcance de la evidencia

Los ensayos previos de selección y calidad pertenecen a sus snapshots. Hubo tres
invocaciones esperadas de skill en cuatro positivos y dos controles negativos
proporcionales; el caso editorial no invocó su método. Una corrección editorial
posterior necesitó feedback autorizado y verificación independiente. Se conserva
como corrección guiada, no como éxito autónomo ni evaluación del candidato
Windows. [Evaluación](evaluation.md) explica cómo interpretar esos resultados.

Las capacidades dependen de versión, superficie y permisos. Modelo, esfuerzo y
límites efectivos los conserva el cliente. La telemetría no observada y los
controles de cuenta permanecen desconocidos. Cambiar fuentes o instalar un
paquete no prueba recarga de una sesión abierta.

El historial detallado permanece en revisiones Git. No se instalan informes
retirados ni se cargan formatos anteriores para reconstruir evidencia faltante.
