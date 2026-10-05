import { ArrowRight, CalendarBlank, ChartLineUp, Clock, Crosshair, Scales, ShieldCheck, Thermometer, UsersThree } from '@phosphor-icons/react'
import { Link } from 'react-router-dom'
import Cta from '../components/Cta'
import EdgeCalculator from '../components/EdgeCalculator'
import { CONTACT_EMAIL } from '../config'
import { FECHA_EJEMPLOS, informesLanding } from '../data/informes'
import { fmtNum, fmtPct } from '../format'

const preguntas = [
  [ChartLineUp, 'Tendencias', 'Últimos 5, 10 y 20 partidos, minutos y uso. ¿El jugador está por encima o por debajo de su media?'],
  [Crosshair, 'Matchup', 'Cómo defiende el rival esa estadística y en qué posición. Ritmo de juego esperado.'],
  [UsersThree, 'Factores situacionales', 'Back-to-back, viajes, bajas del equipo y del rival, riesgo de paliza.'],
  [Scales, 'Línea del mercado', 'Nuestra probabilidad estimada frente a la que implica la cuota. La diferencia es la ventaja, si existe.'],
  [Thermometer, 'Nivel de confianza', 'Alto, medio o bajo, explicado en una frase. Sin ventaja, el análisis lo dice.'],
]

const faqs = [
  ['¿Me vais a decir a qué apostar?', 'No. Te damos un análisis estadístico y nuestra estimación de probabilidad. La decisión y el riesgo son tuyos.'],
  ['¿Garantizáis ganancias?', 'No, y desconfía de quien lo haga. Apostar siempre implica riesgo de perder dinero. Por eso publicamos todo el historial.'],
  ['¿Qué props cubrís?', 'Puntos, rebotes, asistencias y triples de los partidos de la NBA, empezando por los de más interés cada día.'],
  ['¿Cuándo se publican los análisis?', 'Antes de cada jornada, a una hora cómoda para España y Latinoamérica.'],
  ['¿Trabajáis con casas de apuestas?', 'No. No tenemos afiliación ni patrocinio de ningún operador.'],
  ['¿Cómo funciona el reembolso?', 'Si el primer mes no te convence, nos escribes y te devolvemos los 9 €. Sin preguntas.'],
]

const anatomia = ['Jugador y partido', 'Prop y línea', 'Cuota', 'Probabilidad implícita', 'Probabilidad estimada', 'Ventaja', 'Confianza', 'Tres razones']

function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div aria-hidden className="pointer-events-none absolute -top-40 right-[-10%] size-[42rem] rounded-full bg-[radial-gradient(closest-side,var(--accent-soft),transparent)]" />
      <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-4 pt-12 pb-20 sm:px-6 md:pt-20 lg:grid-cols-[1.1fr_0.9fr] lg:gap-16 lg:pb-28">
        <div>
          <h1 className="rise text-[2.6rem] leading-[1.02] font-semibold tracking-[-0.035em] sm:text-6xl">
            Player props de la NBA, con números y no con corazonadas.
          </h1>
          <p className="rise mt-6 max-w-[34rem] text-lg leading-relaxed text-muted" style={{ '--i': 1 }}>
            Análisis estadístico en español de cada prop: tendencias, matchup, contexto y comparación con la línea del mercado. Y cuando no hay ventaja, te lo decimos.
          </p>
          <div className="rise mt-9 flex flex-wrap items-center gap-x-6 gap-y-4" style={{ '--i': 2 }}>
            <Cta>Reservar por 9 €</Cta>
            <a href="#ejemplos" className="group inline-flex items-center gap-1.5 font-medium">
              Ver un informe de ejemplo
              <ArrowRight aria-hidden className="size-4 transition-transform duration-200 group-hover:translate-x-0.5" />
            </a>
          </div>
          <p className="rise mt-5 text-sm text-muted" style={{ '--i': 3 }}>
            Reembolso completo si no te convence. Solo mayores de 18 años.
          </p>
        </div>
        <div className="rise" style={{ '--i': 2 }}>
          <EdgeCalculator />
        </div>
      </div>
    </section>
  )
}

