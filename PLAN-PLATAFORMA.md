# PropDeep plataforma: plan (23 de octubre de 2026)

Plan para convertir PropDeep en una plataforma de props NBA en español, para España y Latinoamérica, al estilo de RotoBot. Es solo plan: no cambia código. Se apoya en [AUDIT.md](AUDIT.md).

Cómo leerlo:
- **Esfuerzo:** B = 1 día o menos, M = 2-4 días, A = 5 días o más. Son días de trabajo con Claude Code.
- **[Hecho]**: comprobado. **[Hipótesis]**: por validar.

## 0. Decisiones del autor (23-oct) que fija este plan

1. **Copiar la estructura y el aspecto de RotoBot.** Entran en el MVP el creador de combinadas, el feed de mejores jugadas, el corrector de boletos por captura, la tabla de props y las fichas de jugador.
2. **Cada pata y cada tarjeta enseñan una nota de 0 a 100 y una probabilidad estimada.** No se usan las palabras "EDGE" ni "ventaja", y no se compara con la cuota de ninguna casa.
3. **No se enseñan cuotas en el generador:** el usuario las ve en su casa. Las casas españolas tienen cuotas más bajas que las de EE. UU., así que un "edge frente a la cuota" casi nunca saldría y espantaría.
4. **Por dentro, las patas se eligen por precio frente al consenso y por correlación**, no solo por tendencias. El usuario no ve ese cálculo.

### Cambios respecto al encargo del coordinador

El autor revisó el encargo con Claude Code el 23-oct. Quería copiar RotoBot sin añadidos. Acordamos copiar su experiencia y mantener por dentro el precio y las correlaciones, que es lo que puede hacer que las combinadas salgan mejor. Esto cambia respecto a lo pedido:

| El coordinador pidió | Decisión final | Por qué |
|---|---|---|
| Feed diario con "EDGE" | Feed de "Mejores jugadas" con **nota de 0 a 100 y probabilidad estimada**. Sin las palabras "EDGE" ni "ventaja" | 1) Las casas españolas y latinoamericanas pagan menos que las de EE. UU.: un edge honesto casi nunca saldría y espantaría a los clientes. 2) El "edge" de RotoBot (modelo contra línea) es la señal que perdió un 3,6 % en nuestro backtest. 3) Anunciar una ventaja que los datos no sostienen es publicidad engañosa |
| Que el generador enseñe la probabilidad real de la combinada frente a la cuota ofrecida | Enseña la **probabilidad estimada de cada pata y de la combinada**, pero **ninguna cuota ni comparación con cuotas** | Así lo quiere el autor, para que la experiencia sea como la de RotoBot. Además, las cuotas españolas no las tenemos y las de EE. UU. confundirían |
| Priorizar patas con edge de precio y tener en cuenta las correlaciones | **Se mantiene, pero solo por dentro**: el usuario no ve el cálculo | Es lo único con ventaja demostrada (AUDIT §3.6), y las correlaciones cambian la probabilidad de la combinada |
| "Qué edge mínimo mostraríamos" | **No se enseña ninguno.** En el feed entra lo que tiene nota ≥ 60 y p_est ≥ p_mercado. Por dentro, "valor alto" = EV ≥ 3 % frente al consenso | Coherente con lo anterior |
| Modelo calibrado con peso ~0,08 | Igual: calibración Platt sobre el precio justo (β ≈ 0,07) | Lo que dicen los datos (AUDIT §3.2) |
| Estadísticas (fichas, defensa por posición, ritmo, uso…) | Igual, y además una **tabla de props** como "Explore Props" de RotoBot | Copiar a RotoBot |
| *(no estaba)* | **Nuevo: corrector de boletos por captura**, también de RotoBot | Da nota a los boletos de Bet365 y Codere y, de paso, guarda por dentro las cuotas españolas, que hoy no tenemos |
| Proveedor de casas españolas | Sin cambios (punto 4). El MVP no depende de él | — |

