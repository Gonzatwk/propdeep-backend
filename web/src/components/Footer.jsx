import { Link } from 'react-router-dom'
import { CONTACT_EMAIL } from '../config'

export default function Footer() {
  return (
    <footer className="border-t border-slate-800 bg-slate-950">
      <div className="mx-auto max-w-6xl space-y-6 px-4 py-10 text-sm text-slate-400">
        <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-base text-amber-100">
          <strong className="mr-1 rounded bg-amber-400 px-1.5 py-0.5 text-sm font-bold text-slate-950">+18</strong>{' '}
          PropDeep ofrece análisis estadístico con fines informativos, no consejos de inversión ni apuestas seguras.
          Apostar implica riesgo de perder dinero. Juega con moderación y solo con lo que puedas permitirte perder.
          Si el juego deja de ser un entretenimiento, pide ayuda en{' '}
          <a href="https://www.jugarbien.es" target="_blank" rel="noopener noreferrer" className="font-semibold underline">
            jugarbien.es
          </a>
          .
        </div>
        <nav className="flex flex-wrap gap-x-4 gap-y-2">
          <Link to="/aviso-legal" className="hover:text-white">Aviso legal</Link>
          <Link to="/privacidad" className="hover:text-white">Política de privacidad</Link>
          <Link to="/cookies" className="hover:text-white">Política de cookies</Link>
          <span>
            Contacto:{' '}
            {CONTACT_EMAIL ? (
              <a href={`mailto:${CONTACT_EMAIL}`} className="hover:text-white">{CONTACT_EMAIL}</a>
            ) : (
              <span className="text-slate-500">[correo pendiente]</span>
            )}
          </span>
        </nav>
        <p>PropDeep no está afiliado a la NBA ni a ningún operador de apuestas.</p>
      </div>
    </footer>
  )
}
