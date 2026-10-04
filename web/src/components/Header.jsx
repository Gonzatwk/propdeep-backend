import { Link } from 'react-router-dom'
import Logo from './Logo'

export default function Header() {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Logo />
        <nav className="flex items-center gap-4 text-sm text-slate-300 sm:gap-6">
          <a href="/#ejemplos" className="hidden hover:text-white sm:inline">Ejemplos</a>
          <Link to="/historial" className="hover:text-white">Historial</Link>
          <a href="/#precio" className="hover:text-white">Precio</a>
          <span className="rounded-md border border-slate-600 px-2 py-0.5 text-xs font-bold text-slate-200">+18</span>
        </nav>
      </div>
    </header>
  )
}
