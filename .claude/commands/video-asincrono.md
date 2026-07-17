---
name: video-asincrono
description: Producir un subvídeo asíncrono del curso Brainteasers Quant — presentación Hespérides + guion teleprompter + justificación pedagógica, con validación por fases. Trigger cuando Omar dice "prepara el vídeo N de la sesión S", "hazme un vídeo sobre X", "graba la píldora de Y" o similar.
---

# /video-asincrono

Punto de entrada para producir un vídeo asíncrono del Máster (curso
Brainteasers Quant). Petición típica en lenguaje natural:

> Prepara el vídeo 3 de la sesión 2. Unos seis minutos. Quiero explicar por
> qué la convexidad cambia el problema. Usa la sección 4 de los apuntes. La
> demostración la haré a mano.

## Pipeline

1. Leer **`~/GitHub/brainteasers-asincronas/CLAUDE.md`** (contrato del repo)
   y `_sistema/convenciones.md`. Son autoritativos; este comando solo enruta.
2. Seguir la "Secuencia por vídeo" de ese CLAUDE.md: syllabus → apuntes →
   `nuevo_video.sh` → diseño conjunto slides+guion → build → render →
   inspección visual página a página → `validar.py` hasta OK.
3. Entregar las tres rutas (PDF, guion, justificación) y commitear el vídeo
   en el repo del vault.

## Dónde vive cada cosa

- Sistema: `~/GitHub/brainteasers-asincronas` (repo privado con remoto).
- Vídeos producidos: `~/OmarOS/05_Projects/Brainteasers_Quant/asincronas/`.
- Fuentes del curso: `~/OmarOS/05_Projects/Brainteasers_Quant/` (solo lectura).

## Guardarraíles

- No tocar QuantOS ni el resto del vault; perímetro `adjacent`.
- No sobrescribir vídeos con `estado: aprobado` (→ `versions/vNN`).
- No entregar sin inspección visual del PDF renderizado ni con `validar.py`
  en fallo.

## Aliases

`/video`, `/pildora`.
