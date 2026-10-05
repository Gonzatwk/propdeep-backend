import { ArrowLeft } from '@phosphor-icons/react'
import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-24 text-center sm:px-6">
      <p className="display tnum text-[8rem] text-c1">404</p>
      <h1 className="display mt-4 text-[3rem]">Tiro fuera</h1>
      <p className="mt-4 text-muted">Esta página no existe. Puede que el enlace esté mal escrito o que la página se haya movido.</p>
      <Link to="/" className="btn btn-primary mt-8 h-12 px-6 text-lg">
        <ArrowLeft aria-hidden className="size-4" /> Volver al inicio
      </Link>
    </div>
  )
}
