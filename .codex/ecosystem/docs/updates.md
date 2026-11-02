# Actualizaciones de Constellation por dispositivo

El equipo mantiene una instalación para todos sus proyectos. Una inscripción
opcional comprueba cada hora el commit publicado en `main` del repositorio
canónico de Constellation. Primero obtiene sólo la referencia remota. Si han
cambiado la revisión, el perfil o el recibo de instalación, descarga el
snapshot publicado de esa revisión exacta y ejecuta la misma sincronización y
vinculación verificadas del alta inicial. El candidato nuevo confirma el
workspace contra su propio hash de distribución antes de reconocer esa revisión. Una pérdida de conexión conserva la
última versión utilizable. El próximo intervalo reintenta una migración
pendiente.

En un equipo POSIX donde ya exista una instalación verificada, usa la entrada
estable del dispositivo, la ruta canónica de OmarOS, el checkout fuente de
Constellation y la ruta real del ejecutable Codex. En este equipo la fuente está
en `~/.codex`. Aquí `--workspace-root` identifica la fuente cuyas skills se
excluyen del descubrimiento duplicado; el workspace operativo de proyectos sigue
en `~/GitHub` y se selecciona con `cli workspace --root ~/GitHub`.
El comando `plan` muestra las definiciones de launchd o systemd de usuario y los
comandos de activación.

```sh
~/.codex/constellation/run updates plan \
  --vault-root ~/OmarOS --workspace-root ~/.codex --codex /ruta/al/codex
```

Inspecciona el resultado de `plan` antes de elegir `enable`. La operación
`enable` escribe la configuración persistente del usuario. En macOS, launchd
puede cargarla en el siguiente inicio de sesión; los comandos de activación
mostrados permiten iniciarla ahora. En Linux, esos comandos habilitan el timer
en el servicio systemd del usuario. Para una instalación genérica, sustituye `--vault-root ...` por
`--general`. La política equivale a aceptar futuras revisiones del `main`
publicado del origen canónico. En equipos donde cada revisión necesita una
aprobación separada, utiliza la [sincronización por SHA](migrations.md).

La entrada estable verifica el paquete antes de ejecutar el temporizador.
Conserva la identidad de la última promoción confirmada en el estado privado
de la instalación. También comprueba si aparecen nuevas skills del paquete
en el checkout o cambian las preferencias de descubrimiento. Con la misma
revisión publicada, concilia esos cambios con la instalación local. El
temporizador usa la entrada estable del equipo y admite cambios de intérprete.
El mismo marcador recuerda las fuentes cuya deshabilitación confirmó el
cliente. Si vuelves a habilitar una de ellas, Codex puede eliminar su fila
`false`. El temporizador conserva esa decisión y detiene la conciliación antes
de escribir otras exclusiones. Para continuar, vuelve a deshabilitar la copia
local en el cliente, o retira la inscripción de ese workspace para mantener
su fuente activa. Si hay un marcador antiguo sin ese historial, revisa las
fuentes activas antes de reanudar la actualización automática.
Las comprobaciones sin cambios terminan silenciosamente.
El fallo de transporte o integridad y el código de salida están disponibles
en el supervisor de usuario. Usa `tick` con los argumentos del alta para
reproducir la comprobación en primer plano. Las definiciones con contenido
ajeno se conservan y se informa del conflicto. Para retirar la inscripción,
ejecuta la orden de desactivación mostrada y retira únicamente los archivos
de definición que siguen correspondiendo al plan de tu equipo.

Los procesos de trabajo nuevos usan la instalación compartida tras una
promoción satisfactoria. Cada supervisor requiere una sesión o servicio de
usuario activo y acceso normal al repositorio privado. Los equipos sin red
adoptan la revisión al volver a conectarse. Los chats abiertos conservan el
catálogo cargado por su cliente; comprueba eventos y confianza nativa después
de actualizar.
