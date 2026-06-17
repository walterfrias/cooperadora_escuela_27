import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { TenantProvider } from './contex/TenantContext';
import { AuthProvider } from './contex/UserContex';
import Header from './components/Header';
import HomePages from './pages/HomePages';
import LoginFormPages from './pages/LoginFormPages';
import PagosPage from './pages/PagosPage';
import PublicacionesPage from './pages/PublicacionesPage';
import EstadoCuentaPage from './pages/EstadoCuentaPage';
import MisHijosPage from './pages/MisHijosPage';
import UsuariosPage from './pages/UsuariosPage';
import PerfilPage from './pages/PerfilPage';
import CuotasPage from './pages/CuotasPage';
import SuscripcionBloqueadaPage from './pages/SuscripcionBloqueadaPage';
import RegistroCooperadoraPage from './pages/RegistroCooperadoraPage';
import RegistroFormPages from './pages/RegistroFormPages';
import ActivarCooperadoraPage from './pages/ActivarCooperadoraPage';

function App() {
  return (
    <BrowserRouter>
      <TenantProvider>
        <AuthProvider>
          <ToastContainer position="top-right" autoClose={5000} />
          <Header />
          <Routes>
            {/* Raíz → registro */}
            <Route path="/" element={<Navigate to="/register" replace />} />

            {/* Ruta pública — registro de cooperadoras */}
            <Route path="/register" element={<RegistroCooperadoraPage />} />

            {/* Rutas por tenant — /:slug/... */}
            <Route path="/:slug" element={<LoginFormPages />} />
            <Route path="/:slug/login" element={<LoginFormPages />} />
            <Route path="/:slug/about" element={<HomePages />} />
            <Route path="/:slug/pagos" element={<PagosPage />} />
            <Route path="/:slug/publicaciones" element={<PublicacionesPage />} />
            <Route path="/:slug/estado-cuenta" element={<EstadoCuentaPage />} />
            <Route path="/:slug/mis-hijos" element={<MisHijosPage />} />
            <Route path="/:slug/usuarios" element={<UsuariosPage />} />
            <Route path="/:slug/perfil" element={<PerfilPage />} />
            <Route path="/:slug/cuotas" element={<CuotasPage />} />
            <Route path="/:slug/registro" element={<RegistroFormPages />} />
            <Route path="/:slug/activar" element={<ActivarCooperadoraPage />} />
            <Route path="/:slug/suscripcion-bloqueada" element={<SuscripcionBloqueadaPage />} />
          </Routes>
        </AuthProvider>
      </TenantProvider>
    </BrowserRouter>
  );
}

export default App;
