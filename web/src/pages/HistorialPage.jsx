import { ArrowClockwise } from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'
import { aEntrada, aResumen, getJson } from '../api'
import { API_URL } from '../config'
import { historial as historialLocal, resumen } from '../data/historial'
import { fmtNum, fmtPct, fmtUnidades } from '../format'

const etiquetaResultado = {
  pendiente: ['Pendiente', 'bg-paper-2 text-muted'],
  ganada: ['Ganada', 'bg-cobalt text-on-dark'],
  perdida: ['Perdida', 'border border-cobalt-deep text-ink'],
  nula: ['Nula', 'bg-paper-2 text-muted'],
}

// Con API configurada, lee /predictions y /track-record; si no, usa src/data/historial.js.
function useHistorial() {
  const [estado, setEstado] = useState({ cargando: Boolean(API_URL), error: false, entradas: historialLocal, tr: null })
  const cargar = useCallback(() => {
    Promise.all([getJson('/predictions'), getJson('/track-record')])
      .then(([preds, tr]) => setEstado({ cargando: false, error: false, entradas: preds.map(aEntrada), tr }))
      .catch(() => setEstado((e) => ({ ...e, cargando: false, error: true })))
  }, [])
  useEffect(() => {
    if (API_URL) cargar()
  }, [cargar])
  const reintentar = () => {
    setEstado((e) => ({ ...e, cargando: true, error: false }))
    cargar()
  }
  return { ...estado, reintentar }
}

function Cifra({ label, value, cargando }) {
  return (
    <div className="border-r border-b border-cobalt-deep p-5 sm:p-6">
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="display tnum mt-2 text-4xl sm:text-5xl">
        {cargando ? <span className="block h-8 w-20 animate-pulse bg-paper-2" /> : value}
      </dd>
    </div>
  )
}

function FilasCargando() {
  return Array.from({ length: 4 }, (_, i) => (
    <tr key={i}>
      <td colSpan={8} className="px-4 py-3.5">
        <span className="block h-5 animate-pulse bg-paper-2" style={{ width: `${88 - i * 9}%` }} />
      </td>
    </tr>
  ))
}

export default function HistorialPage() {
  const { cargando, error, entradas: historial, tr, reintentar } = useHistorial()
  const total = aResumen(tr?.overall) || resumen(historial)
  const porConfianza = (c) => aResumen(tr?.by_confidence?.[c.toLowerCase()]) || resumen(historial, (e) => e.confianza === c)
  const ordenado = [...historial].sort((a, b) => b.publicado.localeCompare(a.publicado))
  const vacio = !cargando && ordenado.length === 0

  return (
    <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6 md:py-20">
      <h1 className="display text-[3.4rem] sm:text-[5rem]">Historial público</h1>
      <p className="mt-5 max-w-2xl text-lg leading-relaxed text-muted">
        Cada análisis se publica antes del partido, con fecha y hora, y no se edita después. Las ganadas y las perdidas.
        El rendimiento se calcula con una apuesta fija de 1 unidad por jugada.
      </p>

      <dl className="mt-10 grid grid-cols-2 border-t border-l border-cobalt-deep bg-paper md:grid-cols-4">
        <Cifra cargando={cargando} label="Análisis publicados" value={tr ? tr.overall.picks + tr.no_bet_analyses : historial.length} />
        <Cifra cargando={cargando} label="Acierto" value={fmtPct(total.acierto)} />
        <Cifra cargando={cargando} label="Beneficio a 1 u" value={total.resueltas ? fmtUnidades(total.beneficio) : '-'} />
        <Cifra cargando={cargando} label="Rendimiento (ROI)" value={fmtPct(total.roi)} />
      </dl>

      <ul className="mt-4 grid gap-3 text-sm md:grid-cols-3">
        {['Alta', 'Media', 'Baja'].map((c) => {
          const r = porConfianza(c)
          return (
            <li key={c} className="flex items-center justify-between border-b border-line py-3.5">
              <span className="font-medium">Confianza {c.toLowerCase()}</span>
              <span className="tnum text-muted">
                {r.resueltas ? `${r.ganadas}/${r.resueltas} · ROI ${fmtPct(r.roi)}` : 'sin datos aún'}
              </span>
            </li>
          )
        })}
      </ul>

      {error && (
        <div role="alert" className="mt-8 flex flex-wrap items-center justify-between gap-4 border border-red bg-paper px-5 py-4">
          <p>No hemos podido cargar el historial. Comprueba tu conexión y vuelve a intentarlo.</p>
          <button type="button" onClick={reintentar} className="btn btn-ghost h-10 px-4">
            <ArrowClockwise aria-hidden className="size-4" /> Reintentar
          </button>
        </div>
      )}

      {vacio ? (
        <div className="mt-10 border border-dashed border-cobalt-deep px-6 py-16 text-center">
          
          <p className="display text-[2.4rem] text-red">El historial empieza el 20 de octubre</p>
          <p className="mx-auto mt-2 max-w-md text-muted">
            Con el primer día de la temporada regular 2026-27. Desde ese día verás aquí cada análisis y su resultado.
          </p>
        </div>
      ) : (
        <div className="mt-10 overflow-x-auto border border-cobalt-deep bg-paper">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-cobalt-deep text-muted">
              <tr>
                {['Publicado', 'Partido / fecha', 'Jugador', 'Prop', 'Cuota', 'Prob. est.', 'Confianza', 'Resultado'].map((h) => (
                  <th key={h} scope="col" className="px-4 py-3 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {cargando ? <FilasCargando /> : ordenado.map((e) => {
                const [txt, cls] = e.jugada ? etiquetaResultado[e.resultado] : ['Sin ventaja', 'bg-paper-2 text-muted']
                return (
                  <tr key={e.id ?? `${e.publicado}-${e.jugador}-${e.prop}`} className="align-top">
                    <td className="tnum px-4 py-3.5 text-muted">{new Date(e.publicado).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' })}</td>
                    <td className="px-4 py-3.5">{e.partido}</td>
                    <td className="px-4 py-3.5 font-medium">
                      {e.jugador}
                      {e.informe && (
                        <details className="mt-1 max-w-sm font-normal">
                          <summary className="cursor-pointer text-xs text-red">Informe</summary>
                          <p className="mt-1 whitespace-pre-line text-xs leading-relaxed text-muted">{e.informe}</p>
                        </details>
                      )}
                    </td>
                    <td className="px-4 py-3.5">{e.lado ? `${e.prop} ${e.lado} de ${fmtNum(e.linea)}` : `${e.prop}: línea ${fmtNum(e.linea)}`}</td>
                    <td className="tnum px-4 py-3.5">{fmtNum(e.cuota)}</td>
                    <td className="tnum px-4 py-3.5">{fmtPct(e.probEstimada)}</td>
                    <td className="px-4 py-3.5">{e.confianza}</td>
                    <td className="px-4 py-3.5"><span className={`px-2 py-1 text-xs font-semibold ${cls}`}>{txt}</span></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
