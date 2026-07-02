import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contex/UserContex';
import { useTenant } from '../contex/TenantContext';
import WalletRevealBanner from './WalletRevealBanner';

interface DashCard {
  icon: string;
  title: string;
  description: string;
  path: string;
  label: string;
}

const Card: React.FC<DashCard> = ({ icon, title, description, path, label }) => (
  <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8 hover:shadow-xl transition-shadow flex flex-col">
    <div className="text-5xl mb-4">{icon}</div>
    <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100 mb-2">{title}</h2>
    <p className="text-gray-600 text-sm flex-1 mb-6">{description}</p>
    <Link
      to={path}
      className="inline-block self-start px-5 py-2 bg-cyan-500 text-white text-sm rounded-lg hover:bg-cyan-600 transition-colors"
    >
      {label}
    </Link>
  </div>
);

const Home: React.FC = () => {
  const { isAuthenticated, isAdmin, isTesorero, isPresidente, isSecretario, isPadre, user } = useAuth();
  const { slug } = useTenant();

  // Sin sesión: landing pública
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-cyan-50 dark:from-gray-900 to-white dark:to-gray-900">
        <section className="container mx-auto px-4 py-16 text-center">
          <h1 className="text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-500 to-cyan-300 mb-4">
            Cooperadora Escolar N°27
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Conectando a la comunidad educativa: información, eventos y gestión para padres y cooperadora.
          </p>
        </section>
        <section className="container mx-auto px-4 pb-16 grid md:grid-cols-2 gap-8 max-w-4xl">
          <Card
            icon="👨‍👩‍👧‍👦"
            title="Para Padres"
            description="Accedé a noticias, novedades escolares y el estado de cuenta de tus hijos."
            path="/login"
            label="Ingresar"
          />
          <Card
            icon="👥"
            title="Área Administrativa"
            description="Gestioná pagos, usuarios y publicaciones. Acceso exclusivo para miembros de la cooperadora."
            path="/login"
            label="Acceder"
          />
        </section>
      </div>
    );
  }

  // Cards por rol
  const padreCards: DashCard[] = [
    {
      icon: '👨‍👩‍👧‍👦',
      title: 'Mis hijos',
      description: 'Consultá la información de cada hijo: grado, inscripción y datos registrados.',
      path: `/${slug}/mis-hijos`,
      label: 'Ver mis hijos',
    },
    {
      icon: '📋',
      title: 'Estado de cuenta',
      description: 'Revisá las cuotas pagas, pendientes y donaciones del año en curso.',
      path: `/${slug}/estado-cuenta`,
      label: 'Ver estado',
    },
    {
      icon: '📢',
      title: 'Publicaciones',
      description: 'Noticias, agenda y novedades de la cooperadora y la escuela.',
      path: `/${slug}/publicaciones`,
      label: 'Ver publicaciones',
    },
  ];

  const tesCards: DashCard[] = [
    {
      icon: '💳',
      title: 'Pagos',
      description: 'Registrá y consultá pagos de cuotas, pagos anuales y donaciones.',
      path: `/${slug}/pagos`,
      label: 'Ir a pagos',
    },
    {
      icon: '👤',
      title: 'Usuarios',
      description: 'Listado completo de usuarios registrados con opciones de edición.',
      path: `/${slug}/usuarios`,
      label: 'Ver usuarios',
    },
    {
      icon: '➕',
      title: 'Nuevo usuario',
      description: 'Registrá un nuevo padre o alumno en el sistema.',
      path: `/${slug}/registro`,
      label: 'Registrar',
    },
    {
      icon: '👨‍👩‍👧‍👦',
      title: 'Mis hijos',
      description: 'Si también sos padre/tutor, consultá la información de tus hijos.',
      path: `/${slug}/mis-hijos`,
      label: 'Ver mis hijos',
    },
    {
      icon: '📋',
      title: 'Estado de cuenta',
      description: 'Revisá las cuotas pagas, pendientes y donaciones de tus hijos.',
      path: `/${slug}/estado-cuenta`,
      label: 'Ver estado',
    },
  ];

  const secCards: DashCard[] = [
    {
      icon: '📢',
      title: 'Publicaciones',
      description: 'Creá y gestioná noticias, novedades y agenda para la comunidad educativa.',
      path: `/${slug}/publicaciones`,
      label: 'Gestionar',
    },
  ];

  const adminCards: DashCard[] = [...tesCards, ...secCards];

  let cards: DashCard[];
  let greeting: string;
  let subtitle: string;

  if (isAdmin) {
    cards = adminCards;
    greeting = `Hola, ${user?.nombre}`;
    subtitle = 'Panel de administración';
  } else if (isTesorero) {
    cards = tesCards;
    greeting = `Hola, ${user?.nombre}`;
    subtitle = 'Panel del Tesorero';
  } else if (isPresidente) {
    cards = tesCards;
    greeting = `Hola, ${user?.nombre}`;
    subtitle = 'Panel del Presidente';
  } else if (isSecretario) {
    cards = secCards;
    greeting = `Hola, ${user?.nombre}`;
    subtitle = 'Panel del Secretario';
  } else if (isPadre) {
    cards = padreCards;
    greeting = `Hola, ${user?.nombre}`;
    subtitle = 'Tu espacio en la cooperadora';
  } else {
    cards = [
      {
        icon: '📢',
        title: 'Publicaciones',
        description: 'Noticias, agenda y novedades de la cooperadora y la escuela.',
        path: `/${slug}/publicaciones`,
        label: 'Ver publicaciones',
      },
    ];
    greeting = `Hola, ${user?.nombre}`;
    subtitle = 'Bienvenido';
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-cyan-50 dark:from-gray-900 to-white dark:to-gray-900">
      <section className="container mx-auto px-4 py-12 text-center">
        <h1 className="text-4xl font-extrabold text-gray-800 dark:text-gray-100 mb-2">{greeting}</h1>
        <p className="text-gray-500 text-lg">{subtitle}</p>
      </section>
      {isPadre && user?.wallet_address && !user?.key_revealed && (
        <div className="container mx-auto px-4 max-w-5xl">
          <WalletRevealBanner />
        </div>
      )}
      <section className={`container mx-auto px-4 pb-16 grid gap-6 max-w-5xl ${
        cards.length === 1 ? 'max-w-sm' :
        cards.length === 2 ? 'md:grid-cols-2 max-w-3xl' :
        'md:grid-cols-3'
      }`}>
        {cards.map((card) => (
          <Card key={card.path} {...card} />
        ))}
      </section>
    </div>
  );
};

export default Home;
