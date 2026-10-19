# Campañas cuantitativas con evidencia reproducible

Usa este flujo para componer capacidades existentes. Adapta las etapas a la
pregunta económica y al contrato del receptor: una estrategia diaria de ETF,
una cartera de futuros y un problema de almacenamiento requieren datos,
contabilidad y ejecución distintos. La generalidad procede de contratos
extensibles y rechazos explícitos de casos no soportados.

## Descubrir antes de ejecutar

Lee las instrucciones del proyecto, su mapa de dependencias y las interfaces
vigentes. Distingue declarado, descubierto, disponible, ejecutado y verificado.
Un SDK, MCP o adaptador instalado no acredita acceso a una cuenta, licencia,
integración ni una llamada exitosa. Consulta documentación primaria actual
cuando una decisión dependa de capacidades externas cambiantes.

En un workspace con laboratorios separados, asigna responsabilidades de este
modo y confirma los nombres e interfaces locales:

| Resultado | Responsabilidad |
| --- | --- |
| Snapshot de datos y controles de admisibilidad | Laboratorio de datos |
| Hipótesis, candidatos, familia y validación | Laboratorio de research |
| Órdenes simuladas, fills y contabilidad causal | Motor de backtesting |
| Asignación, exposiciones y certificado de límites | Cartera y riesgo |
| Paper, conectores y reconciliación | Laboratorio de ejecución |
| Campaña, dependencias y estado persistente | Integración del receptor |
| Presentación y navegación por evidencia | Interfaz, sin recálculo financiero |

No introduzcas importaciones que inviertan sus tiers. La coordinación de agentes
usa capacidades nativas y un contrato por dueño Git; una entrega local conserva
el protocolo del receptor. Combinar disciplinas no exige duplicar el lifecycle.

## Contratar la pregunta y la búsqueda

Antes de examinar los resultados elegidos, registra hipótesis económica,
predicción refutable, baseline comparable, universo, periodo, frecuencia,
capital de referencia y mejora mínima neta. Fija criterios de rechazo,
particiones temporales, objetivo de selección, presupuesto y condiciones de
parada. Distingue el universo histórico del operable actualmente.

Identifica la familia de hipótesis y configuraciones probadas. Registra cada
intento antes de ejecutarlo, incluidos fallos, interrupciones y resultados
negativos; declara cómo se cuentan reintentos idénticos y cambios de parámetros.
Conserva tanto el denominador de pruebas múltiples como la evidencia completa
de retornos y selección. Aumentar un contador no recupera ensayos omitidos.
No reutilices un OOS final para escoger el siguiente ganador sin registrar que
se ha convertido en información de selección.

## Fijar los datos admisibles

Conserva proveedor, revisión, identidades de instrumentos, calendario, zona
horaria, unidades, monedas, corporate actions, ajustes, huecos y derechos de uso.
Distingue observación económica, publicación y recepción. Cuando no se conocen
los vintages o la disponibilidad histórica, informa la limitación y restringe
las conclusiones que dependan de ella. Un timestamp de mercado no demuestra que
esa versión fuese conocida en ese instante.

Comparte snapshots inmutables y caché del receptor entre candidatos; no hagas
descargas duplicadas por agente ni reconstruyas el almacén incidentalmente.
Valida exclusiones de cotización y constituyentes históricos si los necesita
la hipótesis. Comprueba coherencia de raw/adjusted y dividendos para evitar
doble contabilización. Un universo actual no proporciona por sí solo una
estimación histórica sin sesgo de supervivencia.

Separa consultas interactivas de adquisición masiva. Para pruebas offline usa
un transporte replay explícito y reloj fijo: omitir un token no garantiza que
el adaptador deje de consultar credenciales del entorno o hacer red. Los
manifiestos y errores no incluyen tokens ni respuestas privadas de cuentas.

## Evaluar causalidad, economía y selección

Especifica cuándo se conoce la señal, cuándo se envía la orden y a qué precios
puede ejecutarse. Ajusta normalización, selección de variables y parámetros sólo
con el tramo de entrenamiento pertinente. Usa separación temporal y walk-forward;
purga o embargo cuando el solapamiento de etiquetas/horizontes lo requiera.

Reproduce decisiones, órdenes, fills, posiciones y caja con el motor canónico
del receptor. Comprueba comisiones, spread, slippage, FX, financiación,
préstamo de cortos, restricciones de negociación y liquidación pertinentes.
Registra qué costes se cargaron y cuáles no se pudieron medir. Distingue
resultados diagnósticos vectorizados de replay causal auditado; hashes de
configuración o datos no equivalen a un audit root emitido por ese motor.

