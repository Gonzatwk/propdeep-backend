# Auditoría de PropDeep, 23 de octubre de 2026

Cómo leerla:
- **[Hecho]**: lo he comprobado en el código, en la base de datos o en los datos guardados.
- **[Hipótesis]** y **[Opinión]**: lo que creo o recomiendo, pero no está demostrado.
- Gravedad: **CRÍTICO** (hay que arreglarlo antes de seguir midiendo o de enseñarlo a nadie), **IMPORTANTE** (afecta al resultado o a la confianza) y **MEJORA**.

Qué he usado, sin cambiar código ni gastar créditos de The Odds API:
- **Código:** `model.py`, `pipeline.py`, `scripts/backtest.py`, `clients/`, `board.py`, `auto.py`, `track_record.py`, `main.py` y `analisis_peso.py`, más tres revisiones de seguridad, producto y tests.
- **Tests:** `pytest`, 96 de 96 en verde.
- **Caché del backtest:** 1.241 partidos de 2025-26 y 212.659 cuotas de puntos de 8 casas de EE. UU., emparejadas con el resultado real.
- **Datos reales:** `propdeep.db` (abierta solo para leer) y `revision_2026-10-21.csv`.

---

## 1. Resumen de una página

### Dónde estamos de verdad

El software funciona: 96 tests en verde, jornada automática y zona de partidos completa. **El modelo no tiene ventaja demostrable.** Esto sale de 17.549 líneas reales de puntos de 2025-26:

- **La proyección acierta menos que la línea de la casa.** El error medio es de 5,09 puntos frente a 4,85.
- **Está muy mal calibrada.** Cuando dice 15 % de "más", pasa el 44 %. Cuando dice 85 %, pasa el 56 %.
- **Su aportación sobre el mercado es real pero mínima.** Medida mes a mes solo con datos anteriores, le corresponde un peso de **0,07-0,08, no 0,2**.
- **La regla actual es ruido.** Con peso 0,2, umbral de 3 pp y la cuota de la casa con menos margen, habría hecho 585 jugadas en toda la temporada (unas 3,5 por noche), con ROI de **+1,6 % (IC 95 %: −6 % a +9 %)**.
- **Lo único que gana con claridad en los datos no es el modelo.** Es apostar cuando una casa paga por encima del consenso sin margen de las demás: **+11 % a +19 %, con el intervalo por encima de cero en las dos mitades de la temporada**. Pero eso sale casi todo de Bovada y BetOnline, casas offshore que no son legales en España. Con solo casas reguladas desaparece.
- **Rebotes, asistencias y triples nunca se han probado con cuotas reales**, y ya se publican.

### Las 3 cosas más importantes que debes saber

1. **El peso 0,2 se eligió con datos defectuosos.** El modo `--todas-casas` del backtest guarda **una sola casa por línea**, así que no compara casas. Además, aquel backtest llevaba el ajuste por compañeros calculado con quién jugó de verdad, que es información del futuro.

   Con los datos limpios:
   - el peso óptimo es ~0,08;
   - la mezcla a 0,2 predice algo peor que el mercado solo.

2. **El criterio de corte (300 jugadas con ROI ≥ 0) es casi tirar una moneda.**
   - Con 300 apuestas, el intervalo de confianza del ROI es de ±11 puntos. Una estrategia que pierde un 3 % lo supera 3 de cada 10 veces.
   - Además mide cuotas de casas de EE. UU. que no puedes usar desde España: tus picks son de Bet365, que no está en The Odds API.
   - El historial ya contiene **267 veredictos del 21-oct calculados con la configuración antigua** (peso 0,5 y sin el bloqueo de 3 partidos). Esa noche salió −8 %.

3. **Lo que de verdad sirve a un apostador hispano no es el veredicto, sino el precio justo.**
   - Qué probabilidad da el mercado sin margen: el consenso de las casas, o Pinnacle, que ya pagas con la región `eu`.
   - Qué cuota mínima hace falta para que una apuesta valga la pena.
   - Si la cuota de tu casa está por encima o por debajo de ese precio justo.

   Nada de esto gasta créditos extra.

### Las 3 decisiones que tienes que tomar

1. **Redefinir el criterio de corte del 31-dic.**
   - Excluir las predicciones del 21-oct.
   - Medir con métricas de mucha menos varianza: log-loss frente al mercado en todas las líneas analizadas, y CLV frente al cierre de Pinnacle, que cuesta unos 4 créditos por partido.
   - Dejar el ROI como dato secundario.
2. **Decidir qué es PropDeep.**
   - Un "modelo que encuentra ventaja": los datos no lo sostienen.
   - Un "comparador con precio justo de props NBA en español": honesto y útil sin ventaja.
   - O una herramienta personal y pieza de portafolio.
3. **Decidir en qué gastar los créditos que sobran y qué peso usar.**
   - Si quedan unos 15.000 al mes (por confirmar en tu cuenta), puedes validar rebotes, asistencias y triples (~12.000 créditos para 400 partidos) o medir el movimiento de línea a 10 h (~3.000).
   - Y decidir si bajas `MODEL_WEIGHT` a ~0,08 cuando se repita el backtest corregido.

---

## 2. Hallazgos por área

### 2.1 Modelo y ROI

