# Codex y Constellation

`~/.codex` es el directorio de la aplicación Codex. En este equipo también
contiene el repositorio de Constellation, cuya fuente está en `.codex/`.
Compartir la raíz no convierte el estado de la aplicación en código del proyecto.

| Responsabilidad | Ubicación | Qué se mantiene aquí |
| --- | --- | --- |
| Aplicación Codex | `~/.codex/` | Configuración, sesiones, bases de datos y coordinación del cliente. Los gestiona Codex y permanecen locales. |
| Fuente de Constellation | `~/.codex/.codex/` | Métodos, motor, perfiles y pruebas que desarrollamos y versionamos. |
| Instalación de Constellation | `~/.codex/constellation/` | Lanzador, paquete verificado y recibos. Se actualiza mediante el instalador. |
| Conocimiento y operaciones personales | `~/OmarOS/` | Notas, proyectos, documentos y navegación del vault. |
| Proyectos de software | `~/GitHub/` | Código de los repositorios, con contratos e historias Git independientes. |

Para el trabajo cotidiano, abre el proyecto de OmarOS y usa la instalación
compartida. Para cambiar un método o el motor, trabaja en la fuente de
Constellation. Los archivos instalados y el estado del cliente tienen sus
propios mecanismos de actualización y recuperación.

- [Trabajar entre carpetas y usar el lanzador](.codex/README.md)
- [Mantener los métodos y el motor](.codex/AGENTS.md)
- [Entender las bases SQLite y sus archivos auxiliares](.codex/profiles/codex/layout.md#bases-de-datos)
- [Consultar el mapa completo del directorio](.codex/profiles/codex/layout.md)
- [Instalar el perfil en otro equipo](.codex/profiles/README.md)
- [Leer las instrucciones globales de Omar](AGENTS.md)

El Git de esta raíz publica en `main` de
[omar15899/constellation](https://github.com/omar15899/constellation).
La [allowlist](.gitignore) limita la publicación a la fuente y las instrucciones
mantenidas; excluye configuración, conversaciones, bases de datos, instalaciones
y recuperación local.
