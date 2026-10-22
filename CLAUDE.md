# CLAUDE.md — PropDeep

## 1. Qué es el proyecto
- Web en español de análisis estadístico de player props de la NBA para apostadores hispanohablantes (España y Latinoamérica).
- Cada análisis da tendencias, matchup, factores situacionales, comparación con la línea del mercado y nivel de confianza.
- Es una herramienta de información orientativa (estilo Rotobot), NUNCA de "picks seguros".
- Ahora mismo (oct-2026) lo usa solo el autor, en local, para validarlo antes de venderlo.

## 2. Stack y arquitectura
- Backend: Python + FastAPI (repo `Gonzatwk/propdeep-backend`). App en `main.py` (`app`). Base de datos con SQLAlchemy: SQLite en local (`propdeep.db`), Postgres si se despliega.
- Frontend: React 19 + Vite + React Router en `web/` del mismo repo. Estilos en `web/src/index.css` y fuentes autoalojadas con `@fontsource`. Publicado en Cloudflare Pages (https://propdeep.pages.dev). Ya no se usa Lovable.
- Comunicación: la web llama a la API por HTTP usando `VITE_API_URL`; el backend permite el origen con `CORS_ORIGINS`.
- Datos: API de Balldontlie (estadísticas, partidos, lesiones) y The Odds API (cuotas).
- Textos de los informes y chat: API de Claude (Anthropic). Si falla o no hay clave, se usa una plantilla.

### Mapa de carpetas
```
main.py                 API FastAPI: todos los endpoints y la configuración de CORS
propdeep.bat            arranque con doble clic en Windows (backend + web + navegador)
Procfile                arranque en Railway: uvicorn main:app
requirements.txt        dependencias del backend
requirements-dev.txt    + pytest, pandas, statsmodels (tests y scripts de análisis)
.env.example            plantilla de variables de entorno (copiar a .env)
BACKEND.md              guía del backend: despliegue, Stripe, uso en local
PRODUCT.md              dirección de producto y diseño
propdeep/
  config.py             Settings leídos del entorno (get_settings())
  clients/balldontlie.py  cliente Balldontlie (reintento ante 429 y caché)
  clients/odds.py       cliente The Odds API (props y moneyline)
  model.py              modelo: tendencias, proyección, probabilidad, quitar margen, análisis
  pipeline.py           Analyzer: junta datos, contexto, lesiones y llama a model.analyze; scan_day
  narrative.py          informe redactado por Claude o plantilla
  db.py                 tabla Prediction, publicar con hash, historial
  track_record.py       liquidar predicciones y resumen de rendimiento
  board.py              zona de partidos (modo análisis y muro de pago)
  auto.py               jornada automática (AUTO_JORNADA)
  picks.py              "Mis picks" y combinadas (inmutables)
  paper.py              "Paper bets": bank simulado en euros
  moneyline.py          cuotas a ganador
  chat.py               chat "Pregunta a PropDeep"
  tipsters.py           auditoría de tipsters (privada hasta TIPSTERS_PUBLIC=true)
  accounts.py, billing.py, mailer.py  cuentas, Stripe y correo de acceso
scripts/                utilidades por línea de comandos (ver sección 3)
tests/                  pytest; tests/fakes.py simula las APIs (los tests no llaman a nada real)
web/
  src/pages/            Home, MisPicks, PaperBets, Tipsters, legales y zona/ (Partidos, Partido,
                        Informe, Proyecciones, Chat, Cuenta, Entrar, DatoDelDia)
  src/components/       piezas de la interfaz
  src/lib/              lógica de cliente (sesión, tablero, combinada, paper...)
  src/data/             datos de demo e informes de ejemplo
  src/config.js         valores por defecto de la web (API_URL, contacto, titular)
  functions/api/avisame.js  lista de espera en Cloudflare KV (sin backend)
.claude/skills/, .impeccable/  skills y notas de diseño para Claude Code
```
No versionados (`.gitignore`): `.env`, `*.db`, `backtest_cache/`, `backtest_out/`.

## 3. Cómo arrancarlo
Entorno del autor: Windows con cmd. El repo está en `%USERPROFILE%\propdeep-backend` y el venv dentro, en `venv\` (o `.venv\`).

Instalación (una vez), desde la carpeta del repo:
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
```
Luego rellenar las claves en `.env`. Para la web: `cd web` y `npm install`.

Arranque:
- Rápido: doble clic en `propdeep.bat`. Abre el backend (`uvicorn main:app`), la web (`npm run dev`) y http://localhost:5173/partidos. Crea `web\.env.local` con `VITE_API_URL=http://localhost:8000` si no existe.
- Backend a mano: `venv\Scripts\activate` y `uvicorn main:app --reload` (http://localhost:8000).
- Web a mano: `cd web`, `npm run dev` (http://localhost:5173).
- Build de la web: `cd web` y `npm run build` (salida `dist`). Lint de la web: `npm run lint` (oxlint).

Tests (con el venv activado): `pytest`. Todos deben pasar antes de cada commit.

Scripts (con el venv activado, desde la raíz):
- `python -m scripts.picks_hoy AAAA-MM-DD [--regions eu] [--casas bet365,williamhill] [--peso 0.2] [--max-events N] [--out archivo.csv]`: jornada en CSV con la mejor cuota. No usarlo con `AUTO_JORNADA=1`: paga las cuotas dos veces.
- `python -m scripts.revision_jornada AAAA-MM-DD [--out archivo.csv]`: proyección frente a resultado de una jornada jugada.
- `python -m scripts.backtest [--temporada 2025] [--lineas proxy|odds-api] [--desde AAAA-MM-DD] [--hasta AAAA-MM-DD] [--stats pts,reb,ast,fg3m] [--regiones us] [--minutos-antes 60] [--max-creditos N] [--estimar] [--todas-casas] [--sin-companeros] [--cache backtest_cache] [--salida backtest_out]`. Usar siempre `--estimar` o `--max-creditos` antes de gastar créditos de The Odds API.
- `python -m scripts.analisis_peso backtest_out\odds-api-casas\lineas.csv`: compara pesos del modelo.
- `python -m scripts.analisis_companeros backtest_out\odds-api-casas\lineas.csv [--peso 0.2] [--ventaja 0.03]`.
- `python -m scripts.informes_ejemplo AAAA-MM-DD [--max-events 3] [--out web/src/data/informes_ejemplo.json] [--regions eu]`.

## 4. Flujo de datos
1. Balldontlie (`propdeep/clients/balldontlie.py`): `/players`, `/stats`, `/games`, `/games/{id}`, `/player_injuries`, con reintento y caché ante el 429.
2. The Odds API (`propdeep/clients/odds.py`): mercados `player_points`, `player_rebounds`, `player_assists`, `player_threes` (y moneyline), cuotas decimales, regiones de `ODDS_REGIONS` (por defecto `eu`).
3. `pipeline.Analyzer.analyze_prop` reúne historial, minutos, rival, pista, traspasos y lesiones, y llama a `model.analyze`.
4. Probabilidad (todo en `propdeep/model.py`):
   - `project()`: proyección con ajuste de minutos y contexto (topes `MAX_MINUTES_ADJ`, `MAX_CONTEXT_ADJ`).
   - `prob_over()`: P(más) con binomial negativa (Poisson si no hay sobredispersión).
   - `devig()`: probabilidad del mercado sin margen.
   - `analyze()`: `p_final = MODEL_WEIGHT * p_modelo + (1 - MODEL_WEIGHT) * p_mercado`. Hoy `MODEL_WEIGHT=0.2` (20 % modelo, 80 % mercado), no 50/50.
5. Ventaja = `p_final` frente a la probabilidad CON margen (`1/cuota`). Si no llega a `MIN_EDGE` (0,03 = 3 pp) o hay bloqueo, queda "sin ventaja".
6. Bloqueos (`_blocking_reason`): jugador Out/Doubtful, menos de 5 partidos, menos de 3 partidos de la temporada actual, o traspasado con menos de 5 partidos en su equipo nuevo.
7. Ajuste "compañero fuera": existe, pero apagado (`TEAMMATE_ADJUST=0`); solo es informativo.
8. Claude redacta el informe usando solo los números calculados (`narrative.py`).
9. Las predicciones se guardan con hash SHA-256 en un historial inmutable (`db.py`), también las "sin ventaja".
10. Con `AUTO_JORNADA=1` (`auto.py`), cada `AUTO_EVERY_MINUTES` (20) se liquida lo terminado y se analiza una vez cada partido que empieza en menos de `AUTO_HOURS_BEFORE` (10) horas.

### Qué manda hoy: umbral de 3 pp frente a modo análisis
- El umbral `MIN_EDGE` decide el veredicto INTERNO (más/menos o "sin ventaja"). Ese veredicto se guarda en el historial para seguir midiendo el modelo y sale en `picks_hoy` para el autor.
- La zona de partidos (`board.py`) está en modo análisis: enseña proyección, % sobre la línea, desgloses y cuotas de cada casa, pero NUNCA un más/menos como recomendación. El veredicto no sale de la API pública.
- No mezclar los dos: no exponer el veredicto al usuario sin decisión expresa del autor.

## 5. Partes críticas
- `propdeep/model.py`: proyección, probabilidad, quitar margen, mezcla con el mercado y bloqueos.
- Emparejar líneas con jugador, partido y rival (`pipeline.py`). Ya hubo un bug con traspasos: partido o rival del equipo anterior.
- Filtros de lesiones y de mínimo de partidos.
- Historial inmutable y cálculo del rendimiento (`db.py`, `track_record.py`): debe ser verificable. No editar predicciones publicadas.
- "Mis picks" (`picks.py`, inmutable) y "Paper bets" (`paper.py`, bank simulado en €, stake sugerido 2 %).
- Consumo de créditos de The Odds API (~8 créditos por partido; plan de 20.000/mes).

## 6. Convenciones
- Todo lo que ve el usuario, en español. También los comentarios, docstrings y mensajes de commit.
- Python: `from __future__ import annotations`, anotaciones de tipo, `dataclass` para estructuras, docstring de módulo que explique el porqué. Constantes del modelo en MAYÚSCULAS al inicio de `model.py`. Sin linter ni formateador configurado para Python: imitar el código que haya alrededor.
- Web: componentes `.jsx` con nombres en español, lógica en `src/lib/`, lint con oxlint.
- Tests: cada cambio de lógica lleva su test en `tests/`, usando `tests/fakes.py` en vez de APIs reales.
- Configuración centralizada en `propdeep/config.py` (`get_settings()`); defaults de la web en `web/src/config.js`. Una variable nueva va también en `.env.example`.
- Endpoints: públicos `/board`, `/board/games/{id}`, `/board/top`, `/board/lines/{id}`, `/picks`, `/tipsters`, `/waitlist`, `/chat`, `/auth/*`, `/me`. Admin con cabecera `x-admin-token` (`/admin/*`, p. ej. `POST /admin/board`). Picks y paper bets solo para correos de `ADMIN_EMAILS`.
- La web NO usa cookies ni servicios o fuentes de terceros. La sesión va en `localStorage`. Existe la página legal de privacidad y cookies (`Cookies.jsx`, `Privacidad.jsx`) porque la ley la pide, pero solo explica que no hay cookies: no añadas ninguna sin decisión del autor.
- Diseño: llamativo, blanco y negro con campo de tiros dorado; nada de fondo oscuro con neón ni estética de plantilla.

## 7. Variables de entorno
Backend (ver `.env.example`):
- `BALLDONTLIE_API_KEY`: clave de Balldontlie.
- `ODDS_API_KEY`: clave de The Odds API.
- `ODDS_REGIONS`: regiones de cuotas (por defecto `eu`).
- `ANTHROPIC_API_KEY` (o `ANTHROPIC_AUTH_TOKEN`): informes y chat. `ANTHROPIC_MODEL`: modelo de los informes.
- `DATABASE_URL`: por defecto `sqlite:///./propdeep.db`.
- `NBA_SEASON`: formato Balldontlie, 2026 = 2026-27.
- `MIN_EDGE` (0.03) y `MODEL_WEIGHT` (0.2): umbral de ventaja y peso del modelo.
- `TEAMMATE_ADJUST`: ajuste por compañero fuera (0 = apagado).
- `ADMIN_TOKEN`: acceso a `/admin/*`. `ADMIN_EMAILS`: correos que publican picks y usan paper bets.
- `CORS_ORIGINS`, `WEB_URL`: orígenes permitidos y dirección de la web.
- `LOCAL_LOGIN`: entrar sin correo (solo con `WEB_URL` en localhost y para `ADMIN_EMAILS`).
- `AUTO_JORNADA`, `AUTO_HOURS_BEFORE`, `AUTO_EVERY_MINUTES`: jornada automática.
- `FREE_LINES_PER_DAY`: líneas gratis por jornada.
- `CHAT_MESSAGES_PER_DAY` (plan Pro), `CHAT_MESSAGES_PER_DAY_BASIC` (resto), `CHAT_EFFORT`, `CHAT_MODEL`: chat.
- Stripe: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_MONTHLY`, `STRIPE_PRICE_YEARLY`, `STRIPE_PRICE_PRO` (25 €/mes), `STRIPE_PRICE_PASS` (pase de 7 días, 5 €). Vacíos = no se ofrecen.
- `TIPSTERS_PUBLIC`: enseña la auditoría de tipsters en la web.
- Correo: `RESEND_API_KEY` (preferido; Railway Hobby bloquea el SMTP) o `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`; `MAIL_FROM`. Sin ninguno, el enlace de acceso sale en el log.

Web (`web/.env.local` o el hosting):
- `VITE_API_URL`: URL del backend. Vacía = datos de demo de `src/data/`.
- `VITE_CONTACT_EMAIL`: correo de contacto.

## 8. Decisiones de producto
- Es análisis estadístico: nunca "pick seguro" ni "ganancia garantizada". El backtest de 2025-26 dio −2,8 % de ROI, sin ventaja.
- Historial de TODAS las predicciones, ganadas y perdidas.
- Juego responsable visible y solo para mayores de 18.
- Sin afiliación ni patrocinios de casas de apuestas (Ley 13/2011, RD 958/2020).
- RGPD básico, sin datos innecesarios.
- Negocio futuro: suscripción de 15 €/mes o 120 €/año con 7 días gratis, plan Pro de 25 €/mes, pase de 7 días a 5 € y freemium de ~3 líneas al día. Preventa de 9 € eliminada.
- Subida anunciada en la web: el mensual pasa a 19 € el 1-ene-2027 (`SUBIDA` en `web/src/lib/zona.js`). Hay que cumplirla o quitar el aviso.
- Desde el 21-oct-2026: primero uso personal en local; el lanzamiento comercial está aplazado.
- Código del lanzamiento: TODO está ya en main. Lo básico (cuentas por enlace, Stripe mensual/anual con prueba de 7 días, muro freemium, chat) llegó antes; el PR #16 (correo por Resend) y el PR #15 (plan Pro, pase de 7 días, subida a 19 €, pausa, correo del día 5, dato del día, auditoría de tipsters) se fusionaron el 22-oct-2026. No queda ningún PR abierto. Lo que falta no es código sino configuración: precios en Stripe, despliegue en Railway, dominio y Resend, webhook.
- Criterio de corte: tras 300 jugadas o el 31-dic-2026, ROI con la mejor cuota ≥ 0 → preparar el lanzamiento; negativo → herramienta personal y portafolio.
- Solo NBA; nada de fútbol ni tenis hasta tener suscriptores.
- Próximo en estudio: backtest de robos, tapones y PRA cuando se renueven los créditos.

## 9. Pendiente de revisar
- Umbral de ventaja casi inalcanzable. Con `MODEL_WEIGHT=0.2` y la ventaja medida frente a la probabilidad CON margen (`1/cuota`), el modelo tiene que separarse unos 28 pp del mercado para llegar a `MIN_EDGE=0.03`. Ejemplo con cuotas 1,90/1,90: mercado sin margen 50 %, con margen 52,6 % (el margen ya resta ~2,6 pp); hace falta `p_final` ≥ 55,6 %, es decir, `p_modelo` ≥ 78 %. En la práctica casi todo sale "sin ventaja". Hay que decidir si es intencionado (prudencia, dado que el backtest no mostró ventaja) o se ajusta (umbral, peso o medir frente a la probabilidad sin margen). No cambiarlo sin decisión del autor y sin backtest.

## 10. Reglas para Claude Code
- Antes de cambiar lógica de cálculo, escribe un test que cubra el comportamiento actual. `pytest` en verde antes de cada commit.
- Cambios pequeños, un commit por cambio lógico.
- No toques archivos `.env` ni subas claves ni datos personales.
- No gastes créditos de The Odds API sin avisar: estima primero.
- Si algo no está claro, pregunta antes de asumir.
- El autor trabaja en Windows/cmd: da los comandos exactos, paso a paso.
