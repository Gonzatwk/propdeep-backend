import { useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Anuncio from './components/Anuncio'
import Cursor from './components/Cursor'
import Footer from './components/Footer'
import FondoPista from './components/FondoPista'
import Header from './components/Header'
import RelojPosesion from './components/RelojPosesion'
import AvisoLegal from './pages/AvisoLegal'
import Cookies from './pages/Cookies'
import Home from './pages/Home'
import MisPicks from './pages/MisPicks'
import NotFound from './pages/NotFound'
import Privacidad from './pages/Privacidad'
import Chat from './pages/zona/Chat'
import Cuenta from './pages/zona/Cuenta'
import Entrar from './pages/zona/Entrar'
import Informe from './pages/zona/Informe'
import Partido from './pages/zona/Partido'
import Partidos from './pages/zona/Partidos'
import { CuentaProvider } from './lib/cuenta'
import useReveal from './lib/useReveal'

// Zona de partidos y cuenta: sin campo de tiros ni reloj, para leer datos sin ruido.
const ZONA = ['/partidos', '/chat', '/entrar', '/cuenta', '/mis-picks']
const enZona = (ruta) => ZONA.some((z) => ruta === z || ruta.startsWith(`${z}/`))

function ScrollToTop() {
  const { pathname, hash } = useLocation()
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView()
    else window.scrollTo(0, 0)
  }, [pathname, hash])
  useReveal(pathname)
  return null
}

export default function App() {
  const zona = enZona(useLocation().pathname)
  return (
    <CuentaProvider>
    <div className="flex min-h-dvh flex-col">
      <a href="#contenido" className="sr-only z-50 bg-gold px-4 py-2 font-semibold text-black focus:not-sr-only focus:fixed focus:top-3 focus:left-3">
        Saltar al contenido
      </a>
      <ScrollToTop />
      {!zona && <FondoPista />}
      <Anuncio />
      <Header />
      <main id="contenido" className="relative z-10 flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/mis-picks" element={<MisPicks />} />
          <Route path="/historial" element={<Navigate to="/mis-picks" replace />} />
          <Route path="/partidos" element={<Partidos />} />
          <Route path="/partidos/:eventId" element={<Partido />} />
          <Route path="/partidos/:eventId/:lineId" element={<Informe />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/entrar" element={<Entrar />} />
          <Route path="/cuenta" element={<Cuenta />} />
          <Route path="/aviso-legal" element={<AvisoLegal />} />
          <Route path="/privacidad" element={<Privacidad />} />
          <Route path="/cookies" element={<Cookies />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
      {!zona && <RelojPosesion />}
      <Cursor />
    </div>
    </CuentaProvider>
  )
}