| # | Gravedad | Hallazgo | Dónde |
|---|---|---|---|
| M1 | **CRÍTICO** | **[Hecho]** El modelo apenas aporta información sobre el mercado.<br>• Coeficiente de su desvío en una regresión logística con el mercado como base: 0,060 (IC 0,013-0,107, p = 0,013).<br>• Mes a mes, solo con datos anteriores: 0,066-0,082.<br>• Peso óptimo por log-loss: 0,08.<br>• Con peso 0,2, la mezcla predice peor que el mercado solo (log-loss 0,69250 frente a 0,69217). | §3.2 |
| M2 | **CRÍTICO** | **[Hecho]** `MODEL_WEIGHT=0.2` se decidió con datos que no comparan casas.<br>• `--todas-casas` pasa antes por `parse_props`, que deja **una casa por (mercado, jugador, línea)**: en `odds-api-casas/lineas.csv` hay como máximo 1 fila por línea.<br>• Ese CSV lleva además el ajuste por compañeros con información posterior (31 % de las filas con factor ≠ 1).<br>• `analisis_peso.py` y el resumen de ese backtest (+2,9 %) heredan los dos problemas. | `scripts/backtest.py:426`, `propdeep/clients/odds.py:110-119`, `scripts/backtest.py:697` |
| M3 | **CRÍTICO** | **[Hecho]** El historial mezcla configuraciones y no guarda cuál se usó.<br>• Las 513 líneas del 21-oct se publicaron con peso 0,5 (deducido en 479 de 479 líneas medibles) y sin el bloqueo de 3 partidos: todas tienen `season_games = 0` y ninguna razón de bloqueo. Era el código de `main` antes de fusionar los PR del 22-oct.<br>• 267 tienen veredicto, y contarían para las "300 jugadas". | `propdeep/db.py:85-111` (no guarda versión ni parámetros) |
| M4 | **IMPORTANTE** | **[Hecho]** El modelo solo está muy mal calibrado: dice 15 % y pasa el 44 %; dice 85 % y pasa el 56 %. La mezcla a 0,2 queda razonable entre 45 y 55 %, pero sobrestima arriba (dice 56 % y pasa el 54 %).<br>**[Hecho]** La desviación que usa es corta: el error real dividido entre la desviación usada tiene una desviación típica de 1,12. Lo que más pesa es que, una vez conocida la línea, lo que el modelo se aparta de ella es casi todo ruido. | `model.py:204-221`, §3.3 |
| M5 | **IMPORTANTE** | **[Hecho]** El punto 9 del CLAUDE.md es correcto. La ventaja se mide frente a 1/cuota **de la misma casa con menos margen** (`model.py:247-248` y `odds.py:136`). Con su margen típico (6,1 %), hace falta p_modelo − p_mercado ≥ ~30 pp con peso 0,2. Salta en el **3,3 % de las líneas**.<br>**[Opinión]** No es un fallo que haya que "abrir". Con los datos actuales, subir el peso o bajar el umbral empeora el ROI: peso 0,5 da −2,3 % y el modelo solo −3,6 % (§3.4). | `model.py:244-256` |
| M6 | **IMPORTANTE** | **[Hecho]** Solo se ha probado **puntos** con cuotas reales: la caché tiene únicamente `player_points`. El backtest "proxy" de las otras tres estadísticas no dice nada del mercado y además está obsoleto: es anterior al tope de minutos y proyecta 66,6 puntos a Tristan Vukcevic. | `backtest_cache/odds/`, `backtest_out/proxy/` |
| M7 | **IMPORTANTE** | **[Hecho]** No se mide el CLV, es decir, si nuestra cuota bate a la de cierre. Producción guarda las cuotas de cuando publica (~10 h antes), pero nunca las de cierre. | `auto.py:46`, `board.py:80-109` |
| M8 | **IMPORTANTE** | **[Hecho]** Fugas y sesgos del backtest:<br>(a) **Compañeros**: cuenta como "fuera" a quien no jugó, lo que incluye bajas de última hora, y usa partidos futuros para descartar traspasos (`nxt`). Activado por defecto.<br>(b) **Parámetros sobre la misma muestra**: peso, binomial negativa y bloqueo de 3 partidos se eligieron y se miden sobre la misma temporada.<br>(c) **Media de la liga**: `_league_ppg` de producción usa la temporada entera; solo afecta si se analizan fechas pasadas con el `Analyzer`.<br>(d) **Fotos tardías**: 2 de 1.241 fotos de cuotas son posteriores al inicio. Despreciable. | `backtest.py:136-160`, `backtest.py:697`, `pipeline.py:191-197` |
| M9 | **IMPORTANTE** | **[Hecho]** El backtest no mide lo mismo que producción:<br>• La línea principal se elige distinto: la más cercana al 50/50 en el backtest y la que ofrecen más casas en producción.<br>• La foto de cuotas es de 60 min antes en el backtest y de hasta ~10 h antes en producción.<br>• El backtest no aplica los bloqueos de lesión ni de traspaso.<br>• Los nombres se emparejan de otra forma. | `backtest.py:437-448` frente a `odds.py:122-138`, `auto.py:46` |
| M10 | MEJORA | **[Hecho]** Con líneas enteras, `prob_over` usa `k = floor(línea)` y el empuje cuenta como "menos": la probabilidad del menos sale inflada en P(X = línea). Hoy no afecta: hay 0 líneas enteras en el backtest y en la base de datos. | `model.py:212`, `model.py:248` |
| M11 | MEJORA | **[Hecho]** `analyze()` tiene `model_weight=0.5` por defecto mientras la configuración dice 0,2. Quien la llame sin pasar el peso usa 0,5. | `model.py:239` |
| M12 | MEJORA | **[Hecho]** `devig` es multiplicativo. Con props cerca del 50/50 vale; no merece cambiarlo. | `model.py:224-227` |

Matemáticas comprobadas **[Hecho]**:
- **Binomial negativa:** está bien parametrizada (r = μ²/(var − μ), p = r/(r + μ), media μ).
- **`project`:** pondera 5, 10 y 20 partidos y temporada; ajuste de minutos con tope de ±15 % y ajuste de contexto con tope de ±5 %.
- **Bloqueos:** los cuatro (Out/Doubtful, <5 partidos, <3 de la temporada, traspasado con <5) están como dice el CLAUDE.md.

No he encontrado errores matemáticos; el problema es de información, no de cálculo.

### 2.2 Calidad del código

