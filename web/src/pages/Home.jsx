import { Link } from 'react-router-dom'
import Cta from '../components/Cta'
import { CONTACT_EMAIL } from '../config'
import { FECHA_EJEMPLOS, informesLanding } from '../data/informes'
import { fmtNum, fmtPct } from '../format'

const bloques = [
  ['Tendencias', 'Últimos 5, 10 y 20 partidos, minutos y uso. ¿El jugador está por encima o por debajo de su media?'],
  ['Matchup', 'Cómo defiende el rival esa estadística y en qué posición. Ritmo de juego esperado.'],
  ['Factores situacionales', 'Back-to-back, viajes, bajas del equipo y del rival, riesgo de paliza.'],
  ['Línea del mercado', 'Nuestra probabilidad estimada frente a la que implica la cuota. La diferencia es la ventaja, si existe.'],
  ['Nivel de confianza', 'Alto, medio o bajo, explicado en una frase. Sin ventaja, el análisis lo dice.'],
]

const planes = [
  { nombre: 'Preventa', precio: '9 €', sufijo: 'el primer mes', texto: 'Plazas de fundador. Acceso desde el primer partido de la temporada. Reembolso completo si no te convence.', destacado: true },
  { nombre: 'Mensual', precio: '15 €', sufijo: '/mes', texto: 'Después del primer mes. Cancelas cuando quieras.' },
  { nombre: 'Anual', precio: '120 €', sufijo: '/año', texto: 'Equivale a 10 €/mes.' },
]

const faqs = [
  ['¿Me vais a decir a qué apostar?', 'No. Te damos un análisis estadístico y nuestra estimación de probabilidad. La decisión y el riesgo son tuyos.'],
  ['¿Garantizáis ganancias?', 'No, y desconfía de quien lo haga. Apostar siempre implica riesgo de perder dinero. Por eso publicamos todo el historial.'],
  ['¿Qué props cubrís?', 'Puntos, rebotes, asistencias y triples de los partidos de la NBA, empezando por los de más interés cada día.'],
  ['¿Cuándo se publican los análisis?', 'Antes de cada jornada, a una hora cómoda para España y Latinoamérica.'],
  ['¿Trabajáis con casas de apuestas?', 'No. No tenemos afiliación ni patrocinio de ningún operador.'],
  ['¿Cómo funciona el reembolso?', 'Si el primer mes no te convence, nos escribes y te devolvemos los 9 €. Sin preguntas.'],
]

function Section({ id, title, children, className = '' }) {
  return (
    <section id={id} className={`scroll-mt-20 px-4 py-16 sm:py-20 ${className}`}>
      <div className="mx-auto max-w-6xl">
        {title && <h2 className="mb-8 text-3xl font-bold tracking-tight text-white sm:text-4xl">{title}</h2>}
        {children}
      </div>
    </section>
  )
}

function Hero() {
  return (
    <section className="relative overflow-hidden px-4 pt-16 pb-20 sm:pt-24">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(249,115,22,0.18),transparent_60%)]" />
      <div className="relative mx-auto max-w-3xl text-center">
        <p className="mb-4 text-sm font-semibold uppercase tracking-widest text-brand">Análisis estadístico · NBA</p>
        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-6xl">
          Player props de la NBA, con números y no con corazonadas.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-300">
          Análisis estadístico en español de cada prop: tendencias, matchup, contexto y comparación con la línea
          del mercado. Y cuando no hay ventaja, te lo decimos.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Cta>Reserva tu primer mes por 9 €</Cta>
          <a href="#ejemplos" className="rounded-xl border border-slate-700 px-6 py-3 font-semibold text-slate-200 hover:border-slate-500">
            Ver un informe de ejemplo
          </a>
        </div>
        <p className="mt-4 text-sm text-slate-400">Reembolso completo si no te convence. Solo mayores de 18 años.</p>
        <p className="mx-auto mt-6 w-fit rounded-full border border-brand/40 bg-brand/10 px-4 py-1.5 text-sm text-orange-200">
          Los primeros análisis se publican el 20 de octubre, con el inicio de la temporada regular.
        </p>
      </div>
    </section>
  )
}

