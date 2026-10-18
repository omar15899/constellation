# Constellation 1.2: proveedor de la alineación de OmarOS

Esta entrega publica la fuente del runtime 1.2 y sus dependencias de
instalación para que OmarOS pueda fijar un commit remoto que contenga
realmente sus recursos. La instalación local ya disponía de un bundle íntegro
de 59 archivos, pero el HEAD remoto todavía correspondía a 1.1.

## Alcance y preservación

Se integran 35 archivos de preparación preexistente: 25 fuentes del bundle
y diez archivos de contratos, regresiones Git y CI. Esa preparación se conserva
mediante adopción explícita por ruta. Su autoría histórica no se ha podido
determinar a partir de las trazas curadas disponibles; no se atribuye a UUIDs
de tareas ni a los agentes que la inspeccionan. El coordinador responde de la
integración actual y de someter el diff completo a revisión independiente.

Se corrige además la referencia de ingeniería que aún imponía tres rondas y
se aclara en EVALUATION que el arnés nativo y su informe siguen siendo trabajo
local independiente. Sus siete archivos se conservan fuera de esta publicación.
No se ejecuta la serie nativa ni se afirma mejora medida de calidad o latencia.

## Comportamiento de la entrega

La revisión conserva independencia, cuotas por archivo y foco, hallazgos,
historial y mínimos acumulados. Sustituye el límite universal de rondas por
admisión con presupuesto explícito y decisiones concretas de continuación.
La ausencia de plazo se informa como desconocida; un plazo agotado bloquea
nuevas versiones sin borrar la evidencia vigente. Los adaptadores Git,
workspace y portable transmiten la misma semántica.

La entrada estable de hooks valida la instalación y sus inventarios bajo
el lock compartido con el instalador. Conserva propiedad de archivos y
rollback. Esta publicación no modifica la confianza nativa del usuario ni
configuración global de capacidades.

## Evidencia y procedencia

La validación usa una copia temporal formada únicamente por HEAD y las rutas
declaradas, con su propio Git y tres fuentes contractuales existentes en HEAD
para resolver enlaces. No contiene los siete archivos de evaluación pendientes.
Pasan las 301 pruebas Git en 532,416 segundos y las 262 portable en 648,373
segundos, con Python 3.12. Las pruebas de comandos nativos requieren que
`python3` resuelva Python 3.11 o posterior; se antepone el entorno designado al
PATH de las pruebas sin modificar la configuración global.

La primera ejecución Git pasó 300 casos y falló el de perfiles porque la
preparación temporal no tenía repositorio Git. Corregida la fixture, pasan
ambas pruebas de perfiles y la suite Git completa; se conserva el fallo en el
historial de checks. No se ha corregido el producto para satisfacer ese error
de preparación. La comprobación final verifica que el código vivo sigue
coincidiendo con la copia probada.

Dos construcciones producen idéntico bundle de 59 recursos, verificado por
su validador oficial. SHA-256 de bundle.json:
`d0b61edb7c0a89f080c3265938ccd6feaccfd09e78441958d17f08bb3f04ab34`.
Frente al paquete 1.2 instalado sólo difieren EVALUATION y la referencia de
ingeniería corregidas; los cuatro recursos de ejecución que consume OmarOS
mantienen exactamente sus bytes y modos.

El cierre comprueba el SHA remoto y el consumidor contrasta los 59 blobs y
modos contra su árbol antes de fijarlo como procedencia. Un hash de bundle
por sí solo no demuestra publicación. La revisión Deep del diff completo
queda registrada en el contrato del proveedor.