function ComoFunciona() {
  return (
    <section id="como-funciona" className="border-t border-line">
      <div className="mx-auto grid max-w-6xl gap-12 px-4 py-20 sm:px-6 md:py-28 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20">
        <div className="lg:sticky lg:top-28 lg:self-start">
          <h2 className="text-3xl font-semibold tracking-[-0.03em] sm:text-[2.6rem] sm:leading-[1.08]">
            Cinco preguntas antes de cada prop
          </h2>
          <p className="mt-5 max-w-sm text-lg leading-relaxed text-muted">
            Todo en español y explicado, para que entiendas el porqué y decidas tú.
          </p>
        </div>
        <ul className="grid gap-x-10 gap-y-10 sm:grid-cols-2">
          {preguntas.map(([Icono, titulo, texto], i) => (
            <li key={titulo} className={i === preguntas.length - 1 ? 'sm:col-span-2 sm:max-w-md' : ''}>
              <Icono aria-hidden weight="duotone" className="size-7 text-accent" />
              <h3 className="mt-4 text-lg font-semibold">{titulo}</h3>
              <p className="mt-2 leading-relaxed text-muted">{texto}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

function SinVentaja() {
  return (
    <section className="bg-surface">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 md:py-28">
        <h2 className="max-w-4xl text-4xl font-semibold tracking-[-0.04em] sm:text-6xl sm:leading-[1.02]">
          Sin ventaja, <span className="text-accent">no hay jugada.</span>
        </h2>
        <p className="mt-8 max-w-2xl text-lg leading-relaxed text-muted">
          La mayoría de servicios te dan picks todos los días, haya valor o no. Nosotros comparamos nuestra probabilidad con
          la de la cuota, y si la diferencia no compensa, lo decimos claramente: "sin ventaja". Algunos días habrá pocas
          jugadas, y eso también es información.
        </p>
        <div className="mt-14 grid gap-px overflow-hidden rounded-2xl border border-line bg-line md:grid-cols-3">
          {[
            'Probabilidades, no promesas.',
            'Todas las predicciones publicadas, las ganadas y las perdidas.',
            'Hecho por un apostador que aplica el mismo criterio con su propio dinero.',
          ].map((t) => (
            <p key={t} className="bg-surface p-6 text-[1.05rem] font-medium leading-snug">{t}</p>
          ))}
        </div>
      </div>
    </section>
  )
}

function Dato({ label, value }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="tnum mt-0.5 font-mono font-semibold">{value}</dd>
    </div>
  )
}

function TarjetaInforme({ informe }) {
  const ventaja = informe.probEstimada - informe.probImplicita
  return (
    <article className="flex flex-col rounded-3xl border border-line bg-surface p-6">
      <p className="text-sm text-muted">{informe.tipo}</p>
      <h3 className="mt-3 text-xl font-semibold">{informe.jugador}</h3>
      <p className="text-sm text-muted">{informe.partido}</p>
      <p className="mt-3 font-semibold text-accent">{informe.prop}</p>
      <dl className="mt-5 grid grid-cols-2 gap-4 text-sm">
        <Dato label="Cuota" value={fmtNum(informe.cuota)} />
        <Dato label="Prob. implícita" value={fmtPct(informe.probImplicita)} />
        <Dato label="Prob. estimada" value={fmtPct(informe.probEstimada)} />
        <Dato label="Ventaja" value={fmtPct(ventaja)} />
        <Dato label="Confianza" value={informe.confianza} />
        <Dato label="Veredicto" value={informe.veredicto} />
      </dl>
      <ul className="mt-5 list-disc space-y-1 pl-5 text-sm leading-relaxed text-muted">
        {informe.porque.map((p) => <li key={p}>{p}</li>)}
      </ul>
      {informe.informe && (
        <details className="mt-5 text-sm">
          <summary className="cursor-pointer font-semibold text-accent">Leer el informe completo</summary>
          <p className="mt-2 whitespace-pre-line leading-relaxed text-muted">{informe.informe}</p>
        </details>
      )}
    </article>
  )
}

function EjemplosPendientes() {
  return (
    <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
      <div className="rounded-3xl border border-line bg-surface p-7 sm:p-9">
        <CalendarBlank aria-hidden weight="duotone" className="size-8 text-accent" />
        <p className="mt-5 text-2xl font-semibold tracking-tight">Llegan el 20 de octubre</p>
        <p className="mt-3 max-w-md leading-relaxed text-muted">
          Los publicaremos con datos reales del primer día de la temporada regular. Aquí no inventamos ejemplos.
        </p>
        <p className="mt-8 text-sm font-medium">Cada informe incluye:</p>
        <ul className="mt-3 flex flex-wrap gap-2">
          {anatomia.map((a) => (
            <li key={a} className="rounded-full border border-line px-3 py-1 text-sm text-muted">{a}</li>
          ))}
        </ul>
      </div>
      <ul className="grid gap-4">
        {informesLanding.map((inf) => (
          <li key={inf.tipo} className="flex items-center justify-between gap-4 rounded-2xl border border-dashed border-line px-5 py-4">
            <span className="font-medium">{inf.tipo}</span>
            <Clock aria-label="En preparación" className="size-5 shrink-0 text-muted" />
          </li>
        ))}
      </ul>
    </div>
  )
}

function Ejemplos() {
  const reales = informesLanding.filter((i) => !i.pendiente)
  return (
    <section id="ejemplos" className="border-t border-line">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 md:py-28">
        <h2 className="text-3xl font-semibold tracking-[-0.03em] sm:text-[2.6rem]">Así es un análisis de PropDeep</h2>
        <p className="mt-5 mb-12 max-w-2xl text-lg leading-relaxed text-muted">
          Tres ejemplos reales{FECHA_EJEMPLOS ? ` con datos del ${new Date(FECHA_EJEMPLOS).toLocaleDateString('es-ES')}` : ''}:
          uno con ventaja, uno sin ventaja y uno con confianza baja, para que veas cómo razonamos en cada caso.
        </p>
        {reales.length ? (
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {reales.map((inf) => <TarjetaInforme key={inf.tipo} informe={inf} />)}
          </div>
        ) : (
          <EjemplosPendientes />
        )}
      </div>
    </section>
  )
}

function Historial() {
  return (
    <section className="border-t border-line">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-20 sm:px-6 md:py-28 lg:grid-cols-2 lg:gap-20">
        <div>
          <h2 className="text-3xl font-semibold tracking-[-0.03em] sm:text-[2.6rem]">Nuestro historial, a la vista</h2>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted">
            Publicamos cada análisis antes del partido, con su fecha y hora, y no se edita después. Cuando termina el
            partido marcamos el resultado, gane o pierda.
          </p>
          <Link to="/historial" className="btn btn-ghost mt-8 px-5 py-3">
            Ver historial completo <ArrowRight aria-hidden className="size-4" />
          </Link>
        </div>
        <div className="rounded-3xl border border-line p-7">
          <div className="flex items-center gap-3 text-sm text-muted">
            <ShieldCheck aria-hidden weight="duotone" className="size-5 text-accent" />
            Empieza con el primer partido de la temporada 2026-27
          </div>
          <dl className="mt-6 grid grid-cols-2 gap-x-6 gap-y-7">
            {['Análisis publicados', 'Porcentaje de acierto', 'Rendimiento a 1 unidad fija', 'Rendimiento por confianza'].map((m) => (
              <div key={m}>
                <dt className="text-sm text-muted">{m}</dt>
                <dd className="tnum mt-1 font-mono text-2xl font-semibold text-muted/70">-</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </section>
  )
}

function Precio() {
  return (
    <section id="precio" className="bg-surface">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 md:py-28">
        <h2 className="max-w-2xl text-3xl font-semibold tracking-[-0.03em] sm:text-[2.6rem] sm:leading-[1.08]">
          Reserva tu plaza para el inicio de la temporada
        </h2>
        <div className="mt-12 grid gap-5 lg:grid-cols-[1.25fr_1fr]">
          <div className="relative overflow-hidden rounded-3xl bg-bg p-8 shadow-[var(--shadow)] ring-1 ring-accent/50 sm:p-10">
            <div aria-hidden className="pointer-events-none absolute -right-24 -bottom-24 size-80 rounded-full bg-[radial-gradient(closest-side,var(--accent-soft),transparent)]" />
            <p className="font-semibold text-accent">Preventa de fundadores</p>
            <p className="mt-4 flex items-baseline gap-3">
              <span className="tnum text-6xl font-semibold tracking-[-0.04em]">9 €</span>
              <span className="text-muted">el primer mes</span>
            </p>
            <p className="mt-5 max-w-md leading-relaxed text-muted">
              Acceso desde el primer partido de la temporada. Reembolso completo si no te convence.
            </p>
            <Cta className="mt-8">Reservar por 9 €</Cta>
          </div>
          <dl className="grid gap-px self-start overflow-hidden rounded-3xl border border-line bg-line">
            <div className="bg-surface p-7">
              <dt className="text-sm text-muted">Mensual, después del primer mes</dt>
              <dd className="mt-2"><span className="tnum text-3xl font-semibold">15 €</span> <span className="text-muted">/mes</span></dd>
              <dd className="mt-1 text-sm text-muted">Cancelas cuando quieras.</dd>
            </div>
            <div className="bg-surface p-7">
              <dt className="text-sm text-muted">Anual</dt>
              <dd className="mt-2"><span className="tnum text-3xl font-semibold">120 €</span> <span className="text-muted">/año</span></dd>
              <dd className="mt-1 text-sm text-muted">Equivale a 10 € al mes.</dd>
            </div>
          </dl>
        </div>
        <p className="mt-8 max-w-3xl text-sm leading-relaxed text-muted">
          Pago seguro con Stripe. Puedes cancelar en cualquier momento desde tu cuenta. Si el primer mes no te convence,
          escríbenos a <a className="underline hover:text-ink" href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a> y te devolvemos los 9 €.
        </p>
      </div>
    </section>
  )
}

function Faq() {
  return (
    <section id="faq" className="border-t border-line">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 md:py-28">
        <h2 className="text-3xl font-semibold tracking-[-0.03em] sm:text-[2.6rem]">Preguntas frecuentes</h2>
        <dl className="mt-12 grid gap-x-16 gap-y-10 md:grid-cols-2">
          {faqs.map(([q, a]) => (
            <div key={q}>
              <dt className="text-lg font-semibold">{q}</dt>
              <dd className="mt-2 max-w-[60ch] leading-relaxed text-muted">{a}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}

export default function Home() {
  return (
    <>
      <Hero />
      <ComoFunciona />
      <SinVentaja />
      <Ejemplos />
      <Historial />
      <Precio />
      <Faq />
    </>
  )
}
