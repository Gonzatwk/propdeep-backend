import { ArrowDown, ArrowRight } from '@phosphor-icons/react'
import { Link } from 'react-router-dom'
import Court, { Leyenda } from '../components/Court'
import Cta from '../components/Cta'
import LaLinea from '../components/LaLinea'
import { CONTACT_EMAIL } from '../config'
import { FECHA_EJEMPLOS, informesLanding } from '../data/informes'
import { hexPoints } from '../lib/hex'
import { fmtNum, fmtPct } from '../format'

const preguntas = [
  ['Tendencias', 'Últimos 5, 10 y 20 partidos, minutos y uso. ¿El jugador está por encima o por debajo de su media?'],
  ['Matchup', 'Cómo defiende el rival esa estadística y en qué posición. Ritmo de juego esperado.'],
  ['Contexto', 'Back-to-back, viajes, bajas del equipo y del rival, riesgo de paliza.'],
  ['Línea del mercado', 'Nuestra probabilidad estimada frente a la que implica la cuota. La diferencia es la ventaja, si existe.'],
  ['Confianza', 'Alta, media o baja, explicada en una frase. Sin ventaja, el análisis lo dice.'],
]

const faqs = [
  ['¿Me vais a decir a qué apostar?', 'No. Te damos un análisis estadístico y nuestra estimación de probabilidad. La decisión y el riesgo son tuyos.'],
  ['¿Garantizáis ganancias?', 'No, y desconfía de quien lo haga. Apostar siempre implica riesgo de perder dinero. Por eso publicamos todo el historial.'],
  ['¿Qué props cubrís?', 'Puntos, rebotes, asistencias y triples de los partidos de la NBA, empezando por los de más interés cada día.'],
  ['¿Cuándo se publican los análisis?', 'Antes de cada jornada, a una hora cómoda para España y Latinoamérica.'],
  ['¿Trabajáis con casas de apuestas?', 'No. No tenemos afiliación ni patrocinio de ningún operador.'],
  ['¿Cómo funciona el reembolso?', 'Si el primer mes no te convence, nos escribes y te devolvemos los 9\u00a0€. Sin preguntas.'],
]

const anatomia = ['Jugador y partido', 'Prop y línea', 'Cuota', 'Probabilidad implícita', 'Probabilidad estimada', 'Ventaja', 'Confianza', 'Tres razones']

function Hero() {
  return (
    <section className="relative overflow-hidden">
      <Court className="pointer-events-none mx-auto block w-full max-w-[640px] lg:hidden" />
      <Court horizontal className="pointer-events-none absolute top-0 right-0 hidden h-full lg:block" />
      <div className="relative mx-auto max-w-6xl px-4 pb-16 sm:px-6 lg:flex lg:min-h-[min(calc(100svh-100px),780px)] lg:items-center lg:py-16">
        <div className="max-w-[40rem] max-lg:mt-2 max-lg:text-center xl:max-w-[44rem]">
          <h1 className="display rise text-[3.3rem] sm:text-[5rem] xl:text-[6rem]">
            Player props de la NBA, con números <span className="text-hot">y no con corazonadas.</span>
          </h1>
          <p className="rise mt-6 max-w-[34rem] text-lg leading-relaxed text-ink-2 max-lg:mx-auto" style={{ '--i': 1 }}>
            Análisis estadístico en español de cada prop: tendencias, matchup, contexto y comparación con la línea del mercado. Y cuando no hay ventaja, te lo decimos.
          </p>
          <div className="rise mt-9 flex flex-col items-center gap-4 sm:flex-row sm:gap-7 max-lg:justify-center" style={{ '--i': 2 }}>
            <Cta>Reservar por 9 €</Cta>
            <a href="#la-linea" className="group inline-flex items-center gap-1.5 font-semibold underline decoration-line underline-offset-4 hover:decoration-ink">
              Probar con un ejemplo
              <ArrowDown aria-hidden className="size-4 transition-transform duration-200 group-hover:translate-y-0.5" />
            </a>
          </div>
          <p className="rise mt-5 text-sm text-muted" style={{ '--i': 3 }}>
            Reembolso completo si no te convence. Solo mayores de 18 años.
          </p>
          <Leyenda className="rise mt-10 max-lg:justify-center" />
        </div>
      </div>
    </section>
  )
}

function Seccion({ id, titulo, children, className = '' }) {
  return (
    <section id={id} className={`border-t border-ink ${className}`}>
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 md:py-24">
        <h2 className="display text-[2.8rem] sm:text-[4rem]">{titulo}</h2>
        {children}
      </div>
    </section>
  )
}