| # | Gravedad | Hallazgo | Dónde |
|---|---|---|---|
| C1 | **CRÍTICO** | `--todas-casas` no hace lo que dice (ver M2). La documentación promete "una fila por casa". | `backtest.py:426`, `BACKEND.md:181` |
| C2 | **CRÍTICO** | No se guarda la versión ni los parámetros del modelo en cada predicción (ver M3). | `db.py:89-111` |
| C3 | **IMPORTANTE** | **Liquidación frágil:**<br>• Si Balldontlie marca un partido "Final" con el boxscore aún vacío, **todas las props de ese partido se anulan para siempre**.<br>• Un fallo de la API en `bdl.game()` o `game_stats()` corta toda la liquidación, y `auto.tick` liquida antes de publicar sin `try`, así que tampoco publica.<br>• Los partidos aplazados se quedan pendientes indefinidamente.<br>**[Hipótesis]** Que Balldontlie dé "Final" antes que las estadísticas no lo he visto pasar, pero el código no lo protege. | `track_record.py:31`, `track_record.py:43-49`, `auto.py:55-56` |
| C4 | **IMPORTANTE** | **[Hecho]** Hay 22 predicciones sin `game_id` (16 con veredicto) que nunca se liquidarán: jugadores traspasados del 21-oct, antes del arreglo. No hay forma de anularlas a mano. | `propdeep.db`, `track_record.py:28` |
| C5 | **IMPORTANTE** | **Jornada automática:**<br>• Un partido publicado a medias (por ejemplo, solo puntos colgados a 10 h) no se vuelve a mirar.<br>• Un partido que no deja ninguna línea se vuelve a pedir cada 20 min.<br>• Si un partido falla, se cortan los demás de esa vuelta.<br>• No hay restricción única (evento, jugador, estadística): `/admin/board` y el hilo automático a la vez podrían duplicar filas y créditos. | `auto.py:39-77`, `board.py:221` |
| C6 | **IMPORTANTE** | **[Hecho]** Hay jugadores con apodo que no se emparejan: Herb Jones, Ace Bailey, Bones Hyland, Moe Wagner, Ron Holland, Alex Sarr, Vincent Williams Jr… En el backtest quedan 218 nombres distintos sin emparejar; los más frecuentes son de rotación habitual.<br>**[Hipótesis]** En producción pasa algo parecido: `find_player` busca por la última palabra y solo acepta un nombre exacto o un candidato único. | `balldontlie.py:64-73`, `backtest.py:195-197` |
| C7 | **IMPORTANTE** | Errores que se tragan sin registro (`track_record.py:84`, `main.py:485`).<br>Accesos directos a claves de datos externos (`pipeline.py:62`, `odds.py:157-158`). `scan_day` solo captura `LookupError` y `ValueError`, así que un `KeyError` corta la jornada después de haber pagado las cuotas. | citados |
| C8 | MEJORA | **Duplicados:**<br>• `_aware` está copiado en 5 módulos.<br>• `main_lines` existe dos veces, con lógica distinta.<br>• Hay dos listas de espera (backend y Cloudflare).<br>• La cuota total de combinadas y el "cobras X" se calculan en la web y en el backend.<br>• Los precios están fijos en `zona.js`, sin relación con Stripe. | varios |
| C9 | MEJORA | **Código y documentación desfasados:**<br>• `billing.PLANS` no se usa.<br>• `BACKEND.md:25` dice "distribución normal" (es binomial negativa).<br>• `web/README.md` describe `/historial` y `GET /predictions`, que no existen.<br>• Sobra `vercel.json`.<br>• `PRODUCT.md` aún habla de la preventa de 9 €.<br>• `backtest_out/proxy` está obsoleto. | citados |
| C10 | MEJORA | En mi ejecución, `pytest` falló **al limpiar** su carpeta temporal (PermissionError en `pytest-current`, Windows). Con `--basetemp` pasan los 96. Puede ser cosa de mi entorno. | — |

**Tests: qué no está probado y debería estarlo [Hecho]**
- **Liquidación:**
  - un empuje;
  - un jugador que falta en el boxscore;
  - el boxscore vacío con el partido terminado;
  - un partido aplazado.
- **`_team_and_game`:**
  - "LA Clippers" y "Los Angeles Clippers";
  - el caso en que `event_teams` no coincide;
  - el caso en que hay partido pero no equipo.
- **`_points_allowed_factor` y `_league_ppg`:** los fakes devuelven siempre 1,0, así que **el ajuste por rival nunca se ha probado**.
- **El `find_player` real:** acentos, sufijos, nombres repetidos.
- **El hash:** no hay test que lo recalcule y compruebe.
- **Webhook de Stripe:** `test_pass_gives_seven_days_and_stacks` manda **el mismo evento** dos veces y da por bueno que sume 14 días. El test consagra el fallo de idempotencia.
- **Fugas del backtest:** el test cubre las estadísticas del propio jugador, pero no el marcador de los rivales ni a los compañeros.
- **`analyze`:** ningún test produce un "menos" ni comprueba la fórmula exacta de la ventaja.

### 2.3 Seguridad y legal

| # | Gravedad | Hallazgo | Dónde |
|---|---|---|---|
| S1 | **CRÍTICO** | **[Hecho]** `POST /analyze` es **público**. Devuelve `side`, `edge`, `confidence`, `expected_value` y `odds_taken`, y en cada llamada gasta Balldontlie y Claude sin límite. La web no lo usa. Hay un test que comprueba que devuelve el lado. Hoy el servidor solo corre en local, pero en un despliegue sería una fuga del veredicto y del gasto. | `main.py:125-129`, `tests/test_api.py:38` |
| S2 | **IMPORTANTE** | **[Hecho]** `/board/top` ("Mejores proyecciones") devuelve `direction: over/under` y ordena por la distancia entre proyección y línea.<br>• Coincide con el veredicto interno en 255 de 267 líneas.<br>• La web lo pinta como "Mejor más/menos" con filtro por lado.<br>• Ordena exactamente por la señal que **pierde** en el backtest (modelo solo: −3,6 %). | `board.py:177-198`, `web/src/pages/zona/Proyecciones.jsx:35-36,80` |
| S3 | **IMPORTANTE** | **[Hecho]** **Stripe:**<br>• El webhook está firmado (bien), pero no descarta eventos repetidos ni ordena: un pase duplicado suma otros 7 días y un `updated` antiguo puede pisar un `deleted`.<br>• `DELETE /me` deja borrar la cuenta con la suscripción en pausa (`paused` no está en `ACTIVE_STATUSES`), y Stripe volvería a cobrar.<br>• El correo del día 5 no se envía en modo automático, y sin proveedor se marca como enviado, aunque la web promete avisar. | `billing.py:136-137`, `accounts.py:23`, `main.py:306-313`, `main.py:489`, `mailer.py:41-45`, `Cuenta.jsx:58` |
| S4 | **IMPORTANTE** | **[Hecho]** **Accesos:**<br>• `LOCAL_LOGIN` devuelve una sesión sin correo a cualquier dirección de `ADMIN_EMAILS`. Solo lo protege que `WEB_URL` sea localhost; no se comprueba dónde escucha el servidor.<br>• Hoy `CORS_ORIGINS` está limitado a `localhost:5173`, pero su valor por defecto es `*`.<br>• Sin proveedor de correo, el enlace de acceso completo sale en el log.<br>• No hay límite por IP en `/auth/login`, `/waitlist` ni `/analyze`. | `main.py:243-244`, `config.py:37`, `config.py:76-78`, `mailer.py:44`, `accounts.py:108-118` |
| S5 | **IMPORTANTE** | **[Hecho]** La portada promete datos que el modelo no usa: "minutos y uso", "en qué posición", "ritmo de juego", "viajes", "bajas del rival" y "riesgo de paliza". El modelo solo usa casa/fuera, back-to-back, puntos que concede el rival (solo en puntos), lesión y compañeros (apagado).<br>**[Opinión]** Antes de vender sería publicidad engañosa. | `web/src/pages/Home.jsx:14-16`, `model.py:65-78` |
| S6 | **IMPORTANTE** | **[Hecho]** **Textos caducados:**<br>• "Abre el 20 de octubre" aparece en unos 12 sitios: `Home.jsx`, `Anuncio.jsx`, `Avisame.jsx`, `Chat.jsx`, `Entrar.jsx`, `Partidos.jsx`, `MisPicks.jsx`, `DatoDelDia.jsx`, `Cuenta.jsx`, `Zona.jsx`.<br>• Se anuncia la subida a 19 € el 1-ene-2027 sin que el producto esté a la venta. | `web/src/` |
| S7 | MEJORA | **[Hecho]** El `content_hash` es público en `/board/lines` y se calcula sobre un registro que incluye `side`, `edge` y `confidence`.<br>**[Hipótesis]** Probando las combinaciones posibles (unas 10⁵) se recupera el veredicto. | `db.py:82-111`, `board.py:173` |
| S8 | MEJORA | **[Hecho]** El historial **no es verificable por terceros**. Los hashes solo existen en la base de datos: quien tenga la base puede editar una fila y recalcular su hash. Para que sea verificable hay que publicarlos fuera (un commit o un gist diario, o OpenTimestamps). | `db.py` |
| S9 | MEJORA | **[Hecho]** Detalles menores:<br>• El token de administración se compara con `!=`, no en tiempo constante.<br>• Las sesiones caducadas nunca se limpian.<br>• `settle_manual` deja anular un pick ya empezado; solo lo impide la web.<br>• `/tipsters`, si se hace público, enseña las selecciones pendientes de otros. | `main.py:87`, `picks.py:241-261` |
| S10 | MEJORA | **[Hecho]** En la web no se menciona la autoprohibición (RGIAJ) ni ningún teléfono de ayuda; solo jugarbien.es.<br>**[Opinión]** No soy abogado. Antes de cobrar a nadie, conviene una consulta sobre la Ley 13/2011 y el RD 958/2020 para una web de análisis sin afiliación que publica picks y rendimientos. | `Footer.jsx` |

