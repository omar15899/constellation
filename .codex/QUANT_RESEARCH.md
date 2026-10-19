# Investigación cuantitativa con capacidades existentes

Constellation coordina objetivos, dependencias y evidencia; los laboratorios
conservan datos, cálculos y validación. Aplica [RESEARCH.md](RESEARCH.md), el
[mapa QuantOS](../QUANTOS.md) y el
[contrato de promoción](../.claude/contracts/promotion_gate.md). Esta guía no
instala proveedores, autoriza operaciones reales ni declara una estrategia válida.

La skill portable [quant-research](skills/quant-research/SKILL.md) conserva la
metodología independiente de los nombres de los proyectos. Su
[workflow](skills/quant-research/references/workflow.md) define búsqueda completa,
admisibilidad temporal, validación y checks de campaña. Esta guía aporta el mapa
local y los límites concretos; tener la skill instalada no acredita la ejecución
de las etapas ni una conexión de datos o broker.

## Elegir el recorrido

Parte de una hipótesis económica refutable, universo y periodo definidos,
baseline comparable y mejora mínima neta. Declara antes de seleccionar resultados
la familia de intentos, criterios de rechazo y particiones temporales. Compón
investigación, implementación y explicación según la petición; no impongas una
lección ni un despliegue multiagente a cada consulta.

| Responsabilidad | Reutilizar y verificar |
| --- | --- |
| Datos | [MarketDataLab](../MarketDataLab/AGENTS.md): adaptadores EODHD, transporte inyectado, replay y almacén compartido. |
| Experimentos | [ResearchLab](../ResearchLab/AGENTS.md): hipótesis, configuraciones, walk-forward e informes de promoción. |
| Ejecución simulada y contabilidad | [BacktestLab](../BacktestLab/AGENTS.md): kernel causal y evidencia de reproducción. |
| Asignación y riesgo | [PortfolioLab](../PortfolioLab/AGENTS.md) y [RiskLab](../RiskLab/AGENTS.md): composición, exposiciones, límites y estrés. |
| Ejecución | [ExecutionLab](../ExecutionLab/AGENTS.md): propuestas y controles; usar simulación o paper dentro del alcance autorizado. |
| Integración e interfaz | [StrategyOrchestrationLab](../StrategyOrchestrationLab/AGENTS.md) compone los contratos y conserva el estado de campaña; [Helix](../tradinginterface/AGENTS.md) consume sus artefactos por API, sin recalcular resultados financieros. |

Comprueba las interfaces actuales de cada dueño Git antes de componerlas. Estos
componentes no acreditan por sí solos una cadena integrada de investigación a
órdenes. Por ejemplo, `run_pretrade()` en
[ExecutionLab](../ExecutionLab/packages/quant_exec_pretrade/src/quant_exec_pretrade/runner.py)
recibe `risk_ok` y `liquidity_ok` del llamador: hay que demostrar su procedencia.
Conserva los tiers y declara dependencias entre repositorios; no dupliques motores.

El contrato de una campaña debe poder enlazar hipótesis/familia, snapshot,
candidato, replay auditado, validación, asignación/riesgo y paper/reconciliación.
Un `fingerprint` identifica entradas o configuración; sólo el motor canónico
puede aportar su auditoría. Las etapas requeridas ausentes y los checks sin
ejecutar bloquean el resultado dependiente. Es posible mostrar resultados
parciales con su estado, pero no presentar una cadena incompleta como aprobada.

## Datos admisibles y reproducibles

Registra fuente, revisión, identidades y cambios de ticker, calendario/zona
horaria, fechas de observación, publicación y recepción, ajustes, huecos,
licencia y hashes del dataset. Una fecha contable no es una fecha de publicación;
un histórico descargado hoy no demuestra qué información estaba disponible ayer.
Usa snapshots autorizados y el almacén existente para repetir experimentos sin
peticiones innecesarias. No reconstruyas ni borres el almacén compartido.

Separa el universo históricamente disponible del operable hoy. Incluye excluidas,
altas, bajas y constituyentes históricos cuando la pregunta lo requiera; informa
la cobertura que falte y no etiquetes como libre de supervivencia una selección
basada en la lista actual. Valida precios, monedas, unidades y corporate actions.
Elige una convención consistente: añadir dividendos a retornos que ya incorporan
su ajuste los contabiliza dos veces.

