# Publicación entre repositorios

Usa el [lanzador común](README.md#operar-desde-cualquier-carpeta) y conserva el
ID del chat. Selecciona la raíz de cada dueño: la fuente publica en `main`, el
hub de GitHub en `codex/workspace`, y los hijos y OmarOS en sus propios upstreams.

| Alcance | Argumentos del lanzador |
| --- | --- |
| Un dueño Git | `cli git --root RUTA --session ID OPERACION` |
| Dueños registrados en el hub | `cli workspace --root "$HOME/GitHub" --session ID OPERACION` |
| OmarOS y sus delegados | `vault --project-root "$HOME/OmarOS" --session ID OPERACION` |

El [manual del vault](ecosystem/vault/README.md) conserva sus formatos específicos,
renombres, cierre local de consultas y delegados externos. No uses una ruta del
vault para representar archivos de otro dueño. Las instrucciones de cada receptor
fijan sus permisos, datos y excepciones.

## Plan y comprobaciones

Para un dueño, ejecuta `begin` y declara `requirements` y `paths` mediante `plan`.
Para varios dueños de GitHub, `workspace plan` crea sus contratos y fija upstreams.
Las rutas son relativas al hub y las dependencias se declaran en el mismo objeto:

```sh
constellation_entry="${CODEX_HOME:-$HOME/.codex}/constellation/run"
"$constellation_entry" cli workspace --root "$HOME/GitHub" --session ID plan <<'JSON'
{
  "requirements": ["Ambos proyectos describen el mismo contrato de datos"],
  "paths": ["Shared/README.md", "PricingLab/README.md"],
  "depends_on": {"PricingLab": ["Shared"]}
}
JSON
"$constellation_entry" cli workspace --root "$HOME/GitHub" --session ID dispatch --capacity 4
"$constellation_entry" cli workspace --root "$HOME/GitHub" --session ID check --repo Shared -- git diff --check
"$constellation_entry" cli workspace --root "$HOME/GitHub" --session ID check --repo PricingLab -- git diff --check
```

`dispatch` propone paquetes; el coordinador asigna agentes nativos reales,
rutas exclusivas y capacidad disponible. Valida proveedores antes de consumidores.
Usa checks apropiados al comportamiento modificado. Un fallo exige evidencia
vigente; `check-resolve --repo RUTA` permite documentar una invocación equivocada
con reemplazo equivalente e independiente, sin borrar el intento original.
Consulta su esquema y límites en la ayuda y en el
[ejemplo del perfil](ecosystem/vault/README.md#un-ciclo-local-por-encargo).

`adopt_existing` justifica por ruta los cambios anteriores que el encargo incorpora;
`unrelated` conserva archivos nuevos ajenos fuera del commit. Declara bajas exactas
en `deletions`, como subconjunto de `paths`. Un plan nuevo no legitima cambios de
destino ni borra hallazgos pendientes; `extend_existing: true` amplía explícitamente
un contrato de workspace activo conservando su alcance.

## Revisión independiente

Aplica [REVIEW.md](../REVIEW.md) y cualquier obligación adicional del receptor.
Tras los checks, registra autores mediante `review-author --repo RUTA`, abre
`review-start --repo RUTA` y registra los informes sobre su token vigente.
Los payloads de autoría, informes, hallazgos, resolución y presupuesto son los del
[manual del perfil](ecosystem/vault/README.md#revisión-independiente); usa rutas
relativas al dueño seleccionado. Para un solo dueño, omite `--repo` y usa `cli git`.

`review-context` muestra cobertura, vigencia, presupuesto y pendientes.
Los hallazgos requieren resolución independiente; los cambios posteriores
requieren nueva evidencia. `review` recibe una clave por requisito exacto y un
texto concreto de evidencia. En el workspace, agrupa ese mapa por dueño:

```json
{
  "Shared": {"Ambos proyectos describen el mismo contrato de datos": "Contrato del proveedor comprobado."},
  "PricingLab": {"Ambos proyectos describen el mismo contrato de datos": "Consumo compatible comprobado."}
}
```

Entrega ese objeto a `cli workspace --root "$HOME/GitHub" --session ID review`
por stdin. La cobertura mecánica no sustituye la revisión real del resultado.

## Commit y recuperación

Publica solo rutas declaradas, en orden de dependencia. Si hay índice ajeno
disjunto, usa `--preserve-index`; un solapamiento exige resolver la autoría.

```sh
"$constellation_entry" cli workspace --root "$HOME/GitHub" --session ID commit --preserve-index -m 'Aclara el contrato de datos' Shared/README.md PricingLab/README.md
"$constellation_entry" cli workspace --root "$HOME/GitHub" --session ID finish
```

`commit` publica y comprueba el SHA remoto. `finish` revalida cada dueño y el
conjunto. Un proveedor sin archivos propios puede publicar su HEAD mediante
`publish --repo RUTA`. Las publicaciones en varios remotos son independientes:
si falla una, `status` conserva el progreso y permite reanudar el dueño pendiente.
No deshagas commits publicados ni reinicies contratos para ocultar el fallo.

Conserva índices ajenos y upstreams congelados. Los commits anteriores pendientes
también saldrán: comprueba su autorización. No uses stash, reset, clean, rebase,
amend o force-push para superar bloqueos. La recuperación del contrato Git usa
`cli git ... recover SHA_COMPLETO` después de una reparación autorizada; audita
el HEAD sin mover ramas, índices ni publicar. La recepción documental de OmarOS
y el diario personal mantienen sus políticas separadas de autorización.

La ayuda de cada operación es la referencia de argumentos vigente. Instalación,
confianza nativa, ejecución de hooks, revisión y publicación se verifican por
separado. El [progreso recuperable](ecosystem/docs/progress.md) conserva hitos
curados en el workflow existente, sin archivar conversaciones.
