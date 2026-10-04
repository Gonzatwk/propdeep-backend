# Backend de PropDeep

API en FastAPI que analiza player props de la NBA con datos reales y guarda un historial
público de todas las predicciones.

## Cómo funciona un análisis

1. **Datos del jugador** (Balldontlie): partidos de esta temporada y la anterior, solo los
   anteriores al partido analizado.
2. **Tendencias**: medias de los últimos 5, 10 y 20 partidos, de la temporada, minutos y
   porcentaje de veces que superó la línea.
3. **Contexto**: local o visitante, back-to-back, lesión, y en puntos cuánto concede el rival
   frente a la media de la liga (ajuste máximo del 5 %).
4. **Probabilidad**: distribución normal (Poisson en triples) alrededor de la proyección,
   mezclada al 50 % con la probabilidad del mercado sin margen (`MODEL_WEIGHT`).
5. **Ventaja**: probabilidad estimada menos la implícita en la cuota (con margen). Por debajo
   del 3 % (`MIN_EDGE`) el veredicto es "sin ventaja". Jugadores fuera, en duda o con menos de
   5 partidos nunca son jugada.
6. **Informe**: Claude redacta la explicación en español solo con esos números. Sin clave de
   Claude se usa una plantilla.

## Endpoints

| Método | Ruta | Qué hace |
| --- | --- | --- |
| GET | `/predictions` | Historial público completo |
| GET | `/track-record` | Acierto, beneficio en unidades y ROI, total y por confianza |
| POST | `/analyze` | Analiza una prop sin publicarla |
| POST | `/admin/publish` | Analiza y publica en el historial (cabecera `x-admin-token`) |
| GET | `/admin/scan?game_date=AAAA-MM-DD` | Analiza las props de la jornada con The Odds API |
| POST | `/admin/settle` | Liquida las pendientes con el resultado real |

Lo publicado no se edita: cada predicción guarda un hash SHA-256 de su contenido.

## En local

```bash
pip install -r requirements-dev.txt
cp .env.example .env   # y rellena las claves
pytest
uvicorn main:app --reload
python -m scripts.informes_ejemplo 2026-10-21
```

## Planes de las APIs

- **Balldontlie ALL-STAR** (9,99 $/mes): necesario para `/stats` y `/player_injuries`.
- **The Odds API**: cada partido cuesta (mercados × regiones) créditos; 4 mercados en `eu` = 4.
