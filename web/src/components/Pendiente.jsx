// Marca visible para datos que Gonza debe completar antes de publicar.
export default function Pendiente({ children }) {
  return <mark className="rounded bg-amber-400/20 px-1 text-amber-200">[{children}]</mark>
}