Consume el informe completo de promoción vigente del laboratorio, con la
familia adecuada, restricciones de motor y clase de ejecución. Comprueba que
sus inputs de costes, turnover, exposiciones y penalizaciones fueron realmente
suministrados. No reimplementes ni rebajes un gate para obtener una aprobación.
Si no existe política aplicable, declara una adecuada al experimento antes de
seleccionar, justifica las hipótesis estadísticas y conserva sus límites.

Evalúa sensibilidad a parámetros y costes, estabilidad temporal, regímenes,
drawdown, liquidez, participación y capacidad al capital previsto. Ni un Sharpe
alto ni un gate aprobado garantizan rentabilidad futura. Un bloqueo de datos,
evidencia familiar, costes o auditoría mantiene el resultado limitado.
Una estimación imprecisa o evidencia insuficiente no refuta por sí sola una
hipótesis económica; distingue resultado inconcluso de refutación según el
criterio fijado y conserva el significado de los veredictos del receptor.

## Automatizar una cadena comprobable

Usa el runner y persistencia del receptor. Antes de lanzar una campaña, mapea
cada etapa a una implementación disponible, su contrato de entrada/salida y
sus dependencias; una etapa requerida ausente bloquea la campaña. Si hace falta
desarrollar un adaptador, decláralo como implementación y verifícalo antes de
atribuirle resultados económicos.

La evidencia debe permitir reconstruir esta cadena semántica, usando los
nombres de los contratos locales en lugar de añadir otro esquema paralelo:

```text
hipótesis y familia → snapshot → candidato → backtest auditado
  → asignación y riesgo → validación → paper → reconciliación → interfaz
```

Para cada resultado conserva identidad de campaña/candidato/familia, estado,
entradas y hashes, revisión del código, configuración, semillas, referencias de
salida y motivo verificable de fallo o limitación. Una ejecución sin auditoría
del motor mantiene ese campo ausente; no lo rellena con un hash propio. La
promoción científica y la autorización operativa son decisiones distintas.

La repetición debe ser idempotente o crear un intento nuevo enlazado. Conserva
el estado tras interrupciones y no conviertas una salida parcial o timeout en
éxito. La política de retry distingue lecturas repetibles de órdenes con efectos
externos: una respuesta ambigua del broker requiere reconciliar antes de
reenviar, especialmente si no existe una garantía comprobada de idempotencia.

El pipeline de pruebas automatizado debe ejecutar comportamiento real con
perfiles explícitos y producir un informe máquina de checks, estados y fallos.
Un perfil que no ejecutó sus pruebas obligatorias no puede devolver aprobación.
Verifica los invariantes pertinentes:

- Replay idéntico reproduce decisiones, ledger y métricas con las tolerancias
  declaradas; modificar información futura no altera decisiones anteriores.
- Caja, posiciones y corporate actions se reconcilian; cambios en costes se
  reflejan en P&L y aprobación cuando corresponda.
- Datos obsoletos, fallos de transporte, etapas ausentes y familia incompleta
  conservan su causa y bloquean el resultado que depende de ellos.
- Interrumpir y reanudar preserva intentos y procedencia, sin duplicar efectos.
- Un perfil offline funciona sin credenciales y bloquea red; una integración
  con replay verifica los contratos entre motores y no se presenta como prueba
  de un proveedor o broker remoto.
- La interfaz refleja el estado del servidor, los límites y la procedencia;
  distingue datos de demostración de resultados y no calcula otra rentabilidad.

## De simulación a broker

Trata EODHD u otros proveedores y T212 u otros brokers como roles distintos.
Comprueba capacidades reales para cuenta, instrumentos, histórico, órdenes,
fills y modos; no presupongas que el broker ofrece el histórico de research.
Mantén separados replay local, paper simulado, entorno demo remoto y live.

Los controles de riesgo y liquidez necesitan artefactos verificables, no
booleanos sin origen. La reconciliación compara órdenes, fills, caja y posiciones
con evidencias de ambos lados; la mera existencia de un ledger no demuestra
esa comparación. Paper aprobado no activa real. Cualquier paso a órdenes reales
requiere autorización específica y los controles propios del receptor.

Entrega hipótesis, baseline, familia completa, resultado, evidencia reproducible
y límites pendientes. Distingue lo ejecutado de lo diseñado y los checks de
software de la validez económica. Los checkpoints curados usan el progreso
existente; no incorporan prompts, conversaciones ni datos restringidos.
