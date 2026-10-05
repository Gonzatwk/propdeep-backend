import LegalLayout from '../components/LegalLayout'
import { CONTACT_EMAIL, TITULAR } from '../config'

export default function Privacidad() {
  const correo = <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
  return (
    <LegalLayout title="Política de privacidad">
      <h2>Responsable del tratamiento</h2>
      <p>
        {TITULAR.nombre}, NIF {TITULAR.nif}, {TITULAR.domicilio}. Contacto: {correo}.
      </p>
      <h2>Qué datos tratamos y para qué</h2>
      <ul>
        <li>
          <strong>Aviso de apertura:</strong> si nos dejas tu correo en el formulario, lo usamos solo para escribirte
          cuando abra PropDeep. Base legal: tu consentimiento, que puedes retirar en cualquier momento escribiéndonos.
        </li>
        <li>
          <strong>Tu cuenta:</strong> para entrar solo pedimos tu correo; te mandamos un enlace de acceso y no hay
          contraseña. Guardamos el correo, la fecha de alta y el estado de tu suscripción. Puedes borrar la cuenta
          desde «Mi cuenta». Base legal: ejecución del contrato.
        </li>
        <li>
          <strong>Pago de la suscripción (cuando abra):</strong> el pago lo gestiona Stripe. Nosotros recibimos tu nombre, correo y
          el estado del pago, nunca los datos completos de tu tarjeta. Base legal: ejecución del contrato.
        </li>
        <li>
          <strong>Contacto:</strong> si nos escribes, usamos tu correo y lo que nos cuentes solo para
          responderte. Base legal: tu consentimiento.
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
        <li>El servidor de la API de PropDeep (cuentas y estado de la suscripción).</li>
        <li>El proveedor de correo con el que enviamos el enlace de acceso.</li>
        <li>Cloudflare (alojamiento de la web y almacenamiento de los correos del aviso de apertura).</li>
      </ul>
      <p>
        Algunos de estos proveedores pueden tratar datos fuera del Espacio Económico Europeo, con las garantías que
        exige el RGPD (cláusulas contractuales tipo o marcos de adecuación).
      </p>
      <h2>Cuánto tiempo los guardamos</h2>
      <p>
        Mientras dure tu suscripción y, después, el tiempo que exijan las obligaciones legales y fiscales. Los
        mensajes de contacto, como máximo un año si no hay relación contractual. Los correos del aviso de apertura,
        hasta que te avisemos y, como máximo, seis meses; después los borramos si no te has suscrito.
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