function Linea() {
  return (
    <section id="la-linea" className="border-t border-ink">
      <div className="mx-auto max-w-6xl px-4 pt-16 pb-10 sm:px-6 md:pt-24">
        <h2 className="display max-w-[16ch] text-[2.8rem] sm:text-[4rem]">Mueve la línea y mira de qué lado cae</h2>
        <p className="mt-5 max-w-2xl text-lg leading-relaxed text-muted">
          Cada prop es una frontera. Rojo, los partidos por encima; azul, los de debajo. Si la cuota ya paga lo que dicen
          los números, no hay nada que ganar.
        </p>
      </div>
      <LaLinea />
    </section>
  )
}

function ComoFunciona() {
  return (
    <Seccion id="como-funciona" titulo="Cinco preguntas antes de cada prop">
      <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted">
        Todo en español y explicado, para que entiendas el porqué y decidas tú.
      </p>
      <dl className="mt-12 border-t border-line">
        {preguntas.map(([titulo, texto], i) => (
          <div key={titulo} className="grid gap-2 border-b border-line py-5 md:grid-cols-[18rem_1fr] md:gap-10 md:py-6">
            <dt className="flex items-center gap-3">
              <svg viewBox="0 0 20 22" className="h-[22px] w-5 shrink-0" aria-hidden>
                <polygon points={hexPoints(10, 11, 10)} fill={['var(--c2)', 'var(--c1)', 'var(--n0)', 'var(--h1)', 'var(--h3)'][i]} />
              </svg>
              <span className="display text-[1.9rem]">{titulo}</span>
            </dt>
            <dd className="max-w-[60ch] leading-relaxed text-muted md:pt-1">{texto}</dd>
          </div>
        ))}
      </dl>
    </Seccion>
  )
}

function SinVentaja() {
  return (
    <section className="bg-ink text-on-ink">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 md:py-28">
        <h2 className="display text-[3.6rem] sm:text-[6rem]">
          Sin ventaja, <span className="text-h2">no hay jugada.</span>
        </h2>
        <p className="mt-8 max-w-2xl text-lg leading-relaxed text-on-ink-muted">
          La mayoría de servicios te dan picks todos los días, haya valor o no. Nosotros comparamos nuestra probabilidad con
          la de la cuota, y si la diferencia no compensa, lo decimos claramente: "sin ventaja". Algunos días habrá pocas
          jugadas, y eso también es información.
        </p>
        <ul className="mt-14 grid gap-8 md:grid-cols-3 md:gap-10">
          {[
            'Probabilidades, no promesas.',
            'Todas las predicciones publicadas, las ganadas y las perdidas.',
            'Hecho por un apostador que aplica el mismo criterio con su propio dinero.',
          ].map((t) => (
            <li key={t} className="border-t border-on-ink-muted/40 pt-4 text-lg leading-snug font-medium">{t}</li>
          ))}
        </ul>
      </div>
    </section>
  )
}

function Dato({ label, value }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="tnum mt-0.5 font-semibold">{value}</dd>
    </div>
  )
}

function TarjetaInforme({ informe }) {
  const ventaja = informe.probEstimada - informe.probImplicita
  return (
    <article className="flex flex-col border border-ink bg-paper p-6">
      <p className="text-sm text-muted">{informe.tipo}</p>
      <h3 className="display mt-3 text-3xl">{informe.jugador}</h3>
      <p className="text-sm text-muted">{informe.partido}</p>
      <p className="mt-3 font-semibold text-hot">{informe.prop}</p>
      <dl className="mt-5 grid grid-cols-2 gap-4 border-t border-line pt-4 text-sm">
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
          <summary className="cursor-pointer font-semibold text-hot">Leer el informe completo</summary>
          <p className="mt-2 whitespace-pre-line leading-relaxed text-muted">{informe.informe}</p>
        </details>
      )}
    </article>
  )
}

// Hasta el 20 de octubre: la ficha en blanco de un informe, sin datos inventados.
function EjemplosPendientes() {
  return (
    <div className="grid gap-10 lg:grid-cols-[1fr_1.2fr] lg:gap-16">
      <div>
        <p className="display text-[2.2rem] text-hot">Llegan el 20 de octubre</p>
        <p className="mt-3 max-w-md leading-relaxed text-muted">
          Los publicaremos con datos reales del primer día de la temporada regular. Aquí no inventamos ejemplos.
        </p>
      </div>
      <div className="border border-ink bg-paper">
        <p className="border-b border-ink px-5 py-3 text-sm font-semibold">Ficha de cada informe</p>
        <dl className="grid sm:grid-cols-2">
          {anatomia.map((a, i) => (
            <div key={a} className={`flex items-baseline justify-between gap-4 border-line px-5 py-3.5 ${i < anatomia.length - 2 ? 'border-b' : 'max-sm:border-b max-sm:last:border-b-0'} ${i % 2 === 0 ? 'sm:border-r' : ''}`}>
              <dt className="text-sm">{a}</dt>
              <dd className="h-px w-12 shrink-0 self-end border-b border-dashed border-line" aria-label="Pendiente" />
            </div>
          ))}
        </dl>
      </div>
    </div>
  )
}