**Lo que está bien [Hecho]:**
- **Avisos visibles:** en todas las páginas hay +18, "sin garantía", "no son recomendaciones", "riesgo de perder dinero" y jugarbien.es (`Footer.jsx`, `Header.jsx:60`).
- **Textos:** ningún "pick seguro" ni "ganancia garantizada"; la sección de preguntas lo niega expresamente.
- **Stripe:** el webhook está firmado.
- **Accesos:** enlaces mágicos aleatorios, guardados como hash, de un solo uso y con 20 min de caducidad.
- **Veredicto:** ni el chat ni los informes lo reciben. Las 513 notas terminan con "no una recomendación".
- **RGPD:** existe `DELETE /me`.

### 2.4 Producto: inventario

| Función | Estado [Hecho] | ¿Aporta valor real hoy? [Opinión] | Veredicto |
|---|---|---|---|
| Zona de partidos (líneas, proyección, % sobre la línea, desgloses) | Completa | Sí, es el núcleo | **Mantener** y añadir el precio justo |
| Comparador de casas / mejor cuota | Completo | A medias: son casas de EE. UU. (la región `eu` solo aporta Pinnacle en props) | **Mantener**, reorientado a precio justo y cuota mínima |
| Informe por línea (Claude o plantilla) | Completo | Poco: redacta números que ya se ven | **Simplificar**: plantilla, con Claude opcional |
| Mejores proyecciones (`/board/top`) | Completo | Negativo: empuja hacia la señal que pierde y revela el lado | **Quitar**, o rehacer como "más lejos del precio justo" |
| Chat "Pregunta a PropDeep" | Completo, necesita Claude y suscripción | Poco para uso personal, y cuesta | **Congelar** |
| Mis picks y combinadas | Completo | Sí, como disciplina y diario | **Mantener**, con CLV y sin cifras grandes de rendimiento |
| Paper bets | Completo (misma tabla que picks, con `paper=1`) | Poco: duplica Mis picks | **Simplificar**: un filtro dentro de Mis picks |
| Auditoría de tipsters | Manual y privada | Poco, y con riesgo legal si se publica | **Congelar** |
| Dato del día (imagen y vídeo para redes) | Solo web | Ninguno sin lanzamiento | **Congelar** |
| Moneyline | Completo, cuesta 2 créditos por hora | Poco: fuera del foco de props | **Congelar**, o pedirlo solo a mano |
| Jornada automática | Completa | Sí: alimenta el historial | **Mantener** y arreglar C3 y C5 |
| Historial interno y track record (admin) | Completo | Sí, si guarda la versión del modelo | **Mantener** y arreglar C2 |
| Cuentas por enlace, Stripe, pase, pausa, correo del día 5 | Código completo, sin configurar | Ninguno hasta lanzar | **Congelar** (arreglar S3 antes de activar) |
| Aviso de subida a 19 € | Solo texto | Compromiso público sin producto | **Quitar** el aviso |
| Lista de espera (dos versiones) | Funciona | Poco | **Simplificar** a una |
| Landing y páginas legales | Completas | Necesarias | **Corregir** S5 y S6 |
| Demo e informes de ejemplo | Demo bien; `informes_ejemplo.json` vacío | La demo sirve | Mantener la demo y quitar el hueco vacío |
| `POST /analyze` | Huérfano | Negativo (S1) | **Quitar o proteger** |
| `scripts/picks_hoy` | Funciona; gasta créditos y duplica la jornada automática | Poco con `AUTO_JORNADA=1` | Usar solo sin la jornada automática |
| `scripts/backtest`, `analisis_peso`, `analisis_companeros` | Funcionan, con M2 | Sí, una vez corregidos | **Arreglar** y repetir |

**[Hecho] Sobre Mis picks.** Las 10 jugadas apuntadas el 21-oct son todas a "más" en Bet365:
- La mayoría a cuota baja: 1,33-1,80.
- Hay 2 combinadas, a 5,16 y 7,8, con favoritos a ganador.

**[Hecho]** En 2025-26, apostar siempre al "más" de puntos perdió un 5 % incluso con la mejor cuota de 8 casas. Una combinada multiplica el margen de cada selección: con un 5 % por pata, 5 patas dan un 23 % de pérdida esperada.

**[Opinión]** Si la herramienta sirve para algo, es para no hacer justo eso.

