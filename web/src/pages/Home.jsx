import { ArrowDown, ArrowRight } from '@phosphor-icons/react'
import { Fragment, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import Avisame from '../components/Avisame'
import Cta from '../components/Cta'
import LaLinea from '../components/LaLinea'
import { CONTACT_EMAIL } from '../config'
import { FECHA_EJEMPLOS, informesLanding } from '../data/informes'
import { fmtNum, fmtPct } from '../format'
import { PRECIO, TEXTO_SUBIDA, subidaPendiente } from '../lib/zona'


const preguntas = [
  ['Tendencias', 'Últimos 5, 10 y 20 partidos, minutos y uso. ¿El jugador está por encima o por debajo de su media?'],
  ['Matchup', 'Cómo defiende el rival esa estadística y en qué posición. Ritmo de juego esperado.'],
  ['Contexto', 'Back-to-back, viajes, bajas del equipo y del rival, riesgo de paliza.'],
  ['La línea', 'Cuántas veces la superó en los últimos 5 y 10 partidos y en la temporada, en casa, fuera y contra ese rival.'],
  ['Las casas', 'La misma prop en varias casas, con su línea y su cuota, para que veas dónde está mejor antes de decidir.'],
]

const faqs = [
  ['¿Me vais a decir a qué apostar?', 'No. Te damos datos y análisis de cada línea para que decidas tú. No damos picks ni recomendaciones: la decisión y el riesgo son tuyos.'],
  ['¿Garantizáis ganancias?', 'No, y desconfía de quien lo haga. Es información orientativa. Apostar siempre implica riesgo de perder dinero y a largo plazo es muy difícil ganar a la casa.'],
  ['¿Qué es «Ejemplo de mis picks»?', 'Los picks del fundador hechos con ayuda de la página. Se publican antes del partido, no se editan y salen todos, también los fallados. Son suyos, no del modelo, y no garantizan nada.'],
  ['¿Puedo preguntarle cosas?', 'Sí. Con la suscripción tienes un chat en español para preguntar por los partidos y las líneas del día. Responde con los datos de PropDeep y no te dice qué apostar.'],
  ['¿Qué props cubrís?', 'Puntos, rebotes, asistencias y triples de los partidos de la NBA, empezando por los de más interés cada día.'],
  ['¿Cuándo se publican los análisis?', 'Antes de cada jornada, a una hora cómoda para España y Latinoamérica.'],
  ['¿Trabajáis con casas de apuestas?', 'No. No tenemos afiliación ni patrocinio de ningún operador.'],
  ['¿Cómo funciona la prueba gratis?', 'Cuando abra, tienes 7 días de acceso completo sin pagar. Si no te convence, no sigues y no pagas nada.'],
  ['¿Por qué no puedo pagar ya?', 'Porque no cobramos por algo que aún no puedes usar. Déjanos tu correo y te avisamos el día que abra.'],
]

const anatomia = ['Jugador y partido', 'Prop y línea', 'Proyección', 'Veces que superó la línea', 'Casa, fuera y rival', 'Minutos y contexto', 'Líneas de cada casa', 'Informe en español']

function Palabras({ texto, desde = 0 }) {
  return texto.split(' ').map((w, i) => (
    <Fragment key={i}>
      <span className="palabra" style={{ '--i': desde + i }}>{w}</span>{' '}
    </Fragment>
  ))
}

function Leyenda({ className = '' }) {
  return (
    <div className={`flex flex-wrap items-center gap-x-5 gap-y-1 text-xs font-medium text-muted ${className}`}>
      <span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-full bg-gold" /> Anotado</span>
      <span className="inline-flex items-center gap-1.5"><svg viewBox="0 0 10 10" className="size-2.5" aria-hidden><path d="M1 1l8 8M9 1l-8 8" stroke="var(--grey)" strokeWidth="1.8" /></svg> Fallado</span>
      <span>Campo de tiros ilustrativo</span>
    </div>
  )
}

function Hero() {
  return (
    <section className="relative overflow-x-clip">
      <div className="mx-auto flex min-h-[calc(100svh-6.5rem)] max-w-6xl flex-col justify-end px-4 pt-[34svh] pb-14 sm:px-6 md:pb-20">
        <div className="relative max-w-[52rem]">
          <div aria-hidden className="absolute -inset-x-16 -inset-y-12 -z-10 bg-[radial-gradient(closest-side,oklch(0.14_0_0/0.85),transparent)]" />
          <h1 className="display text-[3.5rem] sm:text-[5.6rem] xl:text-[6.8rem]">
            <Palabras texto="Player props de la NBA, con números" />
            <span className="relative inline-block text-gold">
              <Palabras texto="y no con corazonadas." desde={6} />
              <svg viewBox="0 0 300 20" preserveAspectRatio="none" className="absolute -bottom-2 left-0 h-[0.18em] w-full" aria-hidden>
                <path className="swish" pathLength="1" d="M3 14C80 4 200 2 297 10" fill="none" stroke="var(--gold)" strokeWidth="5" strokeLinecap="round" />
              </svg>
            </span>
          </h1>
          <p className="rise mt-7 max-w-[36rem] text-lg leading-relaxed text-muted" style={{ '--i': 8 }}>
            Análisis estadístico en español de cada prop: tendencias, cuántas veces superó la línea, rival, contexto y las líneas de cada casa comparadas. Información para decidir tú, sin promesas.
          </p>
          <div className="rise mt-9 flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:gap-7" style={{ '--i': 9 }}>
            <Cta />
            <a href="#la-linea" className="group inline-flex items-center gap-1.5 font-semibold underline decoration-grey underline-offset-4 hover:decoration-gold">
              Pruébalo con un ejemplo
              <ArrowDown aria-hidden className="size-4 transition-transform duration-200 group-hover:translate-y-0.5" />
            </a>
          </div>
          <p className="rise mt-5 text-sm text-muted" style={{ '--i': 10 }}>
            Abre el 20 de octubre con 7 días de prueba gratis. Solo mayores de 18 años.
          </p>
          <Leyenda className="rise mt-8" />
        </div>
      </div>
    </section>
  )
}

const cinta = ['Puntos', 'Rebotes', 'Asistencias', 'Triples', 'Datos, no promesas']

// Cinta de marcador que corre bajo la portada.
function Cinta() {
  const fila = (oculta) => (
    <ul aria-hidden={oculta || undefined} className="flex shrink-0 items-center">
      {cinta.map((t) => (
        <li key={t} className="display flex items-center gap-6 pr-6 text-[1.9rem] whitespace-nowrap">
          {t}
          <svg viewBox="0 0 20 20" className="size-4" aria-hidden><circle cx="10" cy="10" r="8" fill="none" stroke="var(--black)" strokeWidth="3" /></svg>
        </li>
      ))}
    </ul>
  )
  return (
    <div className="relative -rotate-1 overflow-hidden border-y-2 border-black bg-gold py-2.5 text-black">
      <div className="marquee flex w-max">
        {fila(false)}{fila(true)}{fila(true)}{fila(true)}
      </div>
    </div>
  )
}

function Titulo({ children, className = '' }) {
  return <h2 className={`display wipe text-[3rem] sm:text-[4.6rem] ${className}`}>{children}</h2>
}

function Linea() {
  return (
    <section id="la-linea" className="py-16 md:py-28">
      <div className="mx-auto max-w-6xl px-4 pb-10 sm:px-6">
        <Titulo className="max-w-[18ch]">Línea, cuota y datos. <span className="hueco hueco-blanco">Pruébalo tú</span></Titulo>
        <p className="mt-5 max-w-2xl text-lg leading-relaxed text-muted">
          Elige un jugador, mueve la línea y la cuota, y mira de qué lado caen sus partidos. Es el primer dato que mira cualquiera; PropDeep te da muchos más.
        </p>
      </div>
      <LaLinea />
    </section>
  )
}

function ComoFunciona() {
  return (
    <section id="como-funciona" className="py-16 md:py-24">
      <div className="panel mx-auto max-w-6xl px-4 py-12 sm:px-10 md:py-16">
        <Titulo>Cinco preguntas antes de <span className="text-gold">cada prop</span></Titulo>
        <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted">
          Todo en español y explicado, para que entiendas el porqué y decidas tú.
        </p>
        <dl className="mt-12 border-t border-white/30">
          {preguntas.map(([titulo, texto], i) => (
            <div key={titulo} className="lift group relative grid gap-2 border-b border-white/30 py-5 md:grid-cols-[20rem_1fr] md:gap-10 md:py-7" style={{ '--i': i }}>
              <span aria-hidden className="absolute inset-0 -z-10 origin-left scale-x-0 bg-gold/10 transition-transform duration-500 ease-[var(--ease-snap)] group-hover:scale-x-100" />
              <dt className="flex items-center gap-4">
                <svg viewBox="0 0 30 30" className="size-7 shrink-0 transition-transform duration-500 group-hover:rotate-180" aria-hidden>
                  <circle cx="15" cy="15" r="13" fill="var(--gold)" />
                  <path d="M2 15H28M15 2V28M5.5 6.5C10 10 10 20 5.5 23.5M24.5 6.5C20 10 20 20 24.5 23.5" fill="none" stroke="var(--black)" strokeWidth="1.6" />
                </svg>
                <span className="display text-[2.3rem] transition-colors group-hover:text-gold">{titulo}</span>
              </dt>
              <dd className="max-w-[60ch] text-lg leading-relaxed text-muted md:pt-1.5">{texto}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}

// Mientras la sección cruza la pantalla, las dos líneas del titular se
// desplazan en sentidos opuestos.
function useDeslizar() {
  const ref = useRef(null)
  useEffect(() => {
    if (!matchMedia('(prefers-reduced-motion: no-preference)').matches) return
    const el = ref.current
    let raf = 0
    const actualizar = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const r = el.getBoundingClientRect()
        const p = (innerHeight - r.top) / (innerHeight + r.height)
        el.style.setProperty('--d', Math.max(0, Math.min(1, p)).toFixed(4))
      })
    }
    actualizar()
    addEventListener('scroll', actualizar, { passive: true })
    return () => {
      cancelAnimationFrame(raf)
      removeEventListener('scroll', actualizar)
    }
  }, [])
  return ref
}

function SinPromesas() {
  const ref = useDeslizar()
  return (
    <section ref={ref} className="relative overflow-hidden bg-white text-black">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 md:py-28">
        <h2 className="display text-[4.4rem] sm:text-[8rem] lg:text-[10.5rem]">
          <span className="lift block"><span className="deslizar block">Datos,</span></span>
          <span className="lift hueco hueco-negro block" style={{ '--i': 1 }}><span className="deslizar deslizar-inverso block">no promesas.</span></span>
        </h2>
        <p className="mt-8 max-w-2xl text-lg leading-relaxed font-medium">
          Muchos servicios venden picks y rachas. Nosotros te ahorramos el trabajo de buscar los datos de cada línea y de
          comparar casas, y te los explicamos en español. Lo que hagas con ellos lo decides tú: es información orientativa
          y no garantiza ganar.
        </p>
        <ul className="mt-14 grid gap-8 md:grid-cols-3 md:gap-10">
          {[
            'Información orientativa, sin garantía de ningún resultado.',
            'Las líneas de cada casa, comparadas en un vistazo.',
            'Los picks del fundador, todos, también los fallados.',
          ].map((t, i) => (
            <li key={t} className="lift border-t-4 border-black pt-4 text-xl leading-snug font-semibold" style={{ '--i': i }}>{t}</li>
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
  return (
    <article className="panel flex flex-col border-2 border-white/30 p-6">
      <p className="text-sm text-muted">{informe.tipo}</p>
      <h3 className="display mt-3 text-3xl">{informe.jugador}</h3>
      <p className="text-sm text-muted">{informe.partido}</p>
      <p className="mt-3 font-semibold text-gold">{informe.prop}</p>
      <dl className="mt-5 grid grid-cols-2 gap-4 border-t border-line pt-4 text-sm">
        <Dato label="Cuotas (más / menos)" value={informe.cuotas} />
        <Dato label="Proyección" value={fmtNum(informe.proyeccion)} />
        <Dato label="Superó la línea (últ. 10)" value={fmtPct(informe.superoUltimos10)} />
        <Dato label="Media últimos 10" value={fmtNum(informe.mediaUltimos10)} />
      </dl>
      {informe.informe && (
        <details className="mt-5 text-sm">
          <summary className="cursor-pointer font-semibold text-gold">Leer el informe completo</summary>
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
        <p className="display text-[2.8rem] text-gold">Llegan el 20 de octubre</p>
        <p className="mt-3 max-w-md text-lg leading-relaxed text-muted">
          Los publicaremos con datos reales del primer día de la temporada regular. Aquí no inventamos ejemplos.
        </p>
      </div>
      <div className="lift border-2 border-white/40">
        <p className="display bg-white px-5 py-3 text-xl text-black">Ficha de cada informe</p>
        <dl className="grid sm:grid-cols-2">
          {anatomia.map((a, i) => (
            <div key={a} className={`flex items-baseline justify-between gap-4 border-white/20 px-5 py-3.5 ${i < anatomia.length - 2 ? 'border-b' : 'max-sm:border-b max-sm:last:border-b-0'} ${i % 2 === 0 ? 'sm:border-r' : ''}`}>
              <dt>{a}</dt>
              <dd className="h-px w-12 shrink-0 self-end border-b-2 border-dashed border-gold/60" aria-label="Pendiente" />
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
    <section id="ejemplos" className="py-16 md:py-24">
      <div className="panel mx-auto max-w-6xl px-4 py-12 sm:px-10 md:py-16">
        <Titulo>Así es un análisis de <span className="text-gold">PropDeep</span></Titulo>
        <p className="mt-5 mb-12 max-w-2xl text-lg leading-relaxed text-muted">
          Ejemplos reales{FECHA_EJEMPLOS ? ` con datos del ${new Date(FECHA_EJEMPLOS).toLocaleDateString('es-ES')}` : ''}
          para que veas qué datos tienes de cada línea y cómo te los explicamos.
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

function MisPicks() {
  return (
    <section className="pb-16 md:pb-24">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 sm:px-6 lg:grid-cols-[1fr_1.1fr] lg:gap-16">
        <div>
          <Titulo>Ejemplo de mis picks <span className="hueco hueco-blanco">con ayuda de la página</span></Titulo>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted">
            Los picks del fundador, hechos con los datos de PropDeep. Se publican antes del partido con su cuota y su casa, no
            se editan y salen todos, también los fallados. Son suyos, no del modelo.
          </p>
          <p className="mt-4 max-w-xl font-semibold">Resultados pasados no garantizan nada; a largo plazo es muy difícil ganar a la casa.</p>
          <Link to="/mis-picks" className="btn btn-ghost mt-8 h-12 px-6 text-lg">
            Ver todos los picks <ArrowRight aria-hidden className="size-4" />
          </Link>
        </div>
        <dl className="panel grid grid-cols-2 self-end border-t-2 border-l-2 border-white/40">
          {['Picks publicados', 'Ganados / perdidos', 'Unidades', 'Rendimiento'].map((m, i) => (
            <div key={m} className="lift border-r-2 border-b-2 border-white/40 p-5" style={{ '--i': i }}>
              <dt className="text-sm text-muted">{m}</dt>
              <dd className="display tnum mt-3 text-6xl text-gold">-</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}

function Precio() {
  return (
    <section id="precio" className="relative bg-gold text-black">
      <div id="avisame" className="mx-auto grid max-w-6xl scroll-mt-20 gap-12 px-4 py-16 sm:px-6 md:py-24 lg:grid-cols-[1.2fr_1fr] lg:gap-16">
        <div>
          <Titulo>Abre el 20 de octubre. Te avisamos.</Titulo>
          <p className="mt-8 flex items-end gap-5">
            <span className="display lift tnum text-[9rem] leading-[0.78] sm:text-[12rem]">7</span>
            <span className="pb-3 text-lg leading-snug font-medium">días de prueba gratis<br />con acceso completo</span>
          </p>
          <p className="mt-6 mb-8 max-w-md text-lg leading-relaxed">
            No cobramos nada hasta que puedas usarlo. Déjanos tu correo y te escribimos el día que abra.
          </p>
          <Avisame />
        </div>
        <div className="self-end">
          <p className="text-sm font-semibold">Después de la prueba</p>
          <dl className="mt-3 border-t-2 border-black">
            {[
              ['Mensual', 'Todo el análisis y 5 preguntas de chat al día.', PRECIO.mensual, '/mes'],
              ['Pro', 'Todo, con el chat completo: 30 preguntas al día.', PRECIO.pro, '/mes'],
              ['Anual', `4 meses gratis frente a pagar mes a mes.`, PRECIO.anual, '/año'],
            ].map(([plan, detalle, precio, periodo]) => (
              <div key={plan} className="flex items-baseline justify-between gap-6 border-b-2 border-black/30 py-5">
                <dt>
                  <span className="text-lg font-semibold">{plan}</span>
                  <span className="block text-sm">{detalle}</span>
                </dt>
                <dd className="display tnum shrink-0 text-5xl">{precio} €<span className="text-xl">{periodo}</span></dd>
              </div>
            ))}
          </dl>
          <p className="mt-4 text-sm">¿Solo una semana? Pase de 7 días por {PRECIO.pase} €, sin renovación.</p>
          {subidaPendiente() && <p className="mt-4 border-2 border-black px-4 py-3 font-semibold">{TEXTO_SUBIDA}</p>}
          <p className="mt-6 text-sm leading-relaxed">
            Solo usamos tu correo para avisarte de la apertura. ¿Dudas? Escríbenos a{' '}
            <a className="font-semibold underline" href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
          </p>
        </div>
      </div>
    </section>
  )
}

function Faq() {
  return (
    <section id="faq" className="py-16 md:py-24">
      <div className="panel mx-auto max-w-6xl px-4 py-12 sm:px-10 md:py-16">
        <Titulo>Preguntas frecuentes</Titulo>
        <dl className="mt-12 grid gap-x-16 md:grid-cols-2">
          {faqs.map(([q, a]) => (
            <div key={q} className="border-t border-white/30 py-6">
              <dt className="text-xl font-bold">{q}</dt>
              <dd className="mt-2 max-w-[60ch] text-lg leading-relaxed text-muted">{a}</dd>
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
      <Cinta />
      <Linea />
      <ComoFunciona />
      <SinPromesas />
      <Ejemplos />
      <MisPicks />
      <Precio />
      <Faq />
    </>
  )
}
