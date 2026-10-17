---
name: "mathematics"
description: "Investigate mathematics and mathematical physics, solve substantive mathematical problems, and construct or audit proofs with explicit hypotheses and independent scrutiny. Use for research, derivations, counterexamples and proof obligations, not trivial arithmetic or routine software engineering."
---

# Mathematics

Establece qué se quiere demostrar, calcular o refutar antes de elegir una técnica.
Trabaja con rigor de MSc/PhD cuando el problema lo requiera; adapta la exposición
al usuario. Introduce cada fórmula en prosa y explica qué permite concluir.

Antes de que sostengan un argumento, fija objetos, espacios, tipos, hipótesis,
cuantificadores y objetivo. Aplica la [ontología compartida](../../ecosystem/references/ontology.md):
separa objetos de representaciones, explicita mapas y estructuras preservadas,
y comprueba invariantes. Una biyección no establece equivalencia geométrica;
una expresión en coordenadas no proporciona coordenadas globales. Consulta los
[ejemplos ontológicos](../../ecosystem/references/ontology-examples.md) cuando
esa distinción determine la validez del razonamiento.

Para investigación, problemas difíciles o auditoría de pruebas, lee el
[flujo matemático](references/workflow.md). Distribuye vías matemáticamente
distintas entre agentes cuando aporte valor: sus primeras tentativas deben ser
independientes, sin ver las otras. Busca contraejemplos, casos degenerados e
hipótesis insuficientes. La revisión independiente examina los pasos esenciales,
sus dominios y las hipótesis de cada teorema; el consenso no es una prueba.

Consulta fuentes primarias y sus enunciados exactos cuando el argumento dependa
de resultados externos. Usa cálculo simbólico, experimentos numéricos o sistemas
formales cuando resuelvan una incertidumbre concreta; conserva entradas y
condiciones reproducibles. Los resultados numéricos no sustituyen una prueba.

Cada entrega significativa debe relacionar requisitos, artefactos, evidencia,
autores reales y revisión independiente mediante el
[protocolo nativo](../../ecosystem/references/protocol.md), cuyo motor requiere
Python 3.11+. Aplica el perfil `mathematics` por entregable; combina `coding` o
`writter` donde el resultado también lo necesite. Ajusta el esfuerzo a la
dificultad: una cuenta básica no necesita un proceso de investigación. Para una
entrega sustantiva en conversación, materializa solo un artefacto intencional si
la puerta necesita archivos, nunca una transcripción. El motor admite trabajo
sin Git; no crees un repositorio artificial.

Distingue prueba informal revisada, prueba formal ejecutada, evidencia
experimental, resultado condicional, refutación y cuestión abierta. Una
obligación esencial pendiente impide declarar `proved`. Entrega resultados
parciales honestos con la obligación pendiente y la evidencia necesaria para
reanudar. La puerta comprueba trazabilidad y vigencia, no verdad matemática.