function QueIncluye() {
  return (
    <Section id="analisis" title="Cinco preguntas antes de cada prop" className="bg-slate-900/50">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {bloques.map(([t, d], i) => (
          <div key={t} className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <div className="mb-3 text-sm font-bold text-brand">{i + 1}</div>
            <h3 className="mb-2 font-semibold text-white">{t}</h3>
            <p className="text-sm text-slate-400">{d}</p>
          </div>
        ))}
      </div>
      <p className="mt-8 text-lg text-slate-300">Todo en español y explicado, para que entiendas el porqué y decidas tú.</p>
    </Section>
  )
}

function SinVentaja() {
  return (
    <Section id="distinto">
      <div className="grid items-center gap-10 lg:grid-cols-2">
        <div>
          <h2 className="mb-6 text-3xl font-bold tracking-tight text-white sm:text-4xl">Sin ventaja, no hay jugada</h2>
          <p className="text-lg text-slate-300">
            La mayoría de servicios te dan picks todos los días, haya valor o no. Nosotros comparamos nuestra
            probabilidad con la de la cuota, y si la diferencia no compensa, lo decimos claramente: "sin ventaja".
            Algunos días habrá pocas jugadas, y eso también es información.
          </p>
        </div>
        <ul className="space-y-3">
          {[
            'Probabilidades, no promesas.',
            'Todas las predicciones publicadas, las ganadas y las perdidas.',
            'Hecho por un apostador que aplica el mismo criterio con su propio dinero.',
          ].map((t) => (
            <li key={t} className="flex gap-3 rounded-xl border border-slate-800 bg-slate-900 p-4 text-slate-200">
              <span className="text-brand">●</span>
              {t}
            </li>
          ))}
        </ul>
      </div>
    </Section>
  )
}

function Dato({ label, value }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="font-semibold text-white">{value}</dd>
    </div>
  )
}

function TarjetaInforme({ informe }) {
  if (informe.pendiente) {
    return (
      <div className="flex min-h-72 flex-col rounded-2xl border-2 border-dashed border-slate-700 p-6">
        <span className="mb-3 w-fit rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold text-slate-300">
          {informe.tipo}
        </span>
        <div className="flex flex-1 flex-col items-center justify-center text-center">
          <p className="font-semibold text-slate-300">Informe en preparación</p>
          <p className="mt-2 text-sm text-slate-500">
            Llega el 20 de octubre, con datos reales del primer día de temporada. Aquí no inventamos ejemplos.
          </p>
        </div>
      </div>
    )
  }
  const ventaja = informe.probEstimada - informe.probImplicita
  return (
    <article className="flex flex-col rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <span className="mb-3 w-fit rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold text-slate-300">{informe.tipo}</span>
      <h3 className="text-xl font-bold text-white">{informe.jugador}</h3>
      <p className="text-sm text-slate-400">{informe.partido}</p>
      <p className="mt-3 font-semibold text-brand">{informe.prop}</p>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <Dato label="Cuota" value={fmtNum(informe.cuota)} />
        <Dato label="Prob. implícita" value={fmtPct(informe.probImplicita)} />
        <Dato label="Prob. estimada" value={fmtPct(informe.probEstimada)} />
        <Dato label="Ventaja" value={fmtPct(ventaja)} />
        <Dato label="Confianza" value={informe.confianza} />
        <Dato label="Veredicto" value={informe.veredicto} />
      </dl>
      <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-slate-300">
        {informe.porque.map((p) => <li key={p}>{p}</li>)}
      </ul>
      {informe.informe && (
        <details className="mt-4 text-sm text-slate-300">
          <summary className="cursor-pointer font-semibold text-brand">Leer el informe completo</summary>
          <p className="mt-2 whitespace-pre-line">{informe.informe}</p>
        </details>
      )}
    </article>
  )
}

