import { Link } from 'react-router-dom'

export default function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2 font-bold tracking-tight text-white">
      <img src="/favicon.svg" alt="" className="h-7 w-7" />
      <span className="text-lg">
        Prop<span className="text-brand">Deep</span>
      </span>
    </Link>
  )
}
