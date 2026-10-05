import { ArrowLeft } from '@phosphor-icons/react'
import { Link } from 'react-router-dom'

export default function LegalLayout({ title, children }) {
  return (
    <article className="mx-auto max-w-3xl px-4 py-14 sm:px-6 md:py-20">
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
        <ArrowLeft aria-hidden className="size-4" /> Volver al inicio
      </Link>
      <h1 className="display mt-8 text-[3.2rem] sm:text-[4rem]">{title}</h1>
      <p className="mt-4 border-b border-ink pb-6 text-sm text-muted">Última actualización: 4 de octubre de 2026</p>
      <div className="mt-10 space-y-4 leading-relaxed text-ink-2 [&_a]:underline [&_a:hover]:text-hot [&_h2]:mt-10 [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-ink [&_strong]:text-ink [&_ul]:list-disc [&_ul]:space-y-2 [&_ul]:pl-6">
        {children}
      </div>
    </article>
  )
}