**[Hecho]** Qué hace RotoBot, según su web y su ficha en las tiendas:
- **Combinadas:** el usuario elige deporte, número de patas y nivel de riesgo. Cada pata trae línea, mejor cuota (casas de EE. UU.), una frase de razón y un "edge" de modelo contra mercado. No consta que enseñe la probabilidad total de la combinada.
- **Otras herramientas:** tarjetas "Insights" que se liquidan solas, una tabla de props con nota y % de acierto, fichas de jugador, chat, "Sharp Board" y corrector de boletos por captura.
- **Avisos:** +18 y "no ofrece consejo de apuestas".
- **Resultados:** no publica sus aciertos.

Nos separamos de RotoBot en una cosa: su "edge" de modelo contra línea es la señal que en nuestro backtest perdió un 3,6 % (AUDIT §3.4). Por eso aquí es una nota.

**Hay que cambiar el CLAUDE.md:** "modo análisis, nunca un más/menos como recomendación" pasa a "feed con nota y lado". Así lo decide el autor.

---

## 1. Estadísticas: qué falta y de dónde sale

**[Hecho]** Según la documentación de Balldontlie:
- **ALL-STAR** (9,99 $/mes, el plan que pide el código): `/v1/players` (con `position`), `/v1/games`, `/v1/stats` (boxscore por jugador) y `/v1/player_injuries`.
- **GOAT** (39,99 $/mes) añade:
  - estadísticas avanzadas (`/nba/v1/stats/advanced` y `/nba/v2/stats/advanced`, con `pace` y `usage_percentage`);
  - medias de temporada por categoría, incluida la del rival (`/nba/v1/team_season_averages/general?type=opponent`);
  - clasificación (`/v1/standings`);
  - cuotas de props de casas de EE. UU. (`/v2/odds/player_props`, **sin bet365**);
  - líneas de apertura de props de la última temporada (`/nba/v2/odds/player_props/opening`).

| Funcionalidad | ¿Hay datos? | Endpoint | Plan | Esfuerzo | Nota |
|---|---|---|---|---|---|
| Ficha de jugador con gráfico partido a partido frente a la línea | Sí | `/v1/stats` (ya se usa) | ALL-STAR | M | `compute_trends` ya da medias y % de acierto |
| % de acierto L5, L10, L20 y temporada frente a la línea | Sí | `/v1/stats` | ALL-STAR | B | Ya calculado en `model.compute_trends`; falta enseñarlo |
| Splits casa/fuera y contra el rival | Sí | `/v1/stats` | ALL-STAR | B | Ya calculado en `model.compute_splits` |
| Minutos: tendencia, estabilidad y rol | Sí | `/v1/stats` (`min`) | ALL-STAR | B | Desviación de minutos de los últimos 10 |
| Defensa del rival por posición (lo que concede a G, F y C en pts, reb, ast y triples frente a la media de la liga) | Sí, calculándolo | `/v1/stats` de todos los partidos + `position` de `/v1/players` | ALL-STAR | M | Falta una tabla con todos los boxscores, actualizada a diario. La posición de Balldontlie es gruesa (G, F, C, G-F, F-C) |
| Ritmo (posesiones por partido) | Sí, calculado o directo | Calculado: posesiones ≈ FGA − OREB + TOV + 0,44·FTA con totales de `/v1/stats`. Directo: `pace` en `/stats/advanced` | ALL-STAR (calculado) o GOAT | B-M | La estimación es estándar y suficiente |
| Uso (USG%) | Sí, calculado o directo | Fórmula de USG% con los totales del equipo de `/v1/stats`, o `usage_percentage` | ALL-STAR o GOAT | B-M | |
| Efecto de bajas de compañeros (media con y sin X) | Sí | `/v1/stats` + `/v1/player_injuries` | ALL-STAR | B (enseñarlo) | Ya calculado en `model.teammate_out_factor`. Como ajuste del modelo sigue apagado hasta validarlo sin fugas (AUDIT M8) |
| Back-to-back y descanso | Sí | `/v1/games` | ALL-STAR | B | El back-to-back ya existe; faltan los días de descanso |
| Lesiones | Sí | `/v1/player_injuries` | ALL-STAR | B | Ya existe |
| Clasificación | Sí | `/v1/standings`, o calculada con `/v1/games` | GOAT o ALL-STAR | B | |
| Tracking, hustle y tipos de jugada (toques, penetraciones, asistencias potenciales) | Solo GOAT | `/nba/v1/season_averages/tracking`, `/playtype`, `/hustle` | GOAT | M | Fase 2 |
| Quintetos | Poco útil | `/v1/lineups` (solo con el partido empezado) | GOAT | — | No antes del partido |
| Props de PRA, robos, tapones e hitos "X+" | Sí, de casas de EE. UU. | The Odds API (créditos) o `/v2/odds/player_props` | Créditos o GOAT | M | Fase 2 |

