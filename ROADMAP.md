# ROADMAP de PropDeep

Coordina Claude Code desde el 23-oct-2026, sobre el código real. Este archivo se actualiza al empezar y al terminar cada tarea.

- **Qué se construye:** [PLAN-PLATAFORMA.md](PLAN-PLATAFORMA.md).
- **Por qué:** [AUDIT.md](AUDIT.md).

**Estados:** HECHO · EN CURSO · PENDIENTE · BLOQUEADO (espera algo externo) · DECIDE EL AUTOR.
**Esfuerzo:** B = 1 día o menos · M = 2-4 días · A = 5 días o más.

**Cómo se trabaja**
- Una tarea = un commit con su test y `pytest` en verde, en una rama por bloque. El autor fusiona el PR.
- Lo que marca DECIDE EL AUTOR no se toca hasta que decida, y se le pregunta de una en una.
- Nada de gastar créditos de The Odds API sin estimarlos antes y avisar.

---

## Ahora mismo

| Siguiente | Estado |
|---|---|
| Bloque 0 en la rama `mvp/bloque-0` (un commit por tarea) | EN CURSO |

## Fechas clave

| Fecha | Qué | Estado |
|---|---|---|
| ~10-dic-2026 | Fin estimado del MVP (6-7 semanas desde el 24-oct) | PENDIENTE |
| 2.ª quincena de diciembre | Recordar al autor la subida a 19 € | YA NO HACE FALTA: el aviso se quitó el 24-oct (0.10) |
| 31-dic-2026 | Criterio de corte del modelo. Ver D3: con el nuevo enfoque hay que redefinirlo | DECIDE EL AUTOR |
| 1-ene-2027 | Subida del mensual a 19 €: aviso quitado de la web (0.10), no hay nada que cumplir | HECHO |

## Decisiones pendientes del autor

