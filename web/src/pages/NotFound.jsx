import { ArrowLeft } from '@phosphor-icons/react'
import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-28 text-center sm:px-6">
      <p className="tnum font-mono text-sm text-muted">404</p>
      <h1 className="mt-4 text-4xl font-semibold tracking-[-0.035em]">Esta página no existe</h1>
      <p className="mt-4 text-muted">Puede que el enlace esté mal escrito o que la página se haya movido.</p>
      <Link to="/" className="btn btn-primary mt-8 px-5 py-3">
        <ArrowLeft aria-hidden className="size-4" /> Volver al inicio
      </Link>
    </div>
  )
}