**Recomendación:**
- Con ALL-STAR se puede hacer todo el MVP calculando ritmo, uso y defensa por posición a partir de los boxscores.
- GOAT solo compensa en la fase 2, o para validar rebotes, asistencias y triples con sus líneas de apertura de 2025-26. Es más barato que los créditos históricos de The Odds API, pero son líneas de apertura, no de cierre.

---

## 2. Probabilidad estimada y nota (el feed)

### 2.1 Probabilidad estimada (lo que ve el usuario)
1. **Precio justo del mercado.** Es la probabilidad sin margen media de las casas que ofrecen esa línea, o la de Pinnacle si la trae. **[Hecho]** En la noche del 21-oct, Pinnacle estaba en 313 de 513 líneas.
2. **Inclinación del modelo, calibrada con Platt:**
   `logit(p_est) = α + logit(p_mercado) + β · (logit(p_modelo) − logit(p_mercado))`
   - α y β se ajustan mes a mes en la caché, usando solo meses anteriores.
   - **[Hecho]** Hoy salen β ≈ 0,07 y α ≈ −0,03 (un leve sesgo hacia el menos).
   - Se probará una calibración isotónica como alternativa. Gana la que tenga mejor log-loss en las dos mitades de la temporada.
3. **Distribución anclada al mercado, para cualquier umbral.** Hace falta para hitos tipo "25+ puntos" de "Crea tu apuesta".
   - Se usa una binomial negativa cuya media se ajusta para que P(X > línea principal) = p_est.
   - La dispersión es la del modelo × ~1,12 (AUDIT M4).
   - Con eso, P(X ≥ k) para cualquier k. Ojo: "25+" equivale a "más de 24,5" (AUDIT M10).
4. **Qué saldrá:**
   - **[Hecho]** En la línea principal casi todo saldrá entre el 45 % y el 58 %.
   - **[Hipótesis]** Los umbrales por debajo de la línea darán un 70-90 %.
   - Son cifras honestas. Para patas "seguras" se usan umbrales más bajos, como hace "Crea tu apuesta".

### 2.2 Nota de 0 a 100 (ordena el feed y el generador)
| Componente | Peso inicial | Qué mide |
|---|---|---|
| Valor | 40 % | p_est − p_mercado del lado, más una señal interna de precio: cuota de alguna casa ≥ 3 % por encima del consenso de las demás, lo único que ganó en AUDIT §3.6. Esa señal viene de casas de EE. UU. y no se enseña |
| Forma | 25 % | % de acierto L5, L10 y temporada frente a la línea, y tendencia |
| Matchup | 20 % | Defensa del rival por posición, ritmo esperado y back-to-back |
| Fiabilidad | 15 % | Partidos jugados, estabilidad de minutos y lesiones (también de compañeros) |

**Reglas:**
- **No se enseña nunca el lado que la probabilidad calibrada ve peor que el mercado**: solo lados con p_est ≥ p_mercado.
- En el feed solo entra lo que tenga una nota ≥ 60. Los bloqueos actuales se mantienen: lesión, muestra corta, menos de 3 partidos de temporada y traspaso reciente.
- **Ventaja mínima:** no se enseña ninguna. Por dentro, una pata es de "valor alto" si su EV frente al consenso es ≥ 3 %.
- **Validación sin créditos:** se ordenan las líneas de la caché por nota en deciles y se mira si la nota alta acierta más de lo que dice el precio justo, en las dos mitades de la temporada.
  - Si forma y matchup no aportan (**[Hipótesis]**: es lo probable según AUDIT §3.5), su peso pasa a valor y fiabilidad.
  - Seguirán apareciendo en pantalla como razones de la pata, pero no puntuarán.