| ID | Decisión | Recomendación | Estado |
|---|---|---|---|
| D1 | Restaurar CLAUDE.md. La copia de trabajo solo tiene cambios de formato de un editor de markdown, y las barras que mete estropean los comandos (`venv\\Scripts\\activate`, `VITE\_API\_URL`) | Volver a la versión de `main` (`git checkout -- CLAUDE.md`). El nuevo enfoque se escribirá en la tarea 0.12 | HECHO (23-oct) |
| D2 | Commitear AUDIT.md, PLAN-PLATAFORMA.md y ROADMAP.md. Y qué hacer con `instrucciones-proyecto.md` (tiene datos personales) y `revision_2026-10-21.csv` | Los tres documentos van en la rama `docs/auditoria-plan-roadmap`; los otros dos, a `.gitignore` | HECHO (PR #22 fusionado) |
| D3 | ¿Sigue valiendo el criterio de corte del 31-dic (300 jugadas con ROI ≥ 0) con el enfoque de plataforma? | Redefinirlo con log-loss frente al mercado y acierto frente a la probabilidad dicha (AUDIT §1, §3.9) | DECIDE EL AUTOR |
| D4 | Proveedor de cuotas de casas españolas y latinoamericanas | El autor lo busca con los requisitos de PLAN-PLATAFORMA §4. Bloquea la fase 2.1 | BLOQUEADO |
| D5 | Consulta legal y comprobar si Stripe admite el negocio | Antes de cobrar | PENDIENTE |

## Hecho

| Fecha | Qué |
|---|---|
| 23-oct-2026 | AUDIT.md: auditoría completa (modelo, código, seguridad, producto) |
| 23-oct-2026 | Decisión de enfoque: plataforma al estilo de RotoBot; nota y probabilidad, sin "EDGE" y sin cuotas en el generador |
| 23-oct-2026 | PLAN-PLATAFORMA.md: plan del MVP y de la fase 2, con los cambios respecto al encargo del coordinador anterior |
| 23-oct-2026 | ROADMAP.md creado. Claude Code pasa a coordinar |

---

## MVP

### Bloque 0: Base (4-5 días)

| ID | Tarea | Origen | Esfuerzo | Estado |
|---|---|---|---|---|
| 0.1 | Cerrar `POST /analyze` (solo admin) y cambiar su test | AUDIT S1 | B | HECHO (aa3c6a6) |
| 0.2 | Quitar `/board/top` y la página Proyecciones (la sustituye el feed) | AUDIT S2 | B | HECHO (43e4628) |
| 0.3 | Guardar versión y parámetros del modelo en cada predicción (también en el hash). Marcar las del 21-oct como configuración antigua sin editarlas | AUDIT C2, M3 | B | HECHO (ea81bf9) |
| 0.4 | Liquidación robusta: no anular si el boxscore viene vacío, `try` por partido y anulación manual de las predicciones sin `game_id`. Con tests | AUDIT C3, C4 | M | HECHO (1d2e43d) |
| 0.5 | Corregir `--todas-casas` (todas las casas por línea), repetir el backtest `--sin-companeros` desde la caché y luego `analisis_peso` | AUDIT C1, M2 | B | HECHO (6a0388c) |
| 0.6 | Jornada automática: volver a los partidos publicados a medias y no repetir sin fin los que no tienen líneas | AUDIT C5 | M | HECHO |
| 0.7 | Alias de nombres (Herb Jones, Bones Hyland, Moe Wagner…) | AUDIT C6 | B | HECHO |
| 0.8 | Errores registrados y `KeyError` de datos externos controlados en `scan_day` y en la liquidación | AUDIT C7 | B | HECHO |
| 0.9 | Umbrales "X+" y líneas enteras bien tratados en `prob_over` | AUDIT M10 | B | HECHO |
| 0.10 | Textos de la web: fuera "20 de octubre", las promesas no cubiertas y el aviso de subida | AUDIT S5, S6 | B | HECHO |
| 0.11 | Avisos: +18, juego responsable (jugarbien.es, RGIAJ) y "no es consejo de apuestas" | PLAN §5 | B | PENDIENTE |
| 0.12 | CLAUDE.md con el nuevo enfoque: feed con nota, sin "EDGE", coordinación y ROADMAP | PLAN §0 | B | PENDIENTE |

### Bloque 1: Motor de probabilidad (4-5 días)

| ID | Tarea | Esfuerzo | Estado |
|---|---|---|---|
| 1.1 | Precio justo por línea: consenso sin margen, o Pinnacle si está | B | PENDIENTE |
| 1.2 | Calibración Platt mes a mes (α, β) con su script y tests | M | PENDIENTE |
| 1.3 | Distribución anclada al mercado para cualquier umbral | M | PENDIENTE |
| 1.4 | Validación en la caché (líneas principales y alternativas de Bovada y BetRivers). Informe con log-loss y fiabilidad | M | PENDIENTE |

### Bloque 2: Nota y feed de mejores jugadas (4 días)

| ID | Tarea | Esfuerzo | Estado |
|---|---|---|---|
| 2.1 | Fórmula de la nota de 0 a 100 y su validación por deciles en la caché | M | PENDIENTE |
| 2.2 | Feed en el backend: tarjetas con nota, probabilidad y razón; liquidación automática e historial | M | PENDIENTE |
| 2.3 | Feed en la web | B-M | PENDIENTE |

### Bloque 3: Tabla de props y fichas de jugador (6-7 días)

| ID | Tarea | Esfuerzo | Estado |
|---|---|---|---|
| 3.1 | Tabla de boxscores de todos los partidos, actualizada a diario (`/v1/stats`) | M | PENDIENTE |
| 3.2 | Defensa del rival por posición, ritmo y uso calculados | M | PENDIENTE |
| 3.3 | Endpoint de la ficha de jugador | B | PENDIENTE |
| 3.4 | Tabla de props en la web (como "Explore Props") | M | PENDIENTE |
| 3.5 | Ficha en la web: gráfico partido a partido, splits, minutos y con/sin compañeros | M | PENDIENTE |

### Bloque 4: Creador de combinadas (6-7 días)

| ID | Tarea | Esfuerzo | Estado |
|---|---|---|---|
| 4.1 | Tabla de correlaciones con los boxscores de la caché, y su validación con los meses no usados | M | PENDIENTE |
| 4.2 | Generador en el backend: patas, nivel de riesgo, mismo partido, probabilidad de la combinada | M-A | PENDIENTE |
| 4.3 | Pantalla al estilo de RotoBot, sin cuotas; guardar en Mis picks | M | PENDIENTE |

### Bloque 5: Corrector de boletos por captura (4-5 días)

| ID | Tarea | Esfuerzo | Estado |
|---|---|---|---|
| 5.1 | Claude con visión: de la captura a las patas en JSON | M | PENDIENTE |
| 5.2 | Emparejar con nuestras líneas; nota y probabilidad de cada pata y de la combinada | M | PENDIENTE |
| 5.3 | Subida en la web; la imagen no se guarda | B | PENDIENTE |
| 5.4 | Guardar por dentro, anónimas, las cuotas españolas leídas | B | PENDIENTE |

## Fase 2 (después del MVP)

| ID | Tarea | Esfuerzo | Estado |
|---|---|---|---|
| F2.1 | Integrar el proveedor de casas españolas y latinoamericanas; enseñar la cuota si conviene | M-A | BLOQUEADO (D4) |
| F2.2 | Más mercados: PRA, robos, tapones e hitos. Validarlos antes con aperturas de Balldontlie GOAT o ~12.000 créditos | M | PENDIENTE |
| F2.3 | Estadísticas avanzadas de GOAT en la ficha (tracking, tipos de jugada) | M | PENDIENTE |
| F2.4 | Compañero fuera como ajuste del modelo, validado con datos de producción | M | PENDIENTE |
| F2.5 | Lanzamiento: Stripe (idempotencia, `DELETE /me` con pausa, correo del día 5), `LOCAL_LOGIN`, límites por IP, despliegue | M | PENDIENTE (después de D5) |
| F2.6 | Historial público verificable y CLV frente al cierre de Pinnacle (~900-1.800 créditos al mes) | M | PENDIENTE |
| F2.7 | Chat conectado al generador y adaptación por país de Latinoamérica | M | PENDIENTE |

## Congelado (no se toca salvo que lo pida el autor)

Chat (salvo F2.7), auditoría de tipsters, dato del día, moneyline, Stripe y cuentas (hasta F2.5), correo del día 5 y paper bets.

## Registro

| Fecha | Cambio |
|---|---|
| 23-oct-2026 | ROADMAP creado a partir de AUDIT.md y PLAN-PLATAFORMA.md |
| 23-oct-2026 | D1 hecho: CLAUDE.md devuelto a la versión de `main`. D2: rama `docs/auditoria-plan-roadmap` con los tres documentos y `.gitignore` |
| 24-oct-2026 | PR #22 fusionado. Bloque 0 empezado en `mvp/bloque-0` |
| 24-oct-2026 | 0.1: `/analyze` pasa a `/admin/analyze` |
| 24-oct-2026 | 0.2: fuera `/board/top` y la página Proyecciones (redirige a `/partidos`) |
| 24-oct-2026 | 0.3: `model_version` en cada predicción y dentro del hash; `db.verify()` (las 513 actuales verifican); resumen por versión |
| 24-oct-2026 | 0.4: liquidación sin anulaciones falsas (boxscore vacío), aplazados y predicciones sin partido se anulan, un partido que falla no frena al resto |
| 24-oct-2026 | 0.5: backtest con todas las casas y `--solo-cache`. Repetido sin compañeros (0 créditos): 584 jugadas, ROI +1,8 % (IC −5,7 % a +9,6 %). Con hasta 8 casas por línea, `analisis_peso` da un peso del modelo de 0,06-0,08 y ninguna regla con el IC por encima de 0. El peso no se toca ahora: lo sustituye la calibración del bloque 1 |
| 24-oct-2026 | 0.6: la jornada automática apunta cada petición de cuotas (`event_scans`). Un partido sin líneas o con mercados sin colgar se repasa a 3 h y a 1 h del inicio (máximo 3 peticiones, no una cada 20 min); un partido que falla no frena a los demás |
| 24-oct-2026 | 0.7: alias de 7 apodos sacados de la caché (Ace Bailey, Herb Jones, Bones Hyland…); `find_player` busca por el apellido sin sufijo ("Jaren Jackson Jr." ya no busca "Jr."); el backtest usa los mismos alias |
| 24-oct-2026 | 0.8: cuotas rotas de The Odds API se saltan sin tumbar el partido; un fallo inesperado en una prop no corta la jornada; los errores que antes se tragaban ahora quedan en el log |
| 24-oct-2026 | 0.9: líneas enteras sin contar el empuje como "menos" (`prob_push`) y `prob_at_least` para los hitos "X+". Las líneas ,5 dan exactamente lo mismo que antes (test fijado) |
| 24-oct-2026 | 0.10: fuera los "20 de octubre" (la web dice que está en pruebas privadas), las promesas que el modelo no cumple (ritmo, posición, viajes, paliza) y el aviso de subida a 19 €. Al hacer el feed (2.3) habrá que cambiar la pregunta "¿Me vais a decir a qué apostar?" |
