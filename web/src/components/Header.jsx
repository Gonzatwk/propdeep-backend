import { NavLink } from 'react-router-dom'
import Cta from './Cta'
import Logo from './Logo'

const link = 'px-2.5 py-1.5 text-sm font-medium text-muted transition-colors hover:text-ink'

export default function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-ink bg-bg/92 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Logo />
        <nav aria-label="Principal" className="flex items-center gap-1">
          <a href="/#como-funciona" className={`${link} hidden md:inline-block`}>Cómo funciona</a>
          <NavLink to="/historial" className={({ isActive }) => `${link} ${isActive ? 'text-ink underline decoration-hot decoration-2 underline-offset-[6px]' : ''}`}>Historial</NavLink>
          <a href="/#precio" className={`${link} hidden sm:inline-block`}>Precio</a>
          <span className="tnum mx-1.5 border border-ink px-1.5 py-0.5 text-xs font-bold" title="Solo mayores de 18 años">+18</span>
          <Cta size="sm" className="ml-1 hidden sm:inline-flex">Reservar</Cta>
        </nav>
      </div>
    </header>
  )
}