### 2.3 Mejoras del modelo que son realistas
| Mejora | Valor esperado | Esfuerzo | Cómo validarla sin créditos |
|---|---|---|---|
| Calibración (Platt o isotónica) y anclaje al mercado | Alto: probabilidades honestas | B | Mes a mes en la caché de puntos: log-loss, Brier y fiabilidad |
| Más varianza (× 1,12 más la incertidumbre de la proyección) | Medio | B | Igual |
| Distribución anclada para umbrales alternativos | Alto: hace falta para las combinadas | M | **[Hecho]** La caché trae líneas alternativas de Bovada (95.000 filas) y BetRivers (36.000). Se compara nuestra P(X ≥ k) con el resultado y con su probabilidad sin margen |
| Factor del rival para rebotes, asistencias y triples, por posición | Incierto | M | Solo hay cuotas reales de puntos. Para las otras tres hay que usar los datos de producción desde el 21-oct (unas 500 líneas por noche) o las aperturas de GOAT |
| Compañero fuera usando el parte de lesiones (no "no jugó") | Incierto | M | Solo con datos de producción: el backtest tiene la fuga (AUDIT M8) |
| Proyección de minutos × producción por minuto | Bajo-medio | M | Caché de puntos |
| **No es realista** | — | — | Batir el cierre solo con estadísticas públicas, y los modelos grandes de machine learning con esta cantidad de datos |

**Reglas de validación:**
- Una mejora solo entra si mejora el log-loss frente al mercado **en las dos mitades** de la temporada.
- Se apunta antes de mirar el resultado.
- Se guarda la versión en cada predicción (AUDIT C2).

### 2.4 Resultados de la validación (24-oct-2026)

Datos: caché del backtest de 2025-26, solo puntos, 8 casas de EE. UU., cuotas 60 min antes. Se reproducen con `python -m scripts.calibracion` y `python -m scripts.calibracion --alternativas` (0 créditos).

**Líneas principales.** 17.549 líneas. Cada mes se ajusta solo con los meses anteriores y se mide el log-loss (menos es mejor):

| Probabilidad | Total (n = 13.023) | 1.ª mitad | 2.ª mitad |
|---|---|---|---|
| Mercado (consenso sin margen) | 0,69190 | 0,69174 | 0,69207 |
| **Estimada (Platt)** | **0,69156** | **0,69104** | 0,69212 |
| Mezcla actual al 20 % | 0,69225 | 0,69142 | 0,69314 |

- **[Hecho]** Parámetros con toda la temporada: α = −0,0315 (leve sesgo hacia el menos) y β = 0,0623. Ya están en `propdeep/fair.py`.
- **[Hecho]** Está calibrada: dice 48,0 % y pasa el 47,6 %; dice 51,4 % y pasa el 51,5 %.
- **[Hecho]** Gana al mercado por muy poco, con mejora en la 1.ª mitad y empate en la 2.ª. La mezcla al 20 % de hoy es peor que el mercado solo.
- **[Opinión]** En la práctica, la probabilidad estimada es la del mercado con una inclinación honesta: no esconde una ventaja.

**Líneas alternativas (distribución anclada).** 112.886 cuotas de 15.767 jugador-partido; casi todas de Bovada y BetRivers.

| Probabilidad en la línea alternativa | Log-loss | 1.ª mitad | 2.ª mitad |
|---|---|---|---|
| La propia casa, sin margen | 0,66460 | 0,66435 | 0,66488 |
| Anclada, desviación × 1,00 | 0,66345 | 0,66376 | 0,66312 |
| **Anclada, desviación × 1,06 (elegida)** | **0,66337** | **0,66371** | **0,66301** |
| Anclada, desviación × 1,12 | 0,66344 | 0,66381 | 0,66306 |

Por distancia a la línea principal:

| Línea alternativa | n | Anclada dice | Pasa | La casa dice |
|---|---|---|---|---|
| 2,5 a 5,5 puntos por debajo | 10.592 | 66,6 % | 66,9 % | 66,6 % |
| 0,5 a 2,5 por debajo | 42.879 | 56,9 % | 57,2 % | 57,4 % |
| 0,5 a 2,5 por encima | 43.598 | 41,4 % | 40,9 % | 42,9 % |
| 2,5 a 5,5 por encima | 15.687 | 32,0 % | 29,7 % | 33,6 % |

