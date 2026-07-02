import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contex/UserContex';
import { useTenant } from '../contex/TenantContext';
import { API_URL } from '../config';

import { toast } from 'react-toastify';

interface Usuario {
  uuid: string;
  nombre: string;
  apellido: string;
  email: string | null;
  dni: string;
  rol: string;
  telefono: string;
  activo: boolean;
  fecha_registro: string;
  padre_email: string | null;
  padre_dni: string | null;
  padre_nombre: string | null;
  padre_apellido: string | null;
}

type EditForm = Pick<Usuario, 'nombre' | 'apellido' | 'email' | 'dni' | 'rol' | 'telefono' | 'activo'> & {
  dni_padre?: string;
};

const ROL_LABELS: Record<string, string> = {
  ADMIN: 'Administrador',
  PRES: 'Presidente',
  TES: 'Tesorero',
  SEC: 'Secretario',
  REV: 'Revisor de Cuentas',
  DOC: 'Docente',
  SOC: 'Socio',
  PAD: 'Padre',
  MIE: 'Miembro',
};

const ROL_COLOR: Record<string, string> = {
  ADMIN: 'bg-red-100 text-red-700',
  TES: 'bg-blue-100 text-blue-700',
  SEC: 'bg-green-100 text-green-700',
  PAD: 'bg-yellow-100 text-yellow-700',
  SOC: 'bg-cyan-100 text-cyan-600',
  PRES: 'bg-orange-100 text-orange-700',
  REV: 'bg-pink-100 text-pink-700',
  DOC: 'bg-teal-100 text-teal-700',
  MIE: 'bg-gray-100 text-gray-700',
};

