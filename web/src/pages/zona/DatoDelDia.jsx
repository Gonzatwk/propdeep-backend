import { DownloadSimple, FilmStrip } from '@phosphor-icons/react'
import { useEffect, useRef, useState } from 'react'
import { AvisoDemo, Cargando, Fallo, Pagina } from '../../components/Zona'
import { API_URL } from '../../config'
import { demoLinea, demoPartido, demoTablero } from '../../data/demo'
import { api } from '../../lib/sesion'
import { useModo } from '../../lib/tablero'
import { STAT } from '../../lib/zona'
import { fmtNum } from '../../format'

// "Dato del día" para redes (TikTok, Reels, Shorts, X): imagen y vídeo verticales con una
// línea gratis del día. Solo estadística del jugador: sin cuotas ni casas (las plataformas
// limitan el contenido de apuestas) y con el aviso de +18.
const W = 1080
const H = 1920
const COLOR = { fondo: '#0f0f0f', oro: '#e3be4f', gris: '#8d8d8d', barra: '#2a2a2a', blanco: '#f4f4f4' }
const DISPLAY = '"Big Shoulders Display Variable", "Schibsted Grotesk Variable", sans-serif'
const SANS = '"Schibsted Grotesk Variable", ui-sans-serif, system-ui, sans-serif'
const DURACION = 6500 // ms del vídeo
const CRECER = 2200 // ms que tardan las barras en subir

async function lineasGratis(demo) {
  const tablero = demo ? demoTablero(false) : await api('/board')
  const partidos = await Promise.all(
    tablero.games.filter((g) => g.free_lines > 0).map((g) => (demo ? demoPartido(g.event_id, false) : api(`/board/games/${encodeURIComponent(g.event_id)}`))),
  )
  const ids = partidos.flatMap((p) => p.lines.filter((l) => l.free).map((l) => l.id))
  return Promise.all(ids.map((id) => (demo ? demoLinea(id, false) : api(`/board/lines/${id}`))))
}

function dibujar(ctx, l, t = 1) {
  const valores = [...(l.trends?.recent_values || [])].reverse() // del más antiguo al último
  const supero = valores.filter((v) => v > l.line).length
  ctx.fillStyle = COLOR.fondo
  ctx.fillRect(0, 0, W, H)
  ctx.textBaseline = 'alphabetic'

  ctx.fillStyle = COLOR.oro
  ctx.font = `800 52px ${DISPLAY}`
  ctx.fillText('DATO DEL DÍA', 90, 200)
  ctx.fillStyle = COLOR.gris
  ctx.font = `500 40px ${SANS}`
  const g = l.game || {}
  ctx.fillText(`${g.away_team || ''} en ${g.home_team || ''}`.trim(), 90, 262)

  ctx.fillStyle = COLOR.blanco
  ctx.font = `800 150px ${DISPLAY}`
  const palabras = l.player.toUpperCase().split(' ')
  ctx.fillText(palabras[0], 90, 470)
  if (palabras.length > 1) ctx.fillText(palabras.slice(1).join(' '), 90, 610)

  ctx.font = `600 54px ${SANS}`
  ctx.fillStyle = COLOR.oro
  ctx.fillText(`${STAT[l.stat]} · línea ${fmtNum(l.line)}`, 90, 720)

  ctx.fillStyle = COLOR.blanco
  ctx.font = `800 120px ${DISPLAY}`
  ctx.fillText(`${supero} DE ${valores.length}`, 90, 900)
  ctx.font = `500 46px ${SANS}`
  ctx.fillStyle = COLOR.gris
  ctx.fillText(`partidos por encima de la línea (últimos ${valores.length})`, 90, 970)

  // Barras: últimos partidos frente a la línea.
  const base = 1500
  const alto = 400
  const max = Math.max(l.line * 1.6, ...valores, 1)
  const ancho = (W - 180) / Math.max(valores.length, 1)
  const y = (v) => base - (v / max) * alto
  const avance = Math.min(1, t)
  valores.forEach((v, i) => {
    const retraso = i / valores.length / 2
    const k = Math.max(0, Math.min(1, (avance - retraso) / 0.5))
    const ease = 1 - (1 - k) ** 3
    const top = base - (base - y(v)) * ease
    ctx.fillStyle = v > l.line ? COLOR.oro : COLOR.barra
    ctx.fillRect(90 + i * ancho + 8, top, ancho - 16, base - top)
    if (k >= 1) {
      ctx.fillStyle = COLOR.blanco
      ctx.font = `600 34px ${SANS}`
      ctx.textAlign = 'center'
      ctx.fillText(String(v), 90 + i * ancho + ancho / 2, top - 14)
      ctx.textAlign = 'left'
    }
  })
  ctx.strokeStyle = COLOR.blanco
  ctx.lineWidth = 4
  ctx.setLineDash([18, 12])
  ctx.beginPath()
  ctx.moveTo(90, y(l.line))
  ctx.lineTo(W - 90, y(l.line))
  ctx.stroke()
  ctx.setLineDash([])
  ctx.fillStyle = COLOR.gris
  ctx.font = `500 32px ${SANS}`
  ctx.fillText('Más antiguo', 90, base + 50)
  ctx.textAlign = 'right'
  ctx.fillText('Último', W - 90, base + 50)
  ctx.textAlign = 'left'

  if (l.projection != null) {
    ctx.fillStyle = COLOR.blanco
    ctx.font = `600 46px ${SANS}`
    ctx.fillText(`Proyección PropDeep: ${fmtNum(Math.round(l.projection * 10) / 10)}`, 90, 1660)
  }
  ctx.fillStyle = COLOR.oro
  ctx.font = `800 64px ${DISPLAY}`
  ctx.fillText('PROPDEEP', 90, 1790)
  ctx.fillStyle = COLOR.gris
  ctx.font = `500 28px ${SANS}`
  ctx.fillText('Información estadística, no es una recomendación de apuesta. +18', 90, 1845)
}

