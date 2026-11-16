# Figuras que explican y se dejan comprobar

Usa TikZ cuando una figura revele la construcción, correspondencia, partición,
dependencia, masa o geometría que sostiene el argumento. Define antes qué debe
permitir ver: «cada objeto tiene exactamente dos descripciones» es verificable;
«hacer la página más vistosa» no justifica una figura.

## Integración en el libro

Inspecciona el preámbulo, las macros de figuras y los TikZ cercanos de la versión
vigente. Reutiliza paleta, tamaños y estilos del **manual**; no importes una
composición de Beamer ni sus reglas de duración. Conserva notación, nombres y
colores con un significado estable. Cita la figura en el punto donde haga falta
y escribe un pie que diga qué representa y qué permite concluir.

Diseña primero los objetos y las relaciones, después la geometría. Un árbol
muestra decisiones y hojas; una partición hace visible disjunción y cobertura;
una biyección indica ida y vuelta; un cociente distingue clases y representantes.
No dibujes conexiones adicionales porque completen una simetría agradable.
Si eliges un caso pequeño, identifica su tamaño y explica qué es generalizable.

## Ataques a cada figura

Comprueba su contenido con independencia de que compile:

- Cuenta nodos, hojas, clases y flechas; compara con el ejemplo. ¿Hay omisiones,
  duplicados, orientación errónea o una agrupación que cambia el objeto contado?
- Lee cada etiqueta y relación sin recurrir a tu recuerdo del diseño. ¿Se ve
  qué espacio contiene cada objeto? ¿Una flecha representa una función, una
  dependencia o un movimiento? ¿Dos trazos sugieren una igualdad que no existe?
- Comprueba cardinalidades, probabilidades, unidades, fronteras y leyendas
  pertinentes. Un dibujo simétrico no demuestra equiprobabilidad. Un área
  decorativa no representa una probabilidad salvo que se declare y respete.
- Revisa proporciones cuando tengan significado; identifica un esquema que
  no esté a escala. No permitas que el código visual contradiga la demostración.

En el render real del libro, busca etiquetas solapadas, trazos sobre texto,
flechas que terminan en el objeto equivocado, recortes, tipografía ilegible,
contraste insuficiente y referencias o pies separados de lo que explican.
Los colores no deben ser el único modo de distinguir elementos esenciales.
Revisa a tamaño de lectura y amplía para diagnosticar; una miniatura no acredita
legibilidad y una imagen enorme no corrige una etiqueta minúscula en el PDF.

## Compilar, renderizar, corregir

Usa el compilador del destino y su comando real. Si hace falta aislar un TikZ
para diagnosticar, conserva el preámbulo efectivo; revisa también su integración
final, donde cambian escala, márgenes y saltos. No declares revisión visual por
leer el código o el log.

Con Poppler, una vez localizado el PDF producido:

```sh
pdftoppm -f PAGINA -l PAGINA -scale-to 1800 -png RUTA_PDF PREFIJO_TEMPORAL
```

Sustituye esas variables por las rutas y páginas reales y abre las imágenes con
la herramienta de visualización disponible. Una herramienta PDF equivalente
sirve si produce imágenes legibles. Guarda diagnósticos temporales fuera del
vault; publica solo los entregables o evidencias exigidos por el encargo.

Corrige los defectos matemáticos y visuales y vuelve a compilar e inspeccionar.
Tras la última modificación, comprueba de nuevo todas las figuras afectadas,
sus pies y páginas vecinas. Si refluye el documento, usa las páginas actuales.
La evidencia identifica fuente, PDF vigente, página, qué se comprobó y qué se
corrigió; una huella es útil si ya existe un registro de revisión. No atribuyas
a la versión nueva una inspección de un PDF anterior.

Si falta una herramienta de compilación o visualización, explica el impedimento
concreto y deja esa comprobación pendiente. No sustituyas una revisión adversarial
por una puntuación estética ni la compilación por una declaración de perfección.
