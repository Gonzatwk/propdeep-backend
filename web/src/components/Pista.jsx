// Líneas de media pista NBA a escala (10 unidades = 1 pie), aro arriba.
export default function Pista({ dibujar = false }) {
  const cls = dibujar ? 'trazo' : undefined
  return (
    <g stroke="var(--court)" strokeWidth="1.3" fill="none">
      <path className={cls} pathLength="1" d="M0 1H500" />
      <path className={cls} pathLength="1" d="M170 0V190H330V0" />
      <path className={cls} pathLength="1" d="M190 0V190M310 0V190" strokeOpacity="0.6" />
      <circle className={cls} pathLength="1" cx="250" cy="190" r="60" />
      <path className={cls} pathLength="1" d="M30 0V142A237.5 237.5 0 0 0 470 142V0" />
      <path className={cls} pathLength="1" d="M210 52.5A40 40 0 0 0 290 52.5" />
      <path className={cls} pathLength="1" d="M190 470A60 60 0 0 1 310 470" />
      <path className={cls} pathLength="1" d="M0 469H500" />
      <path d="M220 40H280" stroke="var(--white)" strokeWidth="2.6" />
      <circle cx="250" cy="52.5" r="7.5" stroke="var(--gold)" strokeWidth="2.2" />
    </g>
  )
}