**Qué haría útil la herramienta aunque el modelo no tenga ventaja [Opinión, apoyada en §3.6]**
1. **Precio justo en cada línea.** Probabilidad sin margen del consenso de casas, o de Pinnacle cuando esté, con la **cuota mínima** para el más y para el menos. Ejemplo: "para que el más 22,5 valga la pena, necesitas 1,93 o más".
2. **Calculadora "mi cuota".** Metes la línea y la cuota de tu casa española y te dice el EV frente al precio justo, incluso si tu línea es distinta. Es lo único accionable desde España, porque ni Bet365 ni las casas españolas están en The Odds API.
3. **Radar de mercado.** Casas cuya línea difiere del consenso en 1-2 puntos o cuya cuota supera el precio justo en un 3 % o más. Debe presentarse como dato de mercado, no como pick.
4. **CLV de tus propios picks.** Comparar la cuota a la que apostaste con el cierre sin margen de Pinnacle. Es la mejor señal temprana de si apuestas bien.

---

## 3. Análisis del ROI

### 3.1 Datos

| Fuente | Contenido |
|---|---|
| `backtest_cache/odds/` | 1.241 fotos (una por partido de 2025-26, 21-oct a 17-abr), **solo `player_points`**, región `us`, ~64 min antes del inicio (mediana). 8 casas: Bovada, BetRivers, DraftKings, William Hill US, FanDuel, BetMGM, BetOnline y Fanatics. |
| Emparejamiento | 212.659 cuotas emparejadas con el resultado (Balldontlie), 17.549 jugador-partido, 0 líneas enteras (ningún empuje). |
| Proyección | Recalculada con el código actual (`compute_trends`, `project`, `prob_over`), **sin** ajuste por compañeros, como en producción hoy. |
| Línea principal | Igual que producción (`odds.py:main_lines`): la que ofrecen más casas, a igualdad la más equilibrada, y la casa con menos margen. Además: la mejor cuota de cada lado entre las casas que ofrecen esa línea. |
| Intervalos | IC 95 % = media ± 1,96 · error típico por apuesta. |

**Margen del mercado [Hecho]:**
- **Casa con menos margen:** 6,06 % (mediana).
- **Mejor cuota de cada lado** (líneas con 5 casas o más): 3,19 %.
- **Arbitraje:** el 5,2 % de las líneas lo tenía en la foto.

**[Hecho]** Comparar casas reduce el margen a la mitad.

### 3.2 ¿Aporta información el modelo? (17.549 líneas)

| Probabilidad | Brier (menos es mejor) | Log-loss |
|---|---|---|
| Mercado (consenso sin margen) | 0,24951 | 0,69217 |
| Mercado (casa con menos margen) | 0,24956 | 0,69226 |
| **Modelo solo** | **0,26661** | **0,73317** |
| Mezcla con peso 0,05 | 0,24940 | 0,69195 |
| Mezcla con peso 0,10 | **0,24939** | **0,69193** |
| Mezcla con peso 0,20 (actual) | 0,24968 | 0,69250 |
| Mezcla con peso 0,30 | 0,25037 | 0,69391 |
| Mezcla con peso 0,50 | 0,25298 | 0,69936 |

**Regresión logística** del resultado sobre logit(mercado) y [logit(modelo) − logit(mercado)]:

| Término | Coeficiente | IC 95 % | p |
|---|---|---|---|
| logit del mercado | 1,128 | 0,74-1,52 | <0,001 |
| desvío del modelo | **0,060** | 0,013-0,107 | 0,013 |

**Coeficiente del modelo mes a mes, ajustado solo con los meses anteriores:**

| Mes | Coeficiente |
|---|---|
| Diciembre | 0,078 ± 0,090 |
| Enero | 0,082 ± 0,073 |
| Febrero | 0,079 ± 0,061 |
| Marzo | 0,079 ± 0,055 |
| Abril | 0,066 ± 0,049 |

**[Hecho] Error absoluto medio:** proyección 5,09 puntos, línea de la casa 4,85.

**Conclusión:**
- **[Hecho]** El modelo tiene una pizca de información propia, significativa y estable.
- **[Hecho]** El peso que le corresponde es 0,07-0,08.
- **[Opinión]** Con eso no se paga el margen de una casa (ver §3.4).

### 3.3 Calibración: cuando dice X %, ¿pasa el X %?

| Tramo | Modelo solo: n | dice | pasa | Mezcla 0,2: n | dice | pasa |
|---|---|---|---|---|---|---|
| ≤ 0,20 | 506 | 14,9 % | 44,5 % | — | — | — |
| 0,20-0,30 | 1.531 | 25,9 % | 47,8 % | — | — | — |
| 0,30-0,40 | 3.661 | 35,6 % | 48,9 % | 54 | 39,3 % | 42,6 % |
| 0,40-0,45 | 2.442 | 42,6 % | 47,3 % | 1.761 | 43,5 % | 46,6 % |
| 0,45-0,50 | 2.520 | 47,5 % | 49,3 % | 8.658 | 47,8 % | 47,9 % |
| 0,50-0,55 | 2.273 | 52,5 % | 49,1 % | 6.240 | 52,0 % | 50,3 % |
| 0,55-0,60 | 1.724 | 57,4 % | 49,7 % | 819 | 56,4 % | 53,7 % |
| 0,60-0,70 | 2.034 | 64,2 % | 49,2 % | 17 | 60,7 % | 76,5 % |
| 0,70-0,80 | 650 | 74,0 % | 53,1 % | — | — | — |
| > 0,80 | 208 | 85,4 % | 56,2 % | — | — | — |

El mercado sí está bien calibrado:
- Dice 48,5 % y pasa el 47,3 %.
- Dice 51,5 % y pasa el 50,7 %.
- Hay un leve sesgo hacia el menos, de ~1 pp.

En la noche real del 21-oct (las 4 estadísticas, 397 líneas con resultado) pasa lo mismo: el modelo dice 87 % y pasa el 53 %; dice 13 % y pasa el 44 %.

### 3.4 Regla de producción y variantes (puntos, 2025-26)

Sin los jugadores bloqueados. Un pick por jugador y partido.

| Regla | Cuota usada | n | ROI | IC 95 % |
|---|---|---|---|---|
| Peso 0,2, ventaja ≥ 3 pp (**producción hoy**) | Casa con menos margen | 585 | **+1,6 %** | −6,1 % a +9,3 % |
| Peso 0,2, ventaja ≥ 3 pp | Mejor cuota | 2.354 | +2,6 % | −1,5 % a +6,6 % |
| Peso 0,5, ventaja ≥ 3 pp (antigua) | Casa con menos margen | 6.482 | −2,3 % | −4,6 % a 0,0 % |
| Peso 0,5, ventaja ≥ 3 pp | Mejor cuota | 8.524 | +0,2 % | −1,9 % a +2,3 % |
| Modelo solo (peso 1), ventaja ≥ 3 pp | Casa con menos margen | 11.167 | −3,6 % | −5,4 % a −1,9 % |
| Modelo solo | Mejor cuota | 12.375 | −1,1 % | −2,8 % a +0,6 % |
| Lado del modelo con desvío ≥ 10 pp | Mejor cuota | 8.392 | −0,1 % | −2,2 % a +1,9 % |
| Lado del modelo con desvío ≥ 25 pp | Mejor cuota | 1.425 | +1,5 % | −3,5 % a +6,5 % |

