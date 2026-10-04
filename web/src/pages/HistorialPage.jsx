import { useEffect, useState } from 'react'
import { aEntrada, aResumen, getJson } from '../api'
import { API_URL } from '../config'
import { historial as historialLocal, resumen } from '../data/historial'
import { fmtNum, fmtPct, fmtUnidades } from '../format'

const etiquetaResultado = {
  pendiente: ['Pendiente', 'bg-slate-700 text-slate-200'],
  ganada: ['Ganada', 'bg-emerald-500/20 text-emerald-300'],
  perdida: ['Perdida', 'bg-rose-500/20 text-rose-300'],
  nula: ['Nula', 'bg-slate-700 text-slate-300'],
}

function Cifra({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-bold text-white">{value}</div>
    </div>
  )
}

// Con API configurada, lee /predictions y /track-record; si no, usa src/data/historial.js.
function useHistorial() {
  const [estado, setEstado] = useState({ cargando: Boolean(API_URL), error: false, entradas: historialLocal, tr: null })
  useEffect(() => {
    if (!API_URL) return
    Promise.all([getJson('/predictions'), getJson('/track-record')])
      .then(([preds, tr]) => setEstado({ cargando: false, error: false, entradas: preds.map(aEntrada), tr }))
      .catch(() => setEstado((e) => ({ ...e, cargando: false, error: true })))
  }, [])
  return estado
}

export default function HistorialPage() {
  const { cargando, error, entradas: historial, tr } = useHistorial()
  const total = aResumen(tr?.overall) || resumen(historial)
  const porConfianza = (c) => aResumen(tr?.by_confidence?.[c.toLowerCase()]) || resumen(historial, (e) => e.confianza === c)
  const ordenado = [...historial].sort((a, b) => b.publicado.localeCompare(a.publicado))

  return (
    <div className="mx-auto max-w-6xl px-4 py-14">
      <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">Historial público</h1>
      <p className="mt-4 max-w-3xl text-slate-300">
        Cada análisis se publica antes del partido, con fecha y hora, y no se edita después. Las ganadas y las
        perdidas. El rendimiento se calcula con una apuesta fija de 1 unidad por jugada.
      </p>

      <div className="mt-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Cifra label="Análisis publicados" value={tr ? tr.overall.picks + tr.no_bet_analyses : historial.length} />
        <Cifra label="Acierto" value={fmtPct(total.acierto)} />
        <Cifra label="Beneficio (1 u fija)" value={total.resueltas ? fmtUnidades(total.beneficio) : '—'} />
        <Cifra label="Rendimiento (ROI)" value={fmtPct(total.roi)} />
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        {['Alta', 'Media', 'Baja'].map((c) => {
          const r = porConfianza(c)
          return (
            <div key={c} className="rounded-2xl border border-slate-800 p-4 text-sm text-slate-300">
              <span className="font-semibold text-white">Confianza {c.toLowerCase()}:</span>{' '}
              {r.resueltas ? `${r.ganadas}/${r.resueltas} · ROI ${fmtPct(r.roi)}` : 'sin datos aún'}
            </div>
          )
        })}
      </div>

      {error && (
        <p className="mt-8 rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-200">
          No hemos podido cargar el historial ahora mismo. Prueba de nuevo en unos minutos.
        </p>
      )}

      {cargando ? (
        <p className="mt-10 text-center text-slate-400">Cargando historial…</p>
      ) : ordenado.length === 0 ? (
        <div className="mt-10 rounded-2xl border-2 border-dashed border-slate-700 p-10 text-center">
          <p className="font-semibold text-slate-200">El historial empieza con el primer partido de la temporada 2026-27.</p>
          <p className="mt-2 text-sm text-slate-500">Desde ese día verás aquí cada análisis y su resultado.</p>
        </div>
      ) : (
        <div className="mt-10 overflow-x-auto rounded-2xl border border-slate-800">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-slate-900 text-xs uppercase text-slate-400">
              <tr>
                {['Publicado', 'Partido / fecha', 'Jugador', 'Prop', 'Cuota', 'Prob. est.', 'Confianza', 'Resultado'].map((h) => (
                  <th key={h} className="px-4 py-3 font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {ordenado.map((e) => {
                const [txt, cls] = e.jugada ? etiquetaResultado[e.resultado] : ['Sin ventaja', 'bg-slate-800 text-slate-400']
                return (
                  <tr key={e.id ?? `${e.publicado}-${e.jugador}-${e.prop}`}>
                    <td className="px-4 py-3 text-slate-400">{new Date(e.publicado).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' })}</td>
                    <td className="px-4 py-3">{e.partido}</td>
                    <td className="px-4 py-3 font-medium text-white">
                      {e.jugador}
                      {e.informe && (
                        <details className="mt-1 max-w-sm font-normal text-slate-400">
                          <summary className="cursor-pointer text-xs text-brand">Informe</summary>
                          <p className="mt-1 whitespace-pre-line text-xs">{e.informe}</p>
                        </details>
                      )}
                    </td>
                    <td className="px-4 py-3">{e.lado ? `${e.prop} ${e.lado} de ${fmtNum(e.linea)}` : `${e.prop}: línea ${fmtNum(e.linea)}`}</td>
                    <td className="px-4 py-3">{fmtNum(e.cuota)}</td>
                    <td className="px-4 py-3">{fmtPct(e.probEstimada)}</td>
                    <td className="px-4 py-3">{e.confianza}</td>
                    <td className="px-4 py-3"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${cls}`}>{txt}</span></td>
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
