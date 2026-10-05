import { Link } from 'react-router-dom'
import { CONTACT_EMAIL } from '../config'
import Logo from './Logo'

export default function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto max-w-6xl px-4 pt-14 pb-10 sm:px-6">
        <div className="grid gap-10 md:grid-cols-[1fr_1.4fr]">
          <div className="space-y-3">
            <Logo />
            <p className="max-w-xs text-sm text-muted">Análisis estadístico de player props de la NBA, en español.</p>
          </div>
          <section aria-label="Juego responsable" className="rounded-2xl bg-warn-bg p-5 text-warn-text">
            <p className="flex items-start gap-3 text-[0.95rem] leading-relaxed">
              <span className="mt-0.5 shrink-0 rounded-md bg-warn-text px-1.5 py-0.5 font-mono text-xs font-bold text-warn-bg">+18</span>
              <span>
                PropDeep ofrece análisis estadístico con fines informativos, no consejos de inversión ni apuestas seguras.
                Apostar implica riesgo de perder dinero. Juega con moderación y solo con lo que puedas permitirte perder.
                Si el juego deja de ser un entretenimiento, pide ayuda en{' '}
                <a href="https://www.jugarbien.es" target="_blank" rel="noopener noreferrer" className="font-semibold underline">jugarbien.es</a>.
              </span>
            </p>
          </section>
        </div>
        <div className="mt-12 flex flex-col gap-4 border-t border-line pt-6 text-sm text-muted md:flex-row md:items-center md:justify-between">
          <nav aria-label="Legal" className="flex flex-wrap gap-x-5 gap-y-2">
            <Link to="/aviso-legal" className="hover:text-ink">Aviso legal</Link>
            <Link to="/privacidad" className="hover:text-ink">Privacidad</Link>
            <Link to="/cookies" className="hover:text-ink">Cookies</Link>
            <a href={`mailto:${CONTACT_EMAIL}`} className="hover:text-ink">{CONTACT_EMAIL}</a>
          </nav>
          <p>PropDeep no está afiliado a la NBA ni a ningún operador de apuestas.</p>
        </div>
      </div>
    </footer>
  )
}