Los resúmenes guardados en `backtest_out/` (referencia; ver M2):
- `odds-api`, del 5-oct, con peso 0,5: n = 6.834, −2,8 % (IC −5,1 % a −0,5 %).
- `odds-api-casas`, del 22-oct: n = 1.128, +2,9 % (IC −3,0 % a +9,0 %). **No es fiable**: una casa por línea y compañeros con información futura.

### 3.5 Desglose por segmentos

Regla de producción (peso 0,2, umbral de 3 pp) con la mejor cuota: n = 2.354, +2,6 %.

| Segmento | Tramo: n, ROI [IC 95 %] |
|---|---|
| **Cuota** | <1,80: 43, −0,6 % [−27; +26] · 1,80-1,90: 415, +6,9 % [−2,0; +15,8] · 1,90-2,00: 1.032, −1,8 % [−7,8; +4,2] · 2,00-2,20: 700, +3,0 % [−4,7; +10,8] · >2,20: 164, +17,9 % [−0,8; +36,5] |
| **Línea** | ≤9,5: 806, +1,4 % [−5,5; +8,2] · 10-14,5: 805, +1,9 % [−5,1; +9,0] · 15-19,5: 445, +4,3 % [−5,1; +13,7] · 20-24,5: 191, +5,7 % [−8,7; +20,1] · ≥25: 107, +3,7 % [−15,7; +23,1] |
| **Minutos** (media de los últimos 10) | <20: 564, +7,1 % [−1,0; +15,2] · 20-26: 673, +0,6 % [−7,1; +8,2] · 26-32: 729, −0,9 % [−8,3; +6,5] · ≥32: 388, +5,9 % [−4,3; +16,0] |
| **Partidos de la temporada** | 0-9: 257, +4,1 % [−8,0; +16,1] · 10-29: 756, +1,9 % [−5,3; +9,1] · 30-59: 1.065, +2,6 % [−3,6; +8,7] · 60+: 276, +3,1 % [−8,6; +14,8] |
| **Lado** | más: 722, +1,2 % [−6,3; +8,7] · menos: 1.632, +3,2 % [−1,7; +8,0] |
| **Casa de la mejor cuota** | **Bovada: 718, +11,1 % [+3,2; +18,9]** · BetRivers: 291, +5,6 % · BetMGM: 369, +0,6 % · DraftKings: 280, −0,7 % · BetOnline: 177, −3,2 % · FanDuel: 279, −4,1 % · William Hill US: 208, −10,8 % [−24,1; +2,5] · Fanatics: 32, +13,7 % |
| **Mes** | oct: 62, −2,4 % · nov: 376, +4,7 % · dic: 370, +2,9 % · ene: 529, +5,7 % · feb: 418, −0,2 % · mar: 441, +4,4 % · abr: 158, −9,6 % |
| **Estadística** | Solo hay cuotas reales de puntos. Rebotes, asistencias y triples **sin datos**. |

Con la señal del modelo (desvío ≥ 10 pp, mejor cuota, n = 8.392, −0,1 %) sale lo mismo:
- Solo Bovada es positivo: +8,6 % [+2,6; +14,6].
- Jugadores con menos de 20 minutos: +4,0 % [−0,5; +8,6].
- Líneas de 20 puntos o más: −3 % a −4 %.

**Lectura:**
- **[Hecho]** Ningún segmento tiene el intervalo por encima de cero salvo "la mejor cuota era de Bovada".
- **[Hecho]** Se miraron unos 30 segmentos, así que con un 95 % se esperan 1 o 2 falsos positivos.
- **[Opinión]** Lo de Bovada no es mérito del modelo: es que Bovada se aparta del mercado (ver §3.6). El resto es ruido.

### 3.6 Estrategias sin modelo

**Apostar a ciegas (mejor cuota, n = 17.549):**

| Regla | ROI | IC 95 % |
|---|---|---|
| Todo a "más" | −5,0 % | −6,4 % a −3,5 % |
| Todo a "menos" | −1,2 % | −2,6 % a +0,2 % |
| Todo a "menos" en la casa con menos margen | −3,9 % | −5,3 % a −2,5 % |

**[Hecho]** El "menos" sale unos 4 puntos mejor que el "más" (sesgo conocido de las props), pero no paga el margen.

**Cuota por encima del consenso.** Se apuesta en la casa cuya cuota supera el precio justo calculado con **las demás** casas (consenso sin margen, 4 casas o más en la línea), una vez por jugador y partido:

| EV esperado ≥ | n | ROI | IC 95 % | Por noche |
|---|---|---|---|---|
| 0 % | 3.612 | +2,0 % | −1,4 % a +5,3 % | 21,5 |
| 2 % | 1.487 | +5,3 % | −0,1 % a +10,7 % | 8,9 |
| **4 %** | **708** | **+13,3 %** | **+5,1 % a +21,4 %** | 4,2 |
| 6 % | 415 | +14,9 % | +4,0 % a +25,9 % | 2,5 |
| 8 % | 279 | +18,9 % | +5,2 % a +32,6 % | 1,7 |

Con EV ≥ 4 %:
- **Por mitades de temporada:** +15,2 % [+2,5; +28,0] en la primera y +12,0 % [+1,4; +22,5] en la segunda.
- **Sin Bovada:** n = 120, +15,0 % [−3,7; +33,7].
- **Casas:** con EV ≥ 3 %, 755 de 1.026 apuestas son de Bovada.
- **Cuota media:** 2,21.

**Precio justo del consenso más una ligera inclinación del modelo, apostando a la mejor cuota** (3 casas o más):