function nombreArchivo(l, ext) {
  const limpio = l.player.normalize('NFD').replace(/[^\w]+/g, '-').toLowerCase()
  return `dato-${l.game?.game_date || 'hoy'}-${limpio}-${l.stat}.${ext}`
}

function descargar(blob, nombre) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = nombre
  a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 2000)
}

export default function DatoDelDia() {
  const { demo } = useModo()
  const lienzo = useRef(null)
  const [estado, setEstado] = useState({ cargando: true, lineas: [], error: null })
  const [elegida, setElegida] = useState(0)
  const [grabando, setGrabando] = useState(false)
  const linea = estado.lineas[elegida]

  useEffect(() => {
    if (!demo && !API_URL) {
      setEstado({ cargando: false, lineas: [], error: 'sin-servidor' })
      return
    }
    lineasGratis(demo)
      .then((lineas) => setEstado({ cargando: false, lineas, error: null }))
      .catch(() => setEstado({ cargando: false, lineas: [], error: 'red' }))
  }, [demo])

  useEffect(() => {
    if (!linea || !lienzo.current) return
    document.fonts.ready.then(() => dibujar(lienzo.current.getContext('2d'), linea))
  }, [linea])

  const imagen = () => lienzo.current.toBlob((b) => descargar(b, nombreArchivo(linea, 'png')), 'image/png')

  const video = async () => {
    const tipo = ['video/mp4', 'video/webm;codecs=vp9', 'video/webm'].find((m) => window.MediaRecorder?.isTypeSupported(m))
    if (!tipo) return
    setGrabando(true)
    const ctx = lienzo.current.getContext('2d')
    const grabadora = new MediaRecorder(lienzo.current.captureStream(30), { mimeType: tipo, videoBitsPerSecond: 8e6 })
    const trozos = []
    grabadora.ondataavailable = (e) => e.data.size && trozos.push(e.data)
    grabadora.onstop = () => {
      descargar(new Blob(trozos, { type: tipo }), nombreArchivo(linea, tipo.startsWith('video/mp4') ? 'mp4' : 'webm'))
      setGrabando(false)
    }
    grabadora.start()
    const inicio = performance.now()
    const cuadro = (ahora) => {
      const pasado = ahora - inicio
      dibujar(ctx, linea, pasado / CRECER)
      if (pasado < DURACION) requestAnimationFrame(cuadro)
      else grabadora.stop()
    }
    requestAnimationFrame(cuadro)
  }

  return (
    <Pagina ancho="max-w-5xl">
      <AvisoDemo sinVista />
      <h1 className="display text-[3rem] leading-none sm:text-[4rem]">Dato del día</h1>
      <p className="mt-4 max-w-2xl text-lg text-muted">
        Imagen y vídeo verticales (1080 × 1920) con una línea gratis de hoy, para TikTok, Reels, Shorts o X. Solo datos del
        jugador: ni cuotas ni casas, que las redes limitan el contenido de apuestas. Pon +18 en tu perfil.
      </p>
      <div className="mt-8">
        {estado.cargando ? <Cargando filas={2} /> : estado.error === 'sin-servidor' ? (
          <p className="border border-dashed border-white/40 px-5 py-6 text-muted">Funciona con los datos reales desde el 20 de octubre. Mientras, pruébalo con <a className="underline" href="?demo=1">la demostración</a>.</p>
        ) : estado.error ? <Fallo /> : !linea ? (
          <p className="text-muted">Hoy no hay líneas gratis publicadas todavía.</p>
        ) : (
          <div className="grid gap-8 md:grid-cols-[1fr_20rem]">
            <canvas ref={lienzo} width={W} height={H} className="w-full max-w-[26rem] border border-white/20" aria-label={`Dato del día de ${linea.player}`} />
            <div className="space-y-5">
              <fieldset>
                <legend className="mb-2 font-semibold">Línea</legend>
                {estado.lineas.map((l, i) => (
                  <label key={l.id} className="flex cursor-pointer items-center gap-2 py-1">
                    <input type="radio" name="linea" checked={i === elegida} onChange={() => setElegida(i)} className="accent-[var(--gold)]" />
                    {l.player} · {STAT[l.stat]} {fmtNum(l.line)}
                  </label>
                ))}
              </fieldset>
              <button type="button" onClick={imagen} className="btn btn-gold h-12 w-full px-5 text-lg">
                <DownloadSimple aria-hidden className="size-5" /> Descargar imagen
              </button>
              <button type="button" onClick={video} disabled={grabando || !window.MediaRecorder} className="btn btn-ghost h-12 w-full px-5 text-lg disabled:opacity-60">
                <FilmStrip aria-hidden className="size-5" /> {grabando ? 'Grabando el vídeo…' : 'Descargar vídeo (6 s)'}
              </button>
              <p className="text-sm text-muted">El vídeo se graba en tu navegador mientras las barras suben. Si sale en .webm y la red no lo acepta, súbelo como imagen.</p>
            </div>
          </div>
        )}
      </div>
    </Pagina>
  )
}
