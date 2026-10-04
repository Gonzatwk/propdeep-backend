export default function LegalLayout({ title, children }) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-14">
      <h1 className="mb-2 text-3xl font-bold tracking-tight text-white">{title}</h1>
      <p className="mb-8 text-sm text-slate-500">Última actualización: 4 de octubre de 2026</p>
      <div className="space-y-4 leading-relaxed text-slate-300 [&_h2]:mt-8 [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-white [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-6 [&_a]:underline">
        {children}
      </div>
    </div>
  )
}