function Ejemplos() {
  return (
    <Section id="ejemplos" title="Así es un análisis de PropDeep" className="bg-slate-900/50">
      <p className="-mt-4 mb-8 max-w-3xl text-lg text-slate-300">
        Tres ejemplos reales{FECHA_EJEMPLOS ? ` con datos del ${new Date(FECHA_EJEMPLOS).toLocaleDateString('es-ES')}` : ''}.
        Uno con ventaja, uno sin ventaja y uno con confianza baja, para que veas cómo razonamos en cada caso.
      </p>
      <div className="grid gap-6 md:grid-cols-3">
        {informesLanding.map((inf) => <TarjetaInforme key={inf.tipo} informe={inf} />)}
      </div>
    </Section>
  )
}

function Historial() {
  return (
    <Section id="historial">
      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8 sm:p-10">
        <h2 className="mb-4 text-3xl font-bold tracking-tight text-white sm:text-4xl">Nuestro historial, a la vista</h2>
        <p className="max-w-3xl text-lg text-slate-300">
          Publicamos cada análisis antes del partido, con su fecha y hora, y no se edita después. Cuando termina el
          partido marcamos el resultado, gane o pierda. El historial empieza con el primer partido de la temporada
          2026-27, y desde ese día podrás ver el acierto y el rendimiento acumulado.
        </p>
        <p className="mt-4 text-sm text-slate-400">
          Mostraremos: análisis publicados, porcentaje de acierto, rendimiento con apuesta fija de 1 unidad y
          rendimiento por nivel de confianza.
        </p>
        <Link to="/historial" className="mt-6 inline-block rounded-xl border border-slate-700 px-6 py-3 font-semibold text-slate-200 hover:border-slate-500">
          Ver historial completo
        </Link>
      </div>
    </Section>
  )
}

function Precio() {
  return (
    <Section id="precio" title="Reserva tu plaza para el inicio de la temporada" className="bg-slate-900/50">
      <div className="grid gap-6 md:grid-cols-3">
        {planes.map((p) => (
          <div
            key={p.nombre}
            className={`flex flex-col rounded-2xl border p-6 ${p.destacado ? 'border-brand bg-brand/10' : 'border-slate-800 bg-slate-900'}`}
          >
            <h3 className="font-semibold text-slate-200">{p.nombre}</h3>
            <p className="mt-3">
              <span className="text-4xl font-extrabold text-white">{p.precio}</span>{' '}
              <span className="text-slate-400">{p.sufijo}</span>
            </p>
            <p className="mt-4 flex-1 text-sm text-slate-300">{p.texto}</p>
            {p.destacado && <Cta className="mt-6 w-full">Reservar por 9 €</Cta>}
          </div>
        ))}
      </div>
      <p className="mt-6 text-sm text-slate-400">
        Pago seguro con Stripe. Puedes cancelar en cualquier momento desde tu cuenta. Si el primer mes no te
        convence, escríbenos{CONTACT_EMAIL ? <> a <a className="underline" href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a></> : ''} y te
        devolvemos los 9 €.
      </p>
    </Section>
  )
}

function Faq() {
  return (
    <Section id="faq" title="Preguntas frecuentes">
      <div className="divide-y divide-slate-800 rounded-2xl border border-slate-800">
        {faqs.map(([q, a]) => (
          <details key={q} className="group p-5">
            <summary className="flex cursor-pointer list-none items-center justify-between font-semibold text-white">
              {q}
              <span className="ml-4 text-brand transition group-open:rotate-45">+</span>
            </summary>
            <p className="mt-3 text-slate-300">{a}</p>
          </details>
        ))}
      </div>
    </Section>
  )
}

export default function Home() {
  return (
    <>
      <Hero />
      <QueIncluye />
      <SinVentaja />
      <Ejemplos />
      <Historial />
      <Precio />
      <Faq />
    </>
  )
}