- **[Hecho]** La distribución anclada da la probabilidad de cualquier umbral ("20+", "más de 25,5") mejor que las propias casas, en las dos mitades. El generador de combinadas puede calcular las patas "X+" sin pagar los mercados alternativos.
- **[Hecho]** Los "más" en líneas por encima de la principal salen caros en las casas: dicen un 33,6 % y pasa el 29,7 %. Por debajo de la principal, la casa acierta.
- **[Opinión]** El generador no debe proponer "más" en umbrales altos. Las patas conservadoras (umbrales bajos) no están mal pagadas.
- **Límites:** solo puntos, casas de EE. UU. y foto a 60 min. Para rebotes, asistencias y triples se usa lo mismo hasta tener datos. Desde el 24-oct cada línea publicada guarda su estimación (`analysis.estimate`) para poder validarlo con datos reales.

---

## 3. Creador de combinadas (al estilo de RotoBot)

### 3.1 Qué ve el usuario
- **Qué elige:**
  - número de patas (2-6);
  - nivel de riesgo: Conservador, Equilibrado o Arriesgado;
  - toda la jornada o uno o varios partidos;
  - un jugador fijo, si quiere;
  - "Mismo partido", que es lo de "Crea tu apuesta".
- **Qué recibe:**
  - cada pata con jugador, mercado y línea o umbral ("Más de 22,5 puntos" o "25+ puntos"), **nota**, **probabilidad estimada** y una frase de razón;
  - la **probabilidad estimada de la combinada**;
  - botones para cambiar una pata, regenerar y guardar en Mis picks, donde se liquida sola.
  - **Sin cuotas.**

### 3.2 Cómo se eligen las patas (no se ve)
1. **Candidatas:** todas las (jugador, estadística, umbral, lado) del día con su p_est y su nota. Entran los umbrales alternativos de la distribución anclada.
2. **Franja según el riesgo** **[Hipótesis]**, por ajustar:
   - Conservador: p_est ≥ 0,70 en cada pata, 2-3 patas.
   - Equilibrado: 0,55-0,75.
   - Arriesgado: líneas principales y más patas.
3. **Búsqueda voraz o por haz:**
   - Maximiza la nota media, con prioridad a las patas de "valor alto".
   - Límites: una pata por jugador y estadística y un máximo de patas por partido.
   - No junta patas con correlación negativa fuerte (ρ < −0,15).
   - En "Mismo partido" permite las correlaciones positivas.
4. **Probabilidad de la combinada:**
   - De partidos distintos: el producto.
   - Del mismo partido: cópula gaussiana con la ρ de la tabla y 10.000 simulaciones.

### 3.3 Cómo medir las correlaciones con lo que ya tenemos
- **[Hecho] Datos:** la caché tiene los boxscores completos de 2024-25 y 2025-26 (≈ 92.000 filas jugador-partido) con pts, reb, ast, triples, minutos, equipo y partido.
- **Método:**
  - Para cada jugador-partido, el residuo z = (real − proyección) / desviación, con la proyección de `model.project` usando solo partidos anteriores.
  - Se estima ρ por tipo de pareja:
    - **mismo jugador:** pts-ast, pts-reb, pts-triples, reb-ast;
    - **compañeros:** por rol (titular/suplente, tramos de minutos) y por posición;
    - **rivales del mismo partido.**
  - Se encoge hacia 0 cuando hay poca muestra.
  - Se añade un factor de partido: el ritmo y el total de puntos se mueven juntos.
- **Validación:**
  - Se usan los meses que no se usaron para estimar.
  - Se cogen parejas reales de líneas principales de puntos del mismo partido, que están en la caché con cuotas.
  - Se compara la probabilidad conjunta estimada con la frecuencia real. Se mide con Brier frente a suponerlas independientes.
- **Esfuerzo:** M para la tabla de correlaciones y su validación; A para el generador entero con la web.

### 3.4 Corrector de boletos por captura
- **Cómo funciona:**
  1. El usuario sube la foto de su boleto o de su "Crea tu apuesta" (Bet365, Codere…).
  2. Claude, con visión, devuelve las patas en JSON.
  3. Se emparejan con nuestras líneas: nombres con alias (AUDIT C6), estadística y umbral.