function Ejemplos() {
  const reales = informesLanding.filter((i) => !i.pendiente)
  return (
    <Seccion id="ejemplos" titulo="Así es un análisis de PropDeep">
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
    </Seccion>
  )
}

function Historial() {
  return (
    <Seccion titulo="Nuestro historial, a la vista">
      <div className="mt-5 grid gap-10 lg:grid-cols-[1fr_1.1fr] lg:gap-16">
        <div>
          <p className="max-w-xl text-lg leading-relaxed text-muted">
            Publicamos cada análisis antes del partido, con su fecha y hora, y no se edita después. Cuando termina el
            partido marcamos el resultado, gane o pierda. Empieza con el primer partido de la temporada 2026-27.
          </p>
          <Link to="/historial" className="btn btn-ghost mt-8 h-12 px-6 text-lg">
            Ver historial completo <ArrowRight aria-hidden className="size-4" />
          </Link>
        </div>
        <dl className="grid grid-cols-2 border-t border-l border-ink">
          {['Análisis publicados', 'Acierto', 'Beneficio a 1 u', 'Rendimiento por confianza'].map((m) => (
            <div key={m} className="border-r border-b border-ink p-5">
              <dt className="text-sm text-muted">{m}</dt>
              <dd className="display tnum mt-2 text-5xl text-line">-</dd>
            </div>
          ))}
        </dl>
      </div>
    </Seccion>
  )
}

function Precio() {
  return (
    <section id="precio" className="border-t border-ink bg-paper">
      <div className="mx-auto grid max-w-6xl gap-12 px-4 py-16 sm:px-6 md:py-24 lg:grid-cols-[1.2fr_1fr] lg:gap-16">
        <div>
          <h2 className="display text-[2.8rem] sm:text-[4rem]">Reserva tu plaza para el inicio de la temporada</h2>
          <p className="mt-8 flex items-end gap-4">
            <span className="display tnum text-[7rem] leading-[0.8] text-hot sm:text-[9rem]">9<span className="ml-[0.08em]">€</span></span>
            <span className="pb-2 text-muted">el primer mes,<br />preventa de fundadores</span>
          </p>
          <p className="mt-6 max-w-md leading-relaxed text-muted">
            Acceso desde el primer partido de la temporada. Reembolso completo si no te convence.
          </p>
          <Cta className="mt-8">Reservar por 9 €</Cta>
        </div>
        <div className="self-end">
          <dl className="border-t border-ink">
            <div className="flex items-baseline justify-between gap-6 border-b border-line py-5">
              <dt>
                <span className="font-semibold">Mensual</span>
                <span className="block text-sm text-muted">Después del primer mes. Cancelas cuando quieras.</span>
              </dt>
              <dd className="display tnum shrink-0 text-4xl">15 €<span className="text-xl text-muted">/mes</span></dd>
            </div>
            <div className="flex items-baseline justify-between gap-6 border-b border-line py-5">
              <dt>
                <span className="font-semibold">Anual</span>
                <span className="block text-sm text-muted">Equivale a 10 € al mes.</span>
              </dt>
              <dd className="display tnum shrink-0 text-4xl">120 €<span className="text-xl text-muted">/año</span></dd>
            </div>
          </dl>
          <p className="mt-6 text-sm leading-relaxed text-muted">
            Pago seguro con Stripe. Puedes cancelar en cualquier momento desde tu cuenta. Si el primer mes no te convence,
            escríbenos a <a className="underline hover:text-ink" href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a> y te devolvemos los 9&nbsp;€.
          </p>
        </div>
      </div>
    </section>
  )
}

function Faq() {
  return (
    <Seccion id="faq" titulo="Preguntas frecuentes">
      <dl className="mt-12 grid gap-x-16 md:grid-cols-2">
        {faqs.map(([q, a]) => (
          <div key={q} className="border-t border-line py-6">
            <dt className="text-lg font-semibold">{q}</dt>
            <dd className="mt-2 max-w-[60ch] leading-relaxed text-muted">{a}</dd>
          </div>
        ))}
      </dl>
    </Seccion>
  )
}

export default function Home() {
  return (
    <>
      <Hero />
      <Linea />
      <ComoFunciona />
      <SinVentaja />
      <Ejemplos />
      <Historial />
      <Precio />
      <Faq />
    </>
  )
}
