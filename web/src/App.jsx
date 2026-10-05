import { useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import Anuncio from './components/Anuncio'
import Cursor from './components/Cursor'
import Footer from './components/Footer'
import FondoPista from './components/FondoPista'
import Header from './components/Header'
import RelojPosesion from './components/RelojPosesion'
import AvisoLegal from './pages/AvisoLegal'
import Cookies from './pages/Cookies'
import HistorialPage from './pages/HistorialPage'
import Home from './pages/Home'
import NotFound from './pages/NotFound'
import Privacidad from './pages/Privacidad'
import useReveal from './lib/useReveal'

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
  return (
    <div className="flex min-h-dvh flex-col">
      <a href="#contenido" className="sr-only z-50 bg-gold px-4 py-2 font-semibold text-black focus:not-sr-only focus:fixed focus:top-3 focus:left-3">
        Saltar al contenido
      </a>
      <ScrollToTop />
      <FondoPista />
      <Anuncio />
      <Header />
      <main id="contenido" className="relative z-10 flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/historial" element={<HistorialPage />} />
          <Route path="/aviso-legal" element={<AvisoLegal />} />
          <Route path="/privacidad" element={<Privacidad />} />
          <Route path="/cookies" element={<Cookies />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
      <RelojPosesion />
      <Cursor />
    </div>
  )
}
