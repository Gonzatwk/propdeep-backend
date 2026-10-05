import LegalLayout from '../components/LegalLayout'

export default function Cookies() {
  return (
    <LegalLayout title="Política de cookies">
      <p>
        Esta web no usa cookies de análisis, publicidad ni seguimiento, y no carga servicios de terceros que las
        instalen. Por eso no te mostramos un aviso de cookies.
      </p>
      <h2>Almacenamiento local para mantener la sesión</h2>
      <p>
        Si entras en tu cuenta, guardamos en tu navegador (almacenamiento local, no una cookie) un identificador de sesión
        para que no tengas que entrar cada vez. Es estrictamente necesario para el servicio que pides, no sirve para
        seguirte y se borra al cerrar sesión.
      </p>
      <h2>Cookies de terceros al pagar</h2>
      <p>
        Cuando abra la suscripción, el pago se hará en la página de Stripe. Stripe puede usar cookies
        técnicas necesarias para procesar el pago de forma segura y prevenir el fraude. Puedes consultar su política
        en <a href="https://stripe.com/es/legal/cookies-policy" target="_blank" rel="noopener noreferrer">stripe.com</a>.
      </p>
      <h2>Cambios</h2>
      <p>
        Si en el futuro añadimos cookies que no sean estrictamente necesarias, actualizaremos esta política y te
        pediremos el consentimiento antes de instalarlas.
      </p>
    </LegalLayout>
  )
}