El código actual de MarketDataLab ofrece
[`EodhdAdapter`](../MarketDataLab/packages/quant_market/src/quant_market/adapters/eodhd.py)
para EOD, intraday y ticks;
[`EodhdCorporateAdapter`](../MarketDataLab/packages/quant_market/src/quant_market/adapters/eodhd_corporate.py)
para dividendos/splits, y
[`EodhdReferenceAdapter`](../MarketDataLab/packages/quant_market/src/quant_market/adapters/eodhd_reference.py)
para referencias. `fetch_exchange_symbols()` no expone `delisted`; en los
adaptadores inspeccionados no hay integración de fundamentals con vintages/as-of
ni de constituyentes históricos. La admisibilidad de una barra EOD histórica se
fija a las 23:59:59 UTC de su fecha; intradía usa el cierre del intervalo. Esas
convenciones no demuestran cuándo estuvieron disponibles sus revisiones.

Para pruebas sin red inyecta
[`ReplayTransport.from_files/from_text`](../MarketDataLab/packages/quant_market/src/quant_market/adapters/transport.py)
y un reloj fijo. `build_gateway(..., replay=True)` también selecciona replay.
En cambio, [`build_gateway(..., api_token=None)`](../MarketDataLab/packages/quant_market/src/quant_market/service/factory.py)
puede consultar la variable del token: `None` no es una prohibición de red.

## EODHD: descubierto frente a ejecutado

Fuentes oficiales consultadas el **18-10-2026**; no se verificaron derechos de una
cuenta ni se hicieron llamadas a endpoints de datos durante esta auditoría.

- [EOD](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes):
  OHLC raw, cierre ajustado por splits/dividendos y volumen por splits. El
  proveedor recalcula el historial ajustado; conserva la versión usada y no
  confundas una serie revisada con una reconstrucción point-in-time.
