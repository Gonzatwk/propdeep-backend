import LegalLayout from '../components/LegalLayout'
import { CONTACT_EMAIL, TITULAR } from '../config'

export default function AvisoLegal() {
  return (
    <LegalLayout title="Aviso legal">
      <h2>Titular del sitio web</h2>
      <p>En cumplimiento de la Ley 34/2002 de servicios de la sociedad de la información (LSSI-CE):</p>
      <ul>
        <li>Titular: {TITULAR.nombre}</li>
        <li>NIF: {TITULAR.nif}</li>
        <li>Domicilio: {TITULAR.domicilio}</li>
        <li>Correo electrónico: <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a></li>
      </ul>
      <h2>Objeto</h2>
      <p>
        PropDeep ofrece análisis estadístico de player props de la NBA con fines exclusivamente informativos. No es
        un operador de juego, no acepta apuestas y no está afiliado a la NBA ni a ningún operador de apuestas. Los
        análisis no son recomendaciones de apuesta ni de inversión, ni garantizan ningún resultado.
      </p>
      <h2>Mayoría de edad</h2>
      <p>El servicio está dirigido exclusivamente a mayores de 18 años.</p>
      <h2>Responsabilidad</h2>
      <p>
        Las decisiones que tome cada usuario a partir de los análisis son de su exclusiva responsabilidad. Apostar
        implica riesgo de perder dinero. Si el juego deja de ser un entretenimiento, pide ayuda en{' '}
        <a href="https://www.jugarbien.es" target="_blank" rel="noopener noreferrer">jugarbien.es</a>.
      </p>
      <h2>Propiedad intelectual</h2>
      <p>
        Los textos, análisis y diseño de este sitio pertenecen a su titular. Los nombres de equipos y jugadores se
        usan solo con fines descriptivos.
      </p>
    </LegalLayout>
  )
}
