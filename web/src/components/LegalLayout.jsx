import { ArrowLeft } from '@phosphor-icons/react'
import { Link } from 'react-router-dom'

export default function LegalLayout({ title, children }) {
  return (
    <article className="panel mx-auto my-10 max-w-3xl px-5 py-12 sm:px-10 md:my-16 md:py-16">
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-white">
        <ArrowLeft aria-hidden className="size-4" /> Volver al inicio
      </Link>
      <h1 className="display mt-8 text-[3.2rem] sm:text-[4rem]">{title}</h1>
      <p className="mt-4 border-b border-white pb-6 text-sm text-muted">Última actualización: 4 de octubre de 2026</p>
      <div className="mt-10 space-y-4 leading-relaxed text-white [&_a]:underline [&_a:hover]:text-gold [&_h2]:mt-10 [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-white [&_strong]:text-white [&_ul]:list-disc [&_ul]:space-y-2 [&_ul]:pl-6">
        {children}
      </div>
    </article>
  )
}
