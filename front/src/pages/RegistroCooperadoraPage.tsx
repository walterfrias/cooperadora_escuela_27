import { useState } from 'react';
import { API_URL } from '../config';

interface FormData {
  numero_escuela: string;
  nombre: string;
  nombre_contacto: string;
  email_contacto: string;
}

export default function RegistroCooperadoraPage() {
  const [form, setForm] = useState<FormData>({
    numero_escuela: '',
    nombre: '',
    nombre_contacto: '',
    email_contacto: '',
  });
  const [enviado, setEnviado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/register/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          numero_escuela: Number(form.numero_escuela),
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        const msg = Object.values(data).flat().join(' ');
        setError(msg);
      } else {
        setEnviado(true);
      }
    } catch {
      setError('Error de conexión. Intentá de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  if (enviado) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full text-center space-y-4">
          <h1 className="text-2xl font-bold text-green-700">¡Solicitud enviada!</h1>
          <p className="text-gray-600">
            Recibimos tu solicitud. Te contactaremos a <strong>{form.email_contacto}</strong> cuando tu acceso esté habilitado.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-800">Registrá tu cooperadora</h1>
          <p className="text-gray-500 text-sm mt-1">
            Completá el formulario y te habilitamos el acceso.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Número de escuela</label>
            <input
              type="number"
              name="numero_escuela"
              value={form.numero_escuela}
              onChange={handleChange}
              required
              min={1}
              className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Nombre de la escuela</label>
            <input
              type="text"
              name="nombre"
              value={form.nombre}
              onChange={handleChange}
              required
              className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Tu nombre</label>
            <input
              type="text"
              name="nombre_contacto"
              value={form.nombre_contacto}
              onChange={handleChange}
              required
              className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Email de contacto</label>
            <input
              type="email"
              name="email_contacto"
              value={form.email_contacto}
              onChange={handleChange}
              required
              className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {error && <p className="text-red-600 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Enviando...' : 'Solicitar acceso'}
          </button>
        </form>
      </div>
    </div>
  );
}