| Casas | Peso | Umbral | n | ROI [IC 95 %] | 1.ª mitad | 2.ª mitad |
|---|---|---|---|---|---|---|
| Todas | 0 | 1 pp | 759 | **+11,0 % [+3,2; +18,9]** | +11,3 % | +10,9 % |
| Todas | 0 | 3 pp | 242 | +18,8 % [+3,9; +33,6] | +35,4 % | +10,3 % |
| Todas | 0,08 | 2 pp | 567 | +10,3 % [+1,3; +19,4] | +22,4 % | +2,3 % |
| Todas | 0,2 | 2 pp | 3.523 | +3,3 % [0,0; +6,6] | +4,9 % | +2,0 % |
| Solo reguladas EE. UU. (sin Bovada ni BetOnline) | 0 | 1 pp | 80 (0,5 por noche) | +22,7 % [0,0; +45,4] | — | — |
| Solo reguladas EE. UU. | 0,08 | 1 pp | 639 | −2,1 % [−9,9; +5,6] | +2,0 % | −5,3 % |
| Solo reguladas EE. UU. | 0,2 | 2 pp | 2.669 | +0,6 % [−3,1; +4,3] | +2,6 % | −1,1 % |

**Línea principal de una casa distinta de la del consenso** (apostando hacia el consenso, con la cuota de esa casa):

| Diferencia | n | ROI | IC 95 % |
|---|---|---|---|
| ≥ 1 punto | 9.924 | −1,5 % | −3,2 % a +0,3 % |
| ≥ 2 puntos | 273 | +14,0 % | +3,7 % a +24,3 % |
| ≥ 3 puntos | 36 | +13,5 % | −13,8 % a +40,8 % |

**Lectura:**
- **[Hecho]** La única ventaja estable de 2025-26 está en **casas blandas que se apartan del consenso**, no en el modelo. Añadirle el modelo no mejora nada: con peso 0,2 la diluye.
- **[Hecho]** Con solo casas reguladas de EE. UU., las oportunidades casi desaparecen.
- **[Hipótesis]** Estas cifras son optimistas para la vida real: una foto puntual que puede estar desfasada, límites de apuesta en las casas offshore y nada de esto accesible desde España.
- **[Hipótesis]** La pregunta que importa, si Bet365 o las casas españolas se apartan del consenso, **no se puede responder con The Odds API**: no las cubre.

### 3.7 La noche real del 21-oct (base de datos y `revision_2026-10-21.csv`)

**[Hecho]** Qué se publicó:
- 513 líneas de las 4 estadísticas; 267 con veredicto (170 de confianza "alta").
- Se usó peso 0,5 y no hubo bloqueos, aunque todas tenían 0 partidos de la temporada.
- Casa principal: FanDuel 310, BetOnline 96, DraftKings 74, Bovada 28.
- Pinnacle está en 313 de las 513 líneas. Es la única casa de la región `eu` que trae props.

**[Hecho]** Resultado de las 196 líneas con veredicto ya liquidables:

| Grupo | n | ROI |
|---|---|---|
| Total (acierto 48,5 %) | 196 | **−8,0 %** |
| Más | 96 | −16,1 % |
| Menos | 100 | −0,2 % |
| Puntos | 64 | −0,6 % |
| Rebotes | 49 | −18,9 % |
| Asistencias | 44 | +0,9 % |
| Triples | 39 | −16,4 % |

**[Opinión]** Una sola noche y con resultados correlacionados no prueba nada, pero no contradice el backtest.

### 3.8 CLV

- **[Hecho]** No se mide.
- **[Opinión]** Es la métrica más útil que falta. Una apuesta concreta puede perder por varianza, pero batir el cierre de forma sistemática solo pasa si hay información. Con 300 apuestas, el CLV medio se mide con un error de décimas de punto; el ROI, con un error de ±11 puntos.
- **Cómo:** guardar ya las cuotas al publicar (se hace) y pedir **una foto del cierre** de los partidos publicados, poco antes del inicio.
  - Solo región `eu` (Pinnacle): ~4 créditos por partido, unos 900 al mes.
  - Con `us,eu`: ~8 por partido, unos 1.800 al mes.

### 3.9 Potencia del criterio de corte

**[Hecho, cálculo]** Para apuestas a ~1,95, la desviación típica del beneficio por apuesta es ≈ 0,97:

| Apuestas | Error típico del ROI | IC 95 % |
|---|---|---|
| 300 | 5,6 pp | ±11 pp |
| 1.000 | 3,1 pp | ±6 pp |
| ~4.000 | 1,5 pp | ±3 pp, lo justo para distinguir +3 % de 0 |

Con 300 apuestas, una estrategia que de verdad pierde un 3 % termina con ROI ≥ 0 un **30 %** de las veces. Una que gana un 3 % termina en negativo otro 30 %.

### 3.10 Lo que falta por medir y cuánto cuesta

El coste del endpoint histórico es 10 × mercados × regiones por partido, según `backtest.py:420`.

| Medición | Créditos |
|---|---|
| Rebotes, asistencias y triples, región `us`, 60 min | 30 por partido: ~12.000 para 400 partidos; ~37.000 la temporada |
| Puntos a 10 h del inicio (como producción): movimiento de línea y CLV histórico | 10 por partido: ~3.000 para 300 partidos; ~12.300 la temporada. Con Pinnacle (`us,eu`), el doble |
| Robos, tapones y PRA | 30 por partido, igual que la primera fila |

**[Hipótesis]** Producción gasta ~8 créditos por partido (4 mercados × `us,eu`) más hasta 2 por hora de moneyline: unos 2.000-3.300 al mes. Si el plan es de 20.000, sobran del orden de 15.000. **Compruébalo en tu cuenta antes de lanzar nada**, y usa siempre `--estimar`.

---

## 4. Ideas, ordenadas por impacto y esfuerzo

Impacto y esfuerzo: A = alto, M = medio, B = bajo.

