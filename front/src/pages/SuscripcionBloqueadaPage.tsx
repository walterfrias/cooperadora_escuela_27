import { useTenant } from '../contex/TenantContext';

export default function SuscripcionBloqueadaPage() {
  const { slug } = useTenant();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full text-center space-y-4">
        <h1 className="text-2xl font-bold text-gray-800">Acceso suspendido</h1>
        <p className="text-gray-600">
          La suscripción de <strong>{slug}</strong> está inactiva o vencida.
        </p>
        <p className="text-gray-500 text-sm">
          Contactá al administrador de la plataforma para renovar el acceso.
        </p>
      </div>
    </div>
  );
}
