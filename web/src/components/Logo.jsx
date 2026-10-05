import { Link } from 'react-router-dom'

export default function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2" aria-label="PropDeep, inicio">
      <svg viewBox="0 0 30 30" className="size-7" aria-hidden>
        <circle cx="15" cy="15" r="13" fill="none" stroke="var(--white)" strokeWidth="2" />
        <path d="M2 15H28M15 2V28M5.5 6.5C10 10 10 20 5.5 23.5M24.5 6.5C20 10 20 20 24.5 23.5" fill="none" stroke="var(--white)" strokeWidth="1.6" />
        <circle cx="15" cy="15" r="5" fill="var(--gold)" />
      </svg>
      <span className="display text-[1.7rem] tracking-[0.01em]">PropDeep</span>
    </Link>
  )
}
