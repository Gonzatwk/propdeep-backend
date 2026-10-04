import LegalLayout from '../components/LegalLayout'
import Pendiente from '../components/Pendiente'
import { CONTACT_EMAIL } from '../config'

export default function Privacidad() {
  const correo = CONTACT_EMAIL || <Pendiente>correo</Pendiente>
  return (
    <LegalLayout title="Política de privacidad">
      <h2>Responsable del tratamiento</h2>
      <p>
        <Pendiente>nombre y apellidos</Pendiente>, NIF <Pendiente>NIF</Pendiente>. Contacto: {correo}.
      </p>
      <h2>Qué datos tratamos y para qué</h2>
      <ul>
        <li>
          <strong>Pago de la suscripción:</strong> el pago lo gestiona Stripe. Nosotros recibimos tu nombre, correo y
          el estado del pago, nunca los datos completos de tu tarjeta. Base legal: ejecución del contrato.
        </li>
        <li>
          <strong>Contacto y reembolsos:</strong> si nos escribes, usamos tu correo y lo que nos cuentes solo para
          responderte. Base legal: tu consentimiento y, en reembolsos, la ejecución del contrato.
        </li>
        <li>
          <strong>Datos técnicos:</strong> el proveedor de alojamiento registra datos técnicos básicos (como la
          dirección IP) por seguridad. Base legal: interés legítimo.
        </li>
      </ul>
      <p>No pedimos más datos de los necesarios, no los vendemos y no hacemos perfiles publicitarios.</p>
      <h2>Proveedores</h2>
      <ul>
        <li>Stripe (pagos).</li>
        <li>Vercel (alojamiento de la web).</li>
      </ul>
      <p>
        Algunos de estos proveedores pueden tratar datos fuera del Espacio Económico Europeo, con las garantías que
        exige el RGPD (cláusulas contractuales tipo o marcos de adecuación).
      </p>
      <h2>Cuánto tiempo los guardamos</h2>
      <p>
        Mientras dure tu suscripción y, después, el tiempo que exijan las obligaciones legales y fiscales. Los
        mensajes de contacto, como máximo un año si no hay relación contractual.
      </p>
      <h2>Tus derechos</h2>
      <p>
        Puedes pedir acceso, rectificación, supresión, oposición, limitación y portabilidad escribiendo a {correo}.
        Si crees que no hemos atendido bien tu solicitud, puedes reclamar ante la Agencia Española de Protección de
        Datos (<a href="https://www.aepd.es" target="_blank" rel="noopener noreferrer">aepd.es</a>).
      </p>
      <h2>Menores</h2>
      <p>El servicio es solo para mayores de 18 años. No tratamos datos de menores de forma consciente.</p>
    </LegalLayout>
  )
}
