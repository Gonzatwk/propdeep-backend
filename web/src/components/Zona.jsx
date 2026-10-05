import { ArrowClockwise, ArrowLeft, Eye, LockSimple } from '@phosphor-icons/react'
import { Link } from 'react-router-dom'
import { useModo } from '../lib/tablero'
import { PRECIO, useIrASuscribir } from '../lib/zona'


// Contenedor de las páginas de la zona: fondo opaco para leer datos sin ruido.
export function Pagina({ children, ancho = 'max-w-6xl' }) {
  return <div className={`mx-auto ${ancho} px-4 py-10 sm:px-6 md:py-14`}>{children}</div>
}

export function Volver({ to, children }) {
  return (
    <Link to={to} className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-white">
      <ArrowLeft aria-hidden className="size-4" /> {children}
    </Link>
  )
}

// Franja que avisa de que los datos son de demostración, con el cambio de vista.
export function AvisoDemo({ sinVista = false }) {
  const { demo, demoSuscriptor } = useModo()
  if (!demo) return null
  const opcion = (valor, texto, activa) => (
    <Link
      to={`?demo=${valor}`}
      replace
      aria-current={activa || undefined}
      className={`px-3 py-1.5 text-sm font-semibold ${activa ? 'bg-black text-gold' : 'text-black hover:bg-black/10'}`}
    >
      {texto}
    </Link>
  )
  return (
    <div role="note" className="mb-8 flex flex-col gap-3 bg-gold px-4 py-3 text-black sm:flex-row sm:items-center sm:justify-between">
      <p className="text-sm font-medium">
        <strong className="font-extrabold">Demostración.</strong> Jugadores y números inventados para enseñar cómo se verá. Los datos reales empiezan el 20 de octubre.
      </p>
      {!sinVista && <div className="flex shrink-0 items-center gap-1 self-start border-2 border-black sm:self-auto" aria-label="Ver como">
        <Eye aria-hidden className="ml-2 size-4" />
        {opcion('1', 'Gratis', !demoSuscriptor)}
        {opcion('suscriptor', 'Suscriptor', demoSuscriptor)}
      </div>}
    </div>
  )
}

// Porcentaje de partidos por encima de la línea, con su muestra.
export function Tasa({ valor, partidos, etiqueta, grande = false }) {
  const tono = valor == null ? 'text-muted' : 'text-white'
  return (
    <div className={grande ? 'border border-white/25 px-4 py-3' : ''}>
      <p className="text-xs text-muted">{etiqueta}</p>
      <p className={`display tnum leading-none ${tono} ${grande ? 'mt-1 text-[2.4rem]' : 'text-[1.4rem]'}`}>
        {valor == null ? '-' : `${Math.round(valor * 100)} %`}
      </p>
      {grande && partidos != null && <p className="tnum mt-1 text-xs text-muted">{partidos} {partidos === 1 ? 'partido' : 'partidos'}</p>}
    </div>
  )
}

export function Bloqueada() {
  return (
    <span className="inline-flex items-center gap-1.5 border border-dashed border-white/30 px-2 py-0.5 text-sm text-muted">
      <LockSimple aria-hidden weight="bold" className="size-3.5" /> Con suscripción
    </span>
  )
}

// Muro de pago: qué desbloquea la suscripción y cuánto cuesta.
export function Muro({ bloqueadas, compacto = false }) {
  const destino = useIrASuscribir()
  return (
    <aside className={`border-2 border-gold bg-black ${compacto ? 'p-5' : 'p-6 sm:p-8'}`}>
      <p className="display text-[2rem] leading-none text-gold sm:text-[2.4rem]">
        {bloqueadas ? `${bloqueadas} líneas más en este partido` : 'Todas las líneas, todos los días'}
      </p>
      <p className="mt-3 max-w-xl text-muted">
        Con la suscripción ves el análisis de cada línea: proyección, cuántas veces superó la línea, casa y fuera, el rival,
        las líneas de cada casa y el informe. Prueba {PRECIO.prueba} días gratis;
        después {PRECIO.mensual} € al mes o {PRECIO.anual} € al año. Cancelas cuando quieras.
      </p>
      <Link to={destino} className="btn btn-gold mt-5 h-12 px-6 text-lg">
        Probar {PRECIO.prueba} días gratis
      </Link>
    </aside>
  )
}

export function Cargando({ filas = 3 }) {
  return (
    <div aria-busy="true" aria-label="Cargando" className="space-y-3">
      {Array.from({ length: filas }, (_, i) => <div key={i} className="h-24 animate-pulse bg-black-2" />)}
    </div>
  )
}

export function Fallo({ reintentar, children = 'No hemos podido cargar los datos. Comprueba tu conexión y vuelve a intentarlo.' }) {
  return (
    <div role="alert" className="flex flex-wrap items-center justify-between gap-4 border border-gold px-5 py-4">
      <p>{children}</p>
      {reintentar && (
        <button type="button" onClick={reintentar} className="btn btn-ghost h-10 px-4">
          <ArrowClockwise aria-hidden className="size-4" /> Reintentar
        </button>
      )}
    </div>
  )
}

export function AvisoResponsable() {
  return (
    <p className="mt-12 flex items-start gap-3 border-t border-line pt-6 text-sm leading-relaxed text-muted">
      <span className="tnum mt-0.5 shrink-0 border border-white px-1.5 py-0.5 text-xs font-bold text-white">+18</span>
      Información estadística orientativa, sin garantía de ningún resultado: no es una recomendación de apuesta. Apostar implica
      riesgo de perder dinero y a largo plazo es muy difícil ganar a la casa. Juega solo con lo que puedas permitirte perder.
    </p>
  )
}