const UsuariosPage: React.FC = () => {
  const { authFetch, isAdmin, isPresidente, isTesorero } = useAuth();
  const { slug } = useTenant();
  const navigate = useNavigate();
  const canManage = isAdmin || isTesorero || isPresidente;

  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);
  const [busqueda, setBusqueda] = useState('');
  const [filtroRol, setFiltroRol] = useState('');

  const [detalle, setDetalle] = useState<Usuario | null>(null);
  const [editando, setEditando] = useState(false);
  const [form, setForm] = useState<EditForm | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [confirmarEliminar, setConfirmarEliminar] = useState<Usuario | null>(null);

  const fetchUsuarios = async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API_URL}/api/usuarios/`);
      const data = await res.json();
      setUsuarios(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsuarios(); }, []);

  const abrirDetalle = (u: Usuario) => {
    setDetalle(u);
    setEditando(false);
    setForm(null);
  };

  const abrirEdicion = (u: Usuario) => {
    setForm({
      nombre: u.nombre,
      apellido: u.apellido,
      email: u.email ?? '',
      dni: u.dni,
      rol: u.rol,
      telefono: u.telefono,
      activo: u.activo,
      ...(u.rol === 'SOC' ? { dni_padre: u.padre_dni ?? '' } : {}),
    });
    setEditando(true);
  };

  const guardar = async () => {
    if (!detalle || !form) return;
    setGuardando(true);
    try {
      const res = await authFetch(`${API_URL}/api/usuarios/${detalle.uuid}/`, {
        method: 'PATCH',
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const err = await res.json();
        toast.error(Object.values(err).flat().join(' '));
        return;
      }
      const actualizado = await res.json();
      setUsuarios((prev) => prev.map((u) => u.uuid === detalle.uuid ? actualizado : u));
      setDetalle(actualizado);
      setEditando(false);
      toast.success('Usuario actualizado');
    } finally {
      setGuardando(false);
    }
  };

  const eliminar = async (uuid: string) => {
    const res = await authFetch(`${API_URL}/api/usuarios/${uuid}/`, { method: 'DELETE' });
    if (res.ok) {
      setUsuarios((prev) => prev.filter((u) => u.uuid !== uuid));
      setDetalle(null);
      setConfirmarEliminar(null);
      toast.success('Usuario eliminado');
    } else {
      toast.error('No se pudo eliminar el usuario');
    }
  };

  const usuariosFiltrados = usuarios.filter((u) => {
    const texto = busqueda.toLowerCase();
    const coincideTexto =
      !texto ||
      u.nombre.toLowerCase().includes(texto) ||
      u.apellido.toLowerCase().includes(texto) ||
      u.dni.includes(texto) ||
      (u.email ?? '').toLowerCase().includes(texto);
    const coincideRol = !filtroRol || u.rol === filtroRol;
    return coincideTexto && coincideRol;
  });

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">

      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">Usuarios</h1>
          {canManage && (
            <button
              onClick={() => navigate(`/${slug}/registro`)}
              className="bg-cyan-500 hover:bg-cyan-600 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            >
              + Crear usuario
            </button>
          )}
        </div>

        {/* Filtros */}
        <div className="flex flex-col sm:flex-row gap-3 mb-5">
          <input
            type="text"
            placeholder="Buscar por nombre, apellido, DNI o email..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="flex-1 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
          />
          <select
            value={filtroRol}
            onChange={(e) => setFiltroRol(e.target.value)}
            className="border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
          >
            <option value="">Todos los roles</option>
            {Object.entries(ROL_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>

        {/* Lista */}
        {loading ? (
          <p className="text-center text-gray-500 dark:text-gray-400 dark:text-gray-500 mt-12">Cargando...</p>
        ) : usuariosFiltrados.length === 0 ? (
          <p className="text-center text-gray-400 dark:text-gray-500 mt-12">No hay usuarios que coincidan.</p>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 dark:border-gray-700 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-100 dark:border-gray-700 dark:border-gray-600">
                <tr>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Nombre</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide hidden sm:table-cell">DNI</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide hidden md:table-cell">Email</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Rol</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide hidden sm:table-cell">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-gray-700">
                {usuariosFiltrados.map((u) => (
                  <tr
                    key={u.uuid}
                    onClick={() => abrirDetalle(u)}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                  >
                    <td className="px-5 py-3.5 font-medium text-gray-800 dark:text-gray-100">
                      {u.apellido}, {u.nombre}
                    </td>
                    <td className="px-5 py-3.5 text-gray-500 hidden sm:table-cell">{u.dni}</td>
                    <td className="px-5 py-3.5 text-gray-500 hidden md:table-cell">{u.email ?? '—'}</td>
                    <td className="px-5 py-3.5">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${ROL_COLOR[u.rol] ?? 'bg-gray-100 text-gray-600'}`}>
                        {ROL_LABELS[u.rol] ?? u.rol}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 hidden sm:table-cell">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${u.activo ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'}`}>
                        {u.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-5 py-3 border-t border-gray-50 text-xs text-gray-400">
              {usuariosFiltrados.length} usuario{usuariosFiltrados.length !== 1 ? 's' : ''}
            </div>
          </div>
        )}
      </main>

      {/* Modal detalle / edición */}
      {detalle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
            {!editando ? (
              <>
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100">
                      {detalle.nombre} {detalle.apellido}
                    </h2>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${ROL_COLOR[detalle.rol] ?? 'bg-gray-100 text-gray-600'}`}>
                      {ROL_LABELS[detalle.rol] ?? detalle.rol}
                    </span>
                  </div>
                  <button onClick={() => setDetalle(null)} className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 text-xl leading-none">&times;</button>
                </div>

                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-gray-500">DNI</dt>
                    <dd className="text-gray-800 dark:text-gray-100 font-medium">{detalle.dni}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Email</dt>
                    <dd className="text-gray-800 dark:text-gray-100">{detalle.email ?? '—'}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Teléfono</dt>
                    <dd className="text-gray-800 dark:text-gray-100">{detalle.telefono || '—'}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Estado</dt>
                    <dd>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${detalle.activo ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'}`}>
                        {detalle.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </dd>
                  </div>
                  {detalle.rol === 'SOC' && (
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Padre/tutor</dt>
                      <dd className="text-gray-800 dark:text-gray-100 text-right">
                        {detalle.padre_dni
                          ? (
                            <span>
                              {detalle.padre_apellido && detalle.padre_nombre
                                ? `${detalle.padre_apellido}, ${detalle.padre_nombre} · `
                                : ''}
                              {detalle.padre_dni}
                              {detalle.padre_email ? ` · ${detalle.padre_email}` : ''}
                            </span>
                          )
                          : <span className="text-amber-500 text-xs">Sin asignar</span>}
                      </dd>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Registro</dt>
                    <dd className="text-gray-800 dark:text-gray-100">
                      {new Date(detalle.fecha_registro).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' })}
                    </dd>
                  </div>
                </dl>

                {canManage && (
                  <div className="flex gap-2 mt-6 justify-end">
                    <button
                      onClick={() => abrirEdicion(detalle)}
                      className="px-3 py-1.5 text-sm rounded-lg border border-cyan-300 text-cyan-600 hover:bg-cyan-50 transition-colors"
                    >
                      Editar
                    </button>
                    <button
                      onClick={() => setConfirmarEliminar(detalle)}
                      className="px-3 py-1.5 text-sm rounded-lg border border-red-300 text-red-600 hover:bg-red-50 transition-colors"
                    >
                      Eliminar
                    </button>
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100">Editar usuario</h2>
                  <button onClick={() => setEditando(false)} className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 text-xl leading-none">&times;</button>
                </div>

                {form && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs text-gray-500 mb-1 block">Nombre</label>
                        <input
                          type="text"
                          value={form.nombre}
                          onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                          className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 mb-1 block">Apellido</label>
                        <input
                          type="text"
                          value={form.apellido}
                          onChange={(e) => setForm({ ...form, apellido: e.target.value })}
                          className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">DNI</label>
                      <input
                        type="text"
                        value={form.dni}
                        onChange={(e) => setForm({ ...form, dni: e.target.value })}
                        className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">Email</label>
                      <input
                        type="email"
                        value={form.email ?? ''}
                        onChange={(e) => setForm({ ...form, email: e.target.value })}
                        className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">Teléfono</label>
                      <input
                        type="text"
                        value={form.telefono}
                        onChange={(e) => setForm({ ...form, telefono: e.target.value })}
                        className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
                      />
                    </div>
                    {detalle?.rol === 'SOC' && (
                      <div>
                        <label className="text-xs text-gray-500 mb-1 block">DNI del padre/tutor</label>
                        <input
                          type="text"
                          value={form.dni_padre ?? ''}
                          onChange={(e) => setForm({ ...form, dni_padre: e.target.value })}
                          placeholder="Dejar vacío para desasignar"
                          className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300 dark:bg-gray-700 dark:text-gray-100"
                        />
                        <p className="mt-1 text-xs text-gray-400">Debe existir un padre/tutor registrado con ese DNI.</p>
                      </div>
                    )}
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">Rol</label>
                      <select
                        value={form.rol}
                        onChange={(e) => setForm({ ...form, rol: e.target.value })}
                        className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
                      >
                        {Object.entries(ROL_LABELS).map(([k, v]) => (
                          <option key={k} value={k}>{v}</option>
                        ))}
                      </select>
                    </div>
                    <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.activo}
                        onChange={(e) => setForm({ ...form, activo: e.target.checked })}
                        className="rounded border-gray-300 text-cyan-500 focus:ring-cyan-300 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
                      />
                      Usuario activo
                    </label>
                  </div>
                )}

                <div className="flex justify-end gap-2 mt-5">
                  <button
                    onClick={() => setEditando(false)}
                    className="px-4 py-2 text-sm rounded-lg text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={guardar}
                    disabled={guardando}
                    className="px-4 py-2 text-sm rounded-lg bg-cyan-500 text-white hover:bg-cyan-600 transition-colors disabled:opacity-60"
                  >
                    {guardando ? 'Guardando...' : 'Guardar'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
      {/* Modal confirmación eliminar */}
      {confirmarEliminar && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-sm mx-4 overflow-hidden">
            {/* Franja roja superior */}
            <div className="bg-red-600 px-6 py-4 flex items-center gap-3">
              <span className="text-3xl">⚠️</span>
              <div>
                <p className="text-white font-bold text-lg leading-tight">Zona de peligro</p>
                <p className="text-red-200 text-xs">Esta acción no se puede deshacer</p>
              </div>
            </div>

            <div className="px-6 py-5">
              <p className="text-gray-800 dark:text-gray-100 text-sm mb-1">
                Estás por eliminar permanentemente a:
              </p>
              <p className="text-gray-900 dark:text-white font-bold text-base mb-1">
                {confirmarEliminar.apellido}, {confirmarEliminar.nombre}
              </p>
              <p className="text-gray-500 text-xs mb-4">
                DNI {confirmarEliminar.dni} · {ROL_LABELS[confirmarEliminar.rol] ?? confirmarEliminar.rol}
              </p>
              <p className="text-red-600 dark:text-red-400 text-xs font-medium bg-red-50 dark:bg-red-900/30 rounded-lg px-3 py-2">
                Se perderán todos sus datos, inscripciones y pagos asociados.
              </p>
            </div>

            <div className="px-6 pb-5 flex gap-3">
              <button
                onClick={() => setConfirmarEliminar(null)}
                className="flex-1 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-sm font-medium py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={() => eliminar(confirmarEliminar.uuid)}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white text-sm font-bold py-2 rounded-lg transition-colors"
              >
                Sí, eliminar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UsuariosPage;