- **Qué enseña:** nota y probabilidad de cada pata, la probabilidad de la combinada con las correlaciones, la pata más floja y una sugerencia para cambiarla.
- **Privacidad:** la imagen no se guarda.
- **Ventaja extra:** las cuotas que se leen del boleto **sí se guardan por dentro, anónimas**. Son la única forma barata de saber cuánto margen ponen las casas españolas y si alguna se aparta del consenso, la pregunta abierta de AUDIT §3.6. No se enseñan.
- **Coste:** una llamada a Claude por imagen, con límite diario por plan.
- **Esfuerzo:** M-A.

---

## 4. Qué pedir a un proveedor con casas españolas y latinoamericanas

**[Hecho]** The Odds API no trae props de casas españolas: en la región `eu` solo sale Pinnacle. Balldontlie tiene bet365 en cuotas de partido, pero **no en props**. Además, el "bet365" de los feeds de EE. UU. es la casa de EE. UU., no bet365.es.

**Requisitos imprescindibles**
1. **Casas por jurisdicción, explícitas:**
   - España: bet365.es, Codere.es, Sportium, Bwin.es, William Hill.es, Betfair.es, Luckia, Retabet, Kirolbet, Marca Apuestas.
   - Latinoamérica: Codere (México, Colombia, Argentina), Caliente, Betano, bet365 (por país), Betsson, Wplay, BetPlay, Rushbet.
   - Tiene que poner "bet365.es", no solo "bet365".
2. **Mercados NBA de jugador:** puntos, rebotes, asistencias, triples, combinados (PRA, P+R, P+A) e **hitos "X+"**, que son los de "Crea tu apuesta". Muy deseable: el precio de combinadas del mismo partido. Casi nadie lo tiene.
3. **Datos:** cuotas decimales con **fecha y hora de cada precio**, actualizadas cada 5-15 minutos antes del partido, en una API REST/JSON con identificadores estables de partido y jugador o nombres fáciles de normalizar.
4. **Histórico:** al menos la temporada pasada, o desde que se contrata, para validar y medir CLV.
5. **Licencia que permita el uso comercial** dentro de una web de pago, aunque no enseñemos la cuota. Que no sea scraping: incumple las condiciones de las casas y es un riesgo legal.
6. **Precio, límites de llamadas, prueba gratuita y soporte.**

**Nombres a mirar** (**[Hipótesis]**: no he comprobado que cubran props de casas españolas): OpticOdds, OddsJam API, SportsGameOdds, odds-api.io y BetsAPI. Antes de pagar, pide siempre una muestra de un partido NBA con props de bet365.es y Codere.

---

## 5. Arreglos de AUDIT.md que siguen haciendo falta

| ID | Qué | Por qué sigue haciendo falta | Esfuerzo | Fase |
|---|---|---|---|---|
| S1 | Cerrar `POST /analyze` (solo admin) | Gasta Claude y Balldontlie sin límite | B | MVP, día 1 |
| S2 | Quitar `/board/top` y su `direction` | Lo sustituye el feed, que tiene su propia lógica | B | MVP |
| C2 | Versión y parámetros en cada predicción | El feed y las combinadas se liquidan solos; sin versión no se puede medir | B | MVP |
| C3, C4 | Liquidación: no anular si el boxscore viene vacío, `try` por partido, anulación manual de lo que no tiene `game_id` | Las tarjetas, las combinadas y Mis picks dependen de ella | M | MVP |
| C1, M2 | Corregir `--todas-casas` y repetir el backtest sin compañeros | La calibración necesita el consenso de todas las casas | B | MVP |
| C5 | La jornada automática debe volver a los partidos publicados a medias | El feed necesita la jornada completa | M | MVP |
| C6 | Alias de nombres | Emparejar líneas y leer boletos | B | MVP |
| C7 | Errores registrados y `KeyError` controlados en `scan_day` | Que un fallo no corte la jornada | B | MVP |
| M10 | Líneas enteras e hitos "X+" bien tratados | Los umbrales del generador | B | MVP |
| S5, S6 | Textos: fuera "20 de octubre", y la portada debe describir el producto nuevo. Lo de "ritmo" y "posición" pasa a ser verdad cuando se haga el punto 1 | Publicidad que no engañe | B | MVP |
| — | CLAUDE.md: nuevo enfoque, feed con nota, sin "EDGE" | Que el código y las reglas no se contradigan | B | MVP |
| Legal | Avisos de +18, juego responsable (jugarbien.es, RGIAJ) y "no es consejo de apuestas", como RotoBot. Sin "EDGE", "pick seguro" ni "ganancia" | Ley de Competencia Desleal y consumo; Ley 13/2011 | B | MVP |
| S3 | Stripe: idempotencia, `DELETE /me` con la suscripción en pausa, correo del día 5 | Antes de cobrar | M | Lanzamiento |
| S4 | `LOCAL_LOGIN`, límites por IP, CORS | Antes de desplegar | B-M | Lanzamiento |
| Legal | Consulta con un abogado (España y cada país de Latinoamérica). **[Hipótesis]** Comprobar si Stripe admite el negocio: creo que tiene la "predicción deportiva" en su lista restringida | Antes de cobrar | — | Lanzamiento |
| S7, S8 | Historial verificable (hashes publicados fuera) | Credibilidad | B | Fase 2 |

