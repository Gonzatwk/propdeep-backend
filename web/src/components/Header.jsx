import { useEffect, useRef } from 'react'
import { NavLink } from 'react-router-dom'
import { UserCircle } from '@phosphor-icons/react'
import { useCuenta } from '../lib/cuenta'
import Cta from './Cta'
import Logo from './Logo'

const link = 'whitespace-nowrap px-1.5 py-1.5 text-sm min-[380px]:px-2 sm:px-2.5 font-semibold text-muted transition-colors hover:text-gold'
const activo = ({ isActive }) => `${link} ${isActive ? 'text-white underline decoration-gold decoration-2 underline-offset-[6px]' : ''}`

// Línea dorada bajo la cabecera que avanza con el scroll, con un balón en la punta.
function Progreso() {
  const ref = useRef(null)
  useEffect(() => {
    let raf = 0
    const actualizar = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const max = document.documentElement.scrollHeight - innerHeight
        ref.current?.style.setProperty('--p', max > 0 ? Math.min(1, scrollY / max).toFixed(4) : '0')
      })
    }
    actualizar()
    addEventListener('scroll', actualizar, { passive: true })
    addEventListener('resize', actualizar)
    return () => {
      cancelAnimationFrame(raf)
      removeEventListener('scroll', actualizar)
      removeEventListener('resize', actualizar)
    }
  }, [])
  return (
    <div ref={ref} aria-hidden className="progreso pointer-events-none absolute inset-x-0 -bottom-px h-[3px]">
      <div className="progreso-linea h-full bg-gold" />
      <svg viewBox="0 0 30 30" className="progreso-balon absolute -top-[6.5px] size-4">
        <circle cx="15" cy="15" r="13" fill="var(--gold)" stroke="var(--black)" strokeWidth="2" />
        <path d="M2 15H28M15 2V28M5.5 6.5C10 10 10 20 5.5 23.5M24.5 6.5C20 10 20 20 24.5 23.5" fill="none" stroke="var(--black)" strokeWidth="2" />
      </svg>
    </div>
  )
}

export default function Header() {
  const { usuario } = useCuenta()
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-black/80 text-white backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-1 px-4 min-[380px]:gap-2 sm:gap-4 sm:px-6">
        <Logo />
        <nav aria-label="Principal" className="flex items-center sm:gap-1">
          <a href="/#como-funciona" className={`${link} hidden lg:inline-block`}>Cómo funciona</a>
          <NavLink to="/partidos" className={activo}>Partidos</NavLink>
          <NavLink to="/chat" className={(e) => `${activo(e)} hidden md:inline-block`}>Chat</NavLink>
          <NavLink to="/mis-picks" className={activo}>Mis picks</NavLink>
          <a href="/#precio" className={`${link} hidden md:inline-block`}>Precio</a>
          <NavLink to={usuario ? '/cuenta' : '/entrar'} className={activo} aria-label={usuario ? 'Mi cuenta' : 'Entrar'}>
            <UserCircle aria-hidden className="size-5 sm:hidden" />
            <span className="hidden sm:inline">{usuario ? 'Cuenta' : 'Entrar'}</span>
          </NavLink>
          <span className="tnum ml-0.5 border-2 min-[380px]:ml-1 sm:mx-1.5 border-white px-1.5 py-0.5 text-xs font-bold" title="Solo mayores de 18 años">+18</span>
          <Cta size="sm" className="ml-1 hidden sm:inline-flex">Avísame</Cta>
        </nav>
      </div>
      <Progreso />
    </header>
  )
}
