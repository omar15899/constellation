---
name: "scholar"
description: "Adapta la explicación ontológica de Constellation al trabajo de OmarOS: utiliza las referencias de enseñanza del vault y decide cómo integrar una explicación en conversación, Markdown o LaTeX."
---

# Scholar

Aplica el criterio editorial de `constellation:writter` a las explicaciones de
OmarOS. El encargo determina la profundidad. En una explicación sustancial,
la [prueba de lectura](references/reader_test.md) ayuda a detectar si se puede
reconstruir el paso decisivo. Para una demostración o derivación sustancial,
usa también `constellation:mathematics`.

Las referencias de calibración pertenecen al vault. Resuelve estas rutas respecto
a la raíz del proyecto OmarOS seleccionado. Cuando la explicación necesite
calibración, lee el pasaje que responda a la dificultad concreta.

- `06_Knowledge_Base/Mathematics/Finance/Matematicas_Financieras.MD` muestra cómo construir el objeto financiero a partir de configuraciones, observables, información y ley. Su pregunta rectora y su mapa maestro orientan la secuencia.
- `06_Knowledge_Base/Mathematics/Functional_Analysis/vectores_coordenadas_y_dual_pairing.md` muestra qué expresa el emparejamiento y qué cambia con una base. Sirve para valorar si el lector distingue el objeto de cada representación que introduce el desarrollo.

El lector debe poder identificar la pregunta, construir sus objetos y seguir el
efecto de cada hipótesis, elección o cambio de representación. Escoge un ejemplo
que conserve su significado al añadir estructura. Justifica el paso difícil
mediante una prueba, un cálculo o una fuente según lo que la afirmación requiera.
Si falta el vault o alguno de sus materiales, aplica el método disponible e
indica el límite cuando afecte al resultado solicitado.

Una explicación pedida en conversación se entrega en conversación. Cuando Omar
pida guardarla, lee las reglas y el destino del vault. Extiende la nota existente
si el argumento continúa allí. La función de la nota decide su ubicación: el
conocimiento establecido vive en el dominio 06, una pregunta de investigación
abierta en 04 y la lectura de un artículo en 15. Para Markdown utiliza los
metadatos y enlaces del dominio, y las convenciones matemáticas del vault. Para
LaTeX inspecciona la entrada real, las macros y los capítulos vecinos; integra y
compila las fuentes correspondientes. Para las sesiones asíncronas o el manual
de Brainteasers, utiliza la especialización respectiva del mismo paquete.
