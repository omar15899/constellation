---
name: "coding"
description: "Implementar, depurar y refactorizar software con requisitos observables, pruebas y revisión independiente. Usar para encargos de ingeniería que cambien o diagnostiquen comportamiento; no para dudas triviales de sintaxis, redacción o teoría matemática por la mera presencia de código."
---

# Ingeniería de software

1. **Entiende el contrato.** Localiza las instrucciones, las entradas normales,
   los consumidores y las invariantes del proyecto. Define el resultado observable.
   Si corriges un fallo, reprodúcelo o fundamenta su causa antes de editar.
2. **Implementa para el dominio completo.** Reutiliza las estructuras existentes.
   Conserva interfaces y datos anteriores salvo cambios pedidos. Haz visible el
   recorrido de los datos con nombres del dominio y pasos claros. Cada abstracción
   debe resolver una necesidad concreta. Cuida los fallos parciales, los reintentos
   y la concurrencia cuando puedan alterar el resultado.
3. **Documenta y comprueba.** En Python usa Google Style para los comentarios y
   docstrings exigidos por la interfaz o la lógica. En otros lenguajes aplica
   la convención equivalente del proyecto. Ejecuta primero las comprobaciones
   existentes pertinentes. Añade pruebas cuando el usuario las pida, el proyecto las exija
   o quede un riesgo concreto sin cubrir.
4. **Entrega con evidencia.** Sigue el ciclo y la revisión exigidos por el proyecto.
   En una corrección local pequeña, una verificación enfocada basta si el proyecto
   lo permite. Comunica únicamente hitos, bloqueos y decisiones materiales durante
   la ejecución. Al terminar, resume el resultado, la evidencia y los límites.

Consulta el [flujo de ingeniería](references/workflow.md) para decisiones de
implementación, documentación, pruebas y revisión en cambios sustantivos. El
[protocolo común](../../ecosystem/references/protocol.md) define cómo reutilizar
un contrato activo, registrar evidencia y coordinar su publicación autorizada.

Si delegas, da alcance exclusivo, condiciones de aceptación y contexto. Usa el
catálogo nativo. Si el rol no está cargado, transmite su instrucción al agente
disponible con el modelo, esfuerzo y permisos heredados. Los roles de
[código](../../ecosystem/agents/coder.toml),
[diagnóstico](../../ecosystem/agents/researcher.toml),
[revisión](../../ecosystem/agents/reviewer.toml),
[seguridad](../../ecosystem/agents/security-reviewer.toml) y
[verificación](../../ecosystem/agents/verifier.toml) tienen sus propias
responsabilidades. Cada obligación matemática, empírica o editorial requiere
evidencia de su tipo.
