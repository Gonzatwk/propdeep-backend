import { Link } from 'react-router-dom'
import { CONTACT_EMAIL } from '../config'
import Logo from './Logo'

export default function Footer() {
  return (
    <footer className="relative z-10 border-t border-line bg-black text-white">
      <div className="mx-auto max-w-6xl px-4 pt-14 pb-10 sm:px-6">
        <div className="grid gap-10 md:grid-cols-[1fr_1.5fr]">
          <div className="space-y-3">
            <Logo />
            <p className="max-w-xs text-sm text-muted">Análisis estadístico de player props de la NBA, en español.</p>
          </div>
          <section aria-label="Juego responsable" className="border border-white/50 p-5">
            <p className="flex items-start gap-3 text-[0.95rem] leading-relaxed">
              <span className="tnum mt-0.5 shrink-0 bg-gold px-1.5 py-0.5 text-xs font-bold text-black">+18</span>
              <span>
                PropDeep ofrece información estadística orientativa, sin garantía de ningún resultado: no son recomendaciones de apuesta ni consejos de inversión.
                Apostar implica riesgo de perder dinero. Juega con moderación y solo con lo que puedas permitirte perder.
                Si el juego deja de ser un entretenimiento, pide ayuda en{' '}
                <a href="https://www.jugarbien.es" target="_blank" rel="noopener noreferrer" className="font-semibold underline">jugarbien.es</a>.
              </span>
            </p>
          </section>
        </div>
        <div className="mt-12 flex flex-col gap-4 border-t border-white/30 pt-6 text-sm text-muted md:flex-row md:items-center md:justify-between">
          <nav aria-label="Legal" className="flex flex-wrap gap-x-5 gap-y-2">
            <Link to="/aviso-legal" className="hover:text-gold">Aviso legal</Link>
            <Link to="/privacidad" className="hover:text-gold">Privacidad</Link>
            <Link to="/cookies" className="hover:text-gold">Cookies</Link>
            <a href={`mailto:${CONTACT_EMAIL}`} className="hover:text-gold">{CONTACT_EMAIL}</a>
          </nav>
          <p>PropDeep no está afiliado a la NBA ni a ningún operador de apuestas.</p>
        </div>
      </div>
    </footer>
  )
}
