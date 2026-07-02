import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contex/UserContex';
import { useTenant } from '../contex/TenantContext';
import { API_URL } from '../config';
import { toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';

type TipoUsuario = 'PAD' | 'SOC' | 'MIE';

const ROLES_MIEMBRO = [
  { value: 'ADMIN', label: 'Administrador' },
  { value: 'PRES',  label: 'Presidente' },
  { value: 'TES',   label: 'Tesorero' },
  { value: 'SEC',   label: 'Secretario' },
  { value: 'REV',   label: 'Revisor de Cuentas' },
  { value: 'DOC',   label: 'Docente' },
  { value: 'MIE',   label: 'Miembro' },
];

interface Grado {
  id: number;
  numero: number;
  letra: string;
}

interface ApiErrors {
  [key: string]: string[] | string | undefined;
}

const RegistroForm: React.FC = () => {
  const { registro, isTesorero, isAdmin, isPresidente, authFetch } = useAuth();
  const { slug } = useTenant();
  const navigate = useNavigate();

  const [tipo, setTipo] = useState<TipoUsuario>('PAD');
  const [nombre, setNombre] = useState('');
  const [apellido, setApellido] = useState('');
  const [dni, setDni] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [telefono, setTelefono] = useState('');
  const [rolMiembro, setRolMiembro] = useState('TES');
  const [dniPadre, setDniPadre] = useState('');
  const [gradoId, setGradoId] = useState('');
  const [anio, setAnio] = useState(new Date().getFullYear().toString());
  const [modalidad, setModalidad] = useState<'mensual' | 'anual'>('mensual');

  const [loading, setLoading] = useState(false);
  const [apiErrors, setApiErrors] = useState<ApiErrors>({});
  const [grados, setGrados] = useState<Grado[]>([]);

  if (!isTesorero && !isAdmin && !isPresidente) {
    navigate(`/${slug}/login`);
    return null;
  }

  const fetchGrados = async () => {
    if (grados.length > 0) return;
    try {
      const res = await authFetch(`${API_URL}/api/grados/`);
      if (res.ok) setGrados(await res.json());
    } catch {}
  };

  const handleTipoChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const t = e.target.value as TipoUsuario;
    setTipo(t);
    setApiErrors({});
    if (t === 'SOC') fetchGrados();
  };

  const getError = (field: string): string | undefined => {
    const e = apiErrors[field];
    return Array.isArray(e) ? e[0] : typeof e === 'string' ? e : undefined;
  };

  const inputClass = (field: string) =>
    `w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-1 dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 transition-colors ${
      getError(field)
        ? 'border-red-400 dark:border-red-500'
        : 'border-gray-300 dark:border-gray-600'
    }`;

  const passwordChecks = [
    { label: 'Mínimo 8 caracteres',       ok: password.length >= 8 },
    { label: 'No puede ser solo números', ok: password.length > 0 && !/^\d+$/.test(password) },
    { label: 'Las contraseñas coinciden', ok: confirmPassword.length > 0 && password === confirmPassword },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((tipo === 'PAD' || tipo === 'MIE') && password !== confirmPassword) {
      setApiErrors({ password: ['Las contraseñas no coinciden.'] });
      return;
    }
    setApiErrors({});
    setLoading(true);
    try {
      let payload: Record<string, any> = { nombre, apellido, dni };

      if (tipo === 'PAD') {
        payload = { ...payload, rol: 'PAD', email, password, telefono };
      } else if (tipo === 'SOC') {
        payload = { ...payload, rol: 'SOC', ...(dniPadre ? { dni_padre: dniPadre } : {}), grado_id: parseInt(gradoId), anio: parseInt(anio), modalidad };
      } else {
        payload = { ...payload, rol: rolMiembro, email, password, telefono };
      }

      const result = await registro(payload as Parameters<typeof registro>[0]);
      if (result.success) {
        const labels: Record<TipoUsuario, string> = { PAD: 'Padre/Tutor', SOC: 'Alumno', MIE: 'Miembro' };
        toast.success(`${labels[tipo]} creado correctamente.`);
        navigate(`/${slug}/about`);
      } else {
        if (result.error) {
          setApiErrors(result.error);
          if (result.error.general) toast.error(result.error.general);
        } else {
          toast.error('Error al crear el usuario. Intentá de nuevo.');
        }
      }
    } catch {
      toast.error('Ocurrió un error inesperado.');
    } finally {
      setLoading(false);
    }
  };

  const submitLabel =
    tipo === 'PAD' ? 'Crear padre/tutor' :
    tipo === 'SOC' ? 'Crear alumno' :
    `Crear ${ROLES_MIEMBRO.find(r => r.value === rolMiembro)?.label ?? 'miembro'}`;

  return (
    <div className="min-h-screen bg-gradient-to-b from-cyan-100 dark:from-gray-900 to-white dark:to-gray-900 flex flex-col items-center justify-start pt-12">
      <div className="max-w-md w-full mx-auto p-6 bg-white dark:bg-gray-800 rounded-lg shadow-md">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Crear usuario</h2>
        <form onSubmit={handleSubmit} className="space-y-4">

          {/* Tipo */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Tipo de usuario *</label>
            <select value={tipo} onChange={handleTipoChange} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-1 dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition-colors">
              <option value="PAD">Padre / Tutor</option>
              <option value="SOC">Alumno (Socio)</option>
              <option value="MIE">Miembro de la cooperadora</option>
            </select>
          </div>

          {/* Rol (solo miembro) */}
          {tipo === 'MIE' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Rol *</label>
              <select value={rolMiembro} onChange={(e) => setRolMiembro(e.target.value)} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-1 dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition-colors">
                {ROLES_MIEMBRO.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>
          )}

          {/* Campos comunes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nombre *</label>
            <input type="text" value={nombre} onChange={(e) => setNombre(e.target.value)} required className={inputClass('nombre')} />
            {getError('nombre') && <p className="mt-1 text-xs text-red-600">{getError('nombre')}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Apellido *</label>
            <input type="text" value={apellido} onChange={(e) => setApellido(e.target.value)} required className={inputClass('apellido')} />
            {getError('apellido') && <p className="mt-1 text-xs text-red-600">{getError('apellido')}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">DNI *</label>
            <input type="text" value={dni} onChange={(e) => setDni(e.target.value)} required className={inputClass('dni')} />
            {getError('dni') && <p className="mt-1 text-xs text-red-600">{getError('dni')}</p>}
          </div>

          {/* PAD y MIE: email + password + telefono */}
          {(tipo === 'PAD' || tipo === 'MIE') && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email *</label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className={inputClass('email')} />
                {getError('email') && <p className="mt-1 text-xs text-red-600">{getError('email')}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Contraseña *</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8}
                    className={`${inputClass('password')} pr-10`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    tabIndex={-1}
                  >
                    {showPassword
                      ? <EyeSlashIcon className="h-4 w-4" />
                      : <EyeIcon className="h-4 w-4" />
                    }
                  </button>
                </div>
                {getError('password') && <p className="mt-1 text-xs text-red-600">{getError('password')}</p>}

                {/* Requisitos en tiempo real */}
                {password.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {passwordChecks.map((check) => (
                      <li key={check.label} className={`flex items-center gap-1.5 text-xs ${check.ok ? 'text-green-600 dark:text-green-400' : 'text-gray-400 dark:text-gray-500'}`}>
                        <span className={`inline-block w-3.5 h-3.5 rounded-full border text-center leading-3 text-[10px] font-bold ${check.ok ? 'bg-green-500 border-green-500 text-white' : 'border-gray-300 dark:border-gray-600'}`}>
                          {check.ok ? '✓' : ''}
                        </span>
                        {check.label}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Repetir contraseña *</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-1 dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 transition-colors pr-10 ${
                      confirmPassword.length > 0 && password !== confirmPassword ? 'border-red-400 dark:border-red-500' : 'border-gray-300 dark:border-gray-600'
                    }`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    tabIndex={-1}
                  >
                    {showPassword
                      ? <EyeSlashIcon className="h-4 w-4" />
                      : <EyeIcon className="h-4 w-4" />
                    }
                  </button>
                </div>
                {confirmPassword.length > 0 && password !== confirmPassword && (
                  <p className="mt-1 text-xs text-red-500">Las contraseñas no coinciden.</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Teléfono</label>
                <input type="tel" value={telefono} onChange={(e) => setTelefono(e.target.value)} className={inputClass('telefono')} />
                {getError('telefono') && <p className="mt-1 text-xs text-red-600">{getError('telefono')}</p>}
              </div>
            </>
          )}

          {/* SOC: email padre + grado + año + modalidad */}
          {tipo === 'SOC' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">DNI del padre/tutor</label>
                <input type="text" value={dniPadre} onChange={(e) => setDniPadre(e.target.value)} placeholder="Opcional, se puede asignar luego" className={inputClass('dni_padre')} />
                {getError('dni_padre') && <p className="mt-1 text-xs text-red-600">{getError('dni_padre')}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Grado *</label>
                <select value={gradoId} onChange={(e) => setGradoId(e.target.value)} required className={inputClass('grado_id')}>
                  <option value="">Seleccionar grado...</option>
                  {grados.map((g) => <option key={g.id} value={g.id}>{g.numero}° {g.letra}</option>)}
                </select>
                {getError('grado_id') && <p className="mt-1 text-xs text-red-600">{getError('grado_id')}</p>}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Año *</label>
                  <input type="number" value={anio} onChange={(e) => setAnio(e.target.value)} required min="2020" max="2099" className={inputClass('anio')} />
                  {getError('anio') && <p className="mt-1 text-xs text-red-600">{getError('anio')}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Modalidad *</label>
                  <select value={modalidad} onChange={(e) => setModalidad(e.target.value as 'mensual' | 'anual')} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-1 dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 transition-colors">
                    <option value="mensual">Mensual</option>
                    <option value="anual">Anual</option>
                  </select>
                </div>
              </div>
            </>
          )}

          <button type="submit" disabled={loading} className="w-full bg-cyan-500 text-white py-2 px-4 rounded-md text-sm hover:bg-cyan-600 transition-colors disabled:bg-cyan-300 disabled:cursor-not-allowed">
            {loading ? 'Creando...' : submitLabel}
          </button>
        </form>
      </div>
    </div>
  );
};

export default RegistroForm;