---

## 6. MVP y fase 2

### MVP: unas 6-7 semanas de trabajo (≈ 29-34 días)

| # | Bloque | Qué incluye | Esfuerzo |
|---|---|---|---|
| 0 | Base | S1, S2, C2, C3-C4, C1 con el backtest repetido, C5-C7, M10, textos S5-S6, avisos legales y CLAUDE.md | 4-5 días |
| 1 | Motor de probabilidad | Precio justo (consenso o Pinnacle), calibración Platt mes a mes (α, β), distribución anclada para cualquier umbral, script de validación sobre la caché (líneas principales y alternativas de Bovada y BetRivers) | 4-5 días |
| 2 | Nota y feed de mejores jugadas | Fórmula de la nota y su validación por deciles; tarjetas con nota, probabilidad y razón, que se liquidan solas, con su historial | 4 días |
| 3 | Tabla de props y fichas de jugador | Boxscores de todos los partidos en una tabla diaria; defensa por posición, ritmo y uso calculados; tabla tipo "Explore Props"; ficha con gráfico partido a partido, splits, minutos y con/sin compañeros | 6-7 días |
| 4 | Creador de combinadas | Tabla de correlaciones con la caché y su validación; generador por nivel de riesgo; pantalla al estilo de RotoBot, sin cuotas | 6-7 días |
| 5 | Corrector de boletos | Captura → Claude con visión → patas → nota y probabilidad de cada pata y de la combinada; guarda las cuotas españolas por dentro | 4-5 días |

- **Créditos de The Odds API en el MVP:** ninguno extra. Producción sigue con ~8 por partido.
- **Balldontlie:** basta ALL-STAR.
- **Claude:** las razones de cada pata se pueden hacer con plantilla. Claude solo hace falta en el corrector de boletos.

### Fase 2 (después del MVP, por orden)
1. **Proveedor con casas españolas y latinoamericanas** (punto 4): integrarlo y, si conviene, enseñar la cuota de cada pata. Esfuerzo M-A, según la API.
2. **Más mercados:** PRA, robos, tapones e hitos, con Balldontlie GOAT o créditos de The Odds API. Antes, su validación (aperturas de GOAT o ~12.000 créditos). Esfuerzo M.
3. **Estadísticas avanzadas de GOAT:** tracking, tipos de jugada y hustle en la ficha. Esfuerzo M.
4. **Compañero fuera como ajuste del modelo,** validado con los datos de producción. Esfuerzo M.
5. **Lanzamiento:** S3, S4, consulta legal, revisión de Stripe, dominio y despliegue. Esfuerzo M.
6. **Historial público verificable** (S7, S8) y medición de CLV con el cierre de Pinnacle (~900-1.800 créditos al mes). Esfuerzo M.
7. **Chat conectado al generador** ("hazme una combinada de 3 con Doncic") y adaptación por país de Latinoamérica. Esfuerzo M.

### Qué medimos aunque no se enseñe
Aunque la web no hable de ventaja, por dentro se sigue midiendo, para no engañarnos:
- el log-loss de p_est frente al mercado;
- el acierto de las tarjetas frente a la probabilidad que dijimos;
- y, cuando haya cuotas españolas por el corrector o por un proveedor, el margen real de esas casas.

Todo con la versión del modelo guardada.