| # | Idea | Beneficio | Esfuerzo | Riesgo | Créditos |
|---|---|---|---|---|---|
| 1 | **Versión del modelo en cada predicción** y criterio de corte por versión | A: sin esto el historial no sirve para decidir | B | B | 0 |
| 2 | **Corregir `--todas-casas`**, repetir el backtest con `--sin-companeros` y `analisis_peso` desde la caché | A: decide el peso con datos limpios | B | B | 0 (todo está en caché) |
| 3 | **Precio justo y cuota mínima** por lado en cada línea (consenso o Pinnacle sin margen) | A: útil desde España, honesto | B | B | 0 |
| 4 | **Calculadora "mi cuota"** (línea y cuota de tu casa → EV frente al precio justo) | A: lo único accionable para un apostador español | B-M | B | 0 |
| 5 | **Métrica semanal**: log-loss y Brier de p_final frente al mercado en todas las líneas | A: miles de líneas por semana, mucha más potencia que el ROI | B | B | 0 |
| 6 | **CLV con el cierre de Pinnacle** para predicciones y Mis picks | A | M | B | ~900-1.800 al mes |
| 7 | **Muestreo manual de Bet365**: apuntar ~50 líneas por semana con su cuota y compararlas con el precio justo | A: es la única forma de saber si las casas españolas dejan valor | M (tiempo tuyo) | B | 0 |
| 8 | Bajar `MODEL_WEIGHT` a ~0,08 o calibrar el modelo (Platt o isotónica) y ampliar la varianza | M: menos jugadas y mejor calibradas | B | B (tras el punto 2) | 0 |
| 9 | Cerrar `/analyze`, quitar `direction`, arreglar la liquidación (C3, C4) y los textos (S5, S6) | M: higiene, protege el historial | B | B | 0 |
| 10 | Backtest de rebotes, asistencias y triples con cuotas reales | A: hoy se publican sin validar | B (el script existe) | B | ~12.000 (400 partidos) |
| 11 | Foto a 10 h de puntos: movimiento de línea y CLV histórico | M | B | B | ~3.000 (300 partidos) |
| 12 | Radar de líneas desalineadas y cuotas fuera de consenso, como dato de mercado | M en España, A con casas offshore | B | M: no debe parecer un pick | 0 |
| 13 | Tabla de alias de nombres (Herb Jones, Bones Hyland…) | B-M | B | B | 0 |
| 14 | Publicar los hashes fuera (commit diario u OpenTimestamps) | M si algún día se lanza | B | B | 0 |
| 15 | Estudio público del backtest (qué funciona y qué no en props NBA) como portafolio | M (personal) | M | B | 0 |
| 16 | Proyección de minutos × producción por minuto, con la línea como punto de partida bayesiano | B-M: la línea ya lo recoge casi todo | M-A | M (sobreajuste) | 0 |
| 17 | Robos, tapones y PRA | B-M | B | B | ~37.000 la temporada |

**Lo que no haría [Opinión]:**
- Subir el peso o bajar el umbral para tener más jugadas: los datos dicen que empeora.
- Añadir más funciones de pago.
- Abrir otros deportes.
- Gastar créditos en robos y tapones antes de validar las 3 estadísticas que ya se publican.

---

## 5. Plan recomendado hasta el 31-dic-2026

**Semana 1 (24-31 oct): que el historial sirva para decidir. Sin créditos.**
1. Tomar la decisión 1 (nuevo criterio de corte) y apuntarla en el CLAUDE.md.
2. Guardar en cada predicción la versión: commit, `MODEL_WEIGHT`, `MIN_EDGE` y regiones. Las del 21-oct no se editan; se excluyen por fecha o versión en el resumen.
3. Cerrar `POST /analyze` (solo admin) y quitar `direction` de `/board/top`, o la página entera.
4. Liquidación:
   - no anular si el boxscore viene vacío;
   - `try` por partido;
   - anulación manual de las predicciones sin `game_id`.
   Con sus tests.
5. Corregir `--todas-casas`, y repetir desde la caché `python -m scripts.backtest --lineas odds-api --todas-casas --sin-companeros --max-creditos 0` y luego `analisis_peso`. Comprobar antes que no pide nada nuevo: todo debería salir de la caché.
6. Decidir el peso con los datos limpios.
7. Textos de la web: fuera "20 de octubre", las promesas no cubiertas (S5) y el aviso de subida.

**Semana 2 (1-7 nov): el producto que sí sirve.**

8. Precio justo y cuota mínima en cada línea, y calculadora "mi cuota".
9. Script semanal de métricas: log-loss frente al mercado por estadística, número de jugadas y ROI como dato secundario.
10. CLV: foto del cierre de los partidos publicados. Estimar el coste primero (~900-1.800 créditos al mes).

**Semanas 3-4 (8-21 nov): gastar créditos con cabeza.**

11. Decisión 3: con `--estimar`, backtest de rebotes, asistencias y triples (unos 400 partidos) o foto a 10 h de puntos.
12. Empezar el muestreo manual de Bet365: unas 50 líneas por semana, apuntando línea, cuota y hora.

**Del 22 de noviembre al 31 de diciembre: medir sin tocar.**

13. Revisión semanal con las métricas del punto 9. No cambiar parámetros a mitad de muestra.
14. Mantener congelado lo accesorio: chat, tipsters, dato del día, Stripe y moneyline.
15. **Decisión del 31-dic con preguntas medibles:**
    - ¿La versión nueva mejora el log-loss del mercado de forma significativa en las líneas analizadas?
    - ¿El CLV medio frente al cierre de Pinnacle es positivo?
    - ¿Bet365 se aparta del precio justo lo bastante como para que la calculadora encuentre valor con frecuencia?

    Qué hacer según las respuestas:
    - Si la respuesta es "no" a las tres, herramienta personal y portafolio.
    - Si solo la tercera es "sí", lanzar como comparador con precio justo, sin vender veredictos.
    - Si las dos primeras son "sí", hay base para hablar de modelo.

---

## 6. Anexo: método

Todo se calculó con Python del `venv` (pandas y statsmodels), leyendo sin escribir nada en el repo:

1. **Partidos y estadísticas.** Cargué `backtest_cache/bdl/stats_2024_*.json`, `stats_2025_*.json` y `games_2025.json` con `scripts.backtest.to_rows`, `to_games` y `Season`.
2. **Cuotas.** Recorrí `backtest_cache/odds/*_odds_date=*.json` y las pasé por `propdeep.clients.odds.parse_all_props`, que da todas las casas. La jornada de cada partido es la fecha de `commence_time` menos 12 h.
3. **Emparejamiento.** Por `strip_suffix(nombre)` y día; solo los jugadores con exactamente una fila (los que jugaron).
4. **Modelo.** Por jugador y partido: `season.history`, `compute_trends`, `season.context` (sin compañeros), `project` y `prob_over` en cada línea. Los bloqueos salen de `model._blocking_reason`.
5. **Línea principal.** Como producción: la de más casas y, a igualdad, la más equilibrada. Consenso = media de las probabilidades sin margen de las casas con esa línea. Mejor cuota = la máxima de cada lado.
6. **Beneficio por apuesta.** Cuota − 1 si se acierta y −1 si se falla; no hay empujes. IC = media ± 1,96 · desviación típica / √n.
7. **Regresión.** `statsmodels.Logit` y `GLM Binomial` con offset para el walk-forward mensual.
8. **Datos reales.** `propdeep.db` abierta con `sqlite3` en modo `ro`. El peso implícito de cada predicción es (p_final − p_mercado) / (p_modelo − p_mercado).

Para repetirlo bastaría un script en `scripts/` con estos pasos. No lo he añadido porque la auditoría no debía tocar código.