- [Excluidas](https://eodhd.com/financial-apis/delisted-stock-companies-data-2) y
  [constituyentes históricos](https://eodhd.com/financial-apis-blog/sp-500-historical-constituents-data):
  cobertura condicionada por fechas y omisiones reconocidas. Comprueba símbolos
  y profundidad efectiva antes de definir el experimento; catálogo no equivale
  a completitud histórica.
- [Fundamentals](https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds)
  incluye fechas contables y de filing; la documentación revisada no establece
  un contrato general de vintages/as-of. No atribuyas esa garantía al proveedor.
- [MCP oficial](https://github.com/EodHistoricalData/EODHD-MCP-Server) y
  [biblioteca Python](https://github.com/EodHistoricalData/EODHD-APIs-Python-Financial-Library)
  existen. Ninguna herramienta EODHD apareció en el catálogo efectivo de esta
  auditoría; no se instalaron ni ejecutaron estas interfaces. El adaptador local
  no requiere el SDK. El MCP tampoco es enteramente de lectura:
  [PRAAMS](https://raw.githubusercontent.com/EodHistoricalData/EODHD-MCP-Server/main/app/tools/get_mp_praams_report_equity_by_ticker.py)
  genera informes/correo y declara `readOnlyHint=False`; enviar correo requiere
  autorización explícita.
- [Licencia personal/comercial](https://eodhd.com/financial-apis/commercial-vs-personal-license-use)
  y [condiciones](https://eodhd.com/financial-apis/terms-conditions): comprueba
  derechos de uso, conservación y redistribución para cada destino. MIT del
  SDK/MCP licencia software, no datos. Las cuotas locales no acreditan derechos
  ni límites efectivos de una cuenta.

Evidencia técnica disponible: en MarketDataLab
`56359e7896e5df7ca427cc455af64da62b1ec435`, los seis módulos EODHD pasaron
**62 pruebas offline** el 18-10-2026, con Python 3.14.6 y pytest 9.1.0.
Reproducción desde ese repositorio, sin instalar dependencias:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
.venv/bin/python -m pytest -q -p no:cacheprovider \
packages/quant_market/tests/test_eodhd*.py
```

Esto comprueba los adaptadores y fixtures; no acredita cobertura del proveedor,
licencia, calidad de todos los datos ni rentabilidad de una estrategia.

## Del experimento al veredicto

1. Fija información admisible y retardo de ejecución. Ajusta transformaciones y
   parámetros sólo con datos anteriores a cada decisión; aplica walk-forward,
   purga/embargo cuando el horizonte lo exija y un OOS final reservado. En el
   [LTR actual](../ResearchLab/research_algorithms/learning_to_rank_cross_sectional/src/ltr_cross_sectional/config.py)
   `execution_lag_bars` vale cero por defecto: justifica o modifica ese supuesto.
2. Reproduce posiciones, fills, caja y corporate actions en BacktestLab.
   Verifica costes efectivamente cargados: comisiones, spread/slippage, FX,
   financiación, préstamo de cortos y liquidación. El
   [adaptador LTR](../ResearchLab/research_algorithms/learning_to_rank_cross_sectional/src/ltr_cross_sectional/backtest/adapter.py)
   advierte que su ruta auditada no cobra préstamo de cortos. Un audit root
   demuestra procedencia; no corrige supuestos económicos o timestamps erróneos.
3. Conserva toda la búsqueda: candidatos fallidos, retornos, dispersión de
   Sharpes y denominador `m`. Consume el informe completo de
   [`build_promotion_report()`](../ResearchLab/research_algorithms/learning_to_rank_cross_sectional/src/ltr_cross_sectional/promotion/report.py)
   y el contrato vigente: FDR, bootstrap, Sharpe, DSR, PBO, Reality Check y
   objetivo robusto. `--n-trials-total` o su autodetección no recuperan la
   evidencia familiar omitida por un `--glob` selectivo. No rebajes umbrales
   ni reinicies el contador al cambiar de agente, modelo o sesión.
4. Examina estabilidad, sensibilidad a costes y supuestos, periodos/regímenes,
   exposiciones, drawdown, liquidez, participación y capacidad al tamaño previsto.
   Separa exploración, validación OOS y paper; un backtest rentable o un gate
   estadístico aprobado no autoriza órdenes reales.
5. Publica el veredicto y `run_class` con baseline, familia, código/datos,
   configuración, semillas, pruebas, límites y criterio de revisión. Los
   hallazgos sustanciales pasan al [diario de progreso](ecosystem/PROGRESS.md)
   y a OmarOS sólo dentro de las raíces personales autorizadas. Mantén fuera
   datos corporativos/restringidos, credenciales y material sin derechos de
   redistribución; conserva referencias a las fuentes en lugar de copiarlas.

La auditoría técnica del 18-10-2026 de los demás laboratorios fue estática; no
ejecutó una investigación económica completa ni validó su integración de extremo a extremo.
Una conclusión bloqueada por datos, costes o evidencia familiar permanece
limitada o pendiente, aunque la infraestructura pase sus pruebas.

## Campañas y pruebas automatizadas

El ejecutor de campañas pertenece a StrategyOrchestrationLab, con su contrato en
[RESEARCH_PIPELINE.md](../StrategyOrchestrationLab/docs/RESEARCH_PIPELINE.md).
Desde ese repositorio, con su entorno preparado:

```sh
.venv/bin/python -m strategy_orchestration_lab validate configs/research_campaign.yaml
.venv/bin/python -m strategy_orchestration_lab run configs/research_campaign.yaml --output-root outputs/research_campaigns --workspace-root ..
.venv/bin/python -m strategy_orchestration_lab status CAMPAIGN_ID --output-root outputs/research_campaigns
.venv/bin/python -m strategy_orchestration_lab verify CAMPAIGN_ID --output-root outputs/research_campaigns
.venv/bin/python -m strategy_orchestration_lab resume configs/research_campaign.yaml --output-root outputs/research_campaigns --workspace-root ..
```

Sustituye `CAMPAIGN_ID` por la identidad devuelta por el runner. La configuración
de ejemplo exige un CSV externo preexistente con `date,symbol,close`, su hash y
procedencia; no descarga datos ni oculta una muestra como resultado real.
El recorrido inicial es diario para renta variable, con estrategias registradas
de momentum, reversión y equiponderación. Otros instrumentos, frecuencias,
proveedores y modelos requieren adaptadores y validación propios. Los estados
de campaña y su verificación de artefactos no sustituyen el veredicto económico.

El CLI de pruebas permite inspeccionar y ejecutar perfiles con informes máquina:

```sh
.venv/bin/python scripts/verify_research.py --profile integration --list
.venv/bin/python scripts/verify_research.py --profile offline --output /tmp/quantos-offline-verification
.venv/bin/python scripts/verify_research.py --profile integration --output /tmp/quantos-integration-verification
```

Usa un directorio de salida nuevo en cada ejecución. El informe es
`OUTPUT/verification.json`, con JUnit de las suites en `OUTPUT/STAGE/junit.xml`.
`--only` selecciona checks concretos y `--timeout` limita cada etapa; un resultado
focalizado puede pasar sin completar el perfil. Comprueba `scope` y
`profile_complete`: listar o no ejecutar una prueba no produce aprobación. La
evidencia vigente de ejecución debe acompañar cualquier afirmación de éxito de
un perfil completo.

Offline usa replay y controles de red de sus procesos de prueba; integración
comprueba contratos entre laboratorios y motores locales. El bloqueo Python se
propaga a hijos Python y el navegador dispone de su guard específico; esto no
es un sandbox de red del sistema operativo. Estos perfiles no consultan cuentas
ni acreditan acceso remoto a EODHD/T212. Paper local, demo remoto y live mantienen
clases distintas: este recorrido no establece una conexión T212 ni envía órdenes
reales. Una disponibilidad histórica, auditoría, promoción, riesgo o
reconciliación pendiente conserva su bloqueo explícito.
