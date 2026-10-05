import { Link } from 'react-router-dom'
import { hexPoints } from '../lib/hex'

export default function Logo({ inverso = false }) {
  return (
    <Link to="/" className="flex items-center gap-2" aria-label="PropDeep, inicio">
      <svg viewBox="0 0 28 30" className="h-7 w-[26px]" aria-hidden>
        <polygon points={hexPoints(14, 15, 14)} fill={inverso ? 'var(--on-ink)' : 'var(--ink)'} />
        <polygon points={hexPoints(14, 15, 6.5)} fill="var(--hot)" />
      </svg>
      <span className="display text-[1.6rem] tracking-[0.01em]">PropDeep</span>
    </Link>
  )
}
