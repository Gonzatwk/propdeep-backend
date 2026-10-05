import { NavLink } from 'react-router-dom'
import Cta from './Cta'
import Logo from './Logo'

const link = 'rounded-full px-3 py-1.5 text-sm text-muted transition-colors hover:text-ink'

export default function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-line/70 bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Logo />
        <nav aria-label="Principal" className="flex items-center gap-1">
          <a href="/#como-funciona" className={`${link} hidden md:inline-block`}>Cómo funciona</a>
          <NavLink to="/historial" className={({ isActive }) => `${link} ${isActive ? 'text-ink' : ''}`}>Historial</NavLink>
          <a href="/#precio" className={`${link} hidden sm:inline-block`}>Precio</a>
          <span className="mx-1 rounded-md border border-line px-1.5 py-0.5 font-mono text-xs font-semibold" title="Solo mayores de 18 años">+18</span>
          <Cta size="sm" className="ml-1 hidden sm:inline-flex">Reservar</Cta>
        </nav>
      </div>
    </header>
  )
}
