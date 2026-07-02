import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { Bars3Icon, XMarkIcon, SunIcon, MoonIcon } from '@heroicons/react/24/outline';
import { useAuth } from '../contex/UserContex';
import { useTheme } from '../contex/ThemeContext';
import { useTenant } from '../contex/TenantContext';
import Avatar from './Avatar';

interface NavItem {
  name: string;
  path: string;
}

const Header: React.FC = () => {
  const [menuOpen, setMenuOpen] = useState(false);
  const { isAuthenticated, isAdmin, isPresidente, isTesorero, isPadre } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { slug, nombre, numeroEscuela } = useTenant();

  const canManage = isAdmin || isTesorero || isPresidente;
  const p = (path: string) => `/${slug}${path}`;

  const navLinks: NavItem[] = [
    { name: 'Inicio', path: p('/about') },
    ...(isPadre ? [
      { name: 'Mis hijos', path: p('/mis-hijos') },
      { name: 'Estado de cuenta', path: p('/estado-cuenta') },
      { name: 'Publicaciones', path: p('/publicaciones') },
    ] : canManage ? [
      { name: 'Usuarios', path: p('/usuarios') },
      { name: 'Pagos', path: p('/pagos') },
      { name: 'Cuotas', path: p('/cuotas') },
      { name: 'Mis hijos', path: p('/mis-hijos') },
      { name: 'Estado de cuenta', path: p('/estado-cuenta') },
      { name: 'Publicaciones', path: p('/publicaciones') },
    ] : [
      { name: 'Publicaciones', path: p('/publicaciones') },
    ]),
  ];

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-4 py-2 rounded-md text-sm font-medium transition-colors duration-200 ${
      isActive
        ? 'bg-cyan-100 dark:bg-cyan-900/40 text-cyan-600 dark:text-cyan-300'
        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-cyan-600 dark:hover:text-cyan-400'
    }`;

  const mobileLinkClass = ({ isActive }: { isActive: boolean }) =>
    `block px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? 'bg-cyan-100 dark:bg-cyan-900/40 text-cyan-600 dark:text-cyan-300'
        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-cyan-600 dark:hover:text-cyan-400'
    }`;

  return (
    <header className="bg-white dark:bg-gray-900 shadow-md dark:shadow-gray-800/50 sticky top-0 z-50 border-b border-transparent dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* Brand */}
          <NavLink to={`/${slug}/about`} className="text-xl font-bold text-cyan-500 shrink-0">
            {numeroEscuela && nombre ? `Cooperadora - ${nombre} N°${numeroEscuela}` : 'CooperaApp'}
          </NavLink>

          {/* Desktop nav */}
          {isAuthenticated && (
            <nav className="hidden md:flex items-center gap-1">
              {navLinks.map((link) => (
                <NavLink key={link.path} to={link.path} className={linkClass}>
                  {link.name}
                </NavLink>
              ))}
            </nav>
          )}

          {/* Right: toggle + Avatar + hamburger */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-md text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              aria-label="Cambiar tema"
            >
              {theme === 'dark'
                ? <SunIcon className="h-5 w-5 text-yellow-400" />
                : <MoonIcon className="h-5 w-5" />
              }
            </button>

            <Avatar />

            {isAuthenticated && (
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="md:hidden p-2 text-gray-500 dark:text-gray-400 hover:text-cyan-500 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                aria-label="Menú"
              >
                {menuOpen
                  ? <XMarkIcon className="h-6 w-6" />
                  : <Bars3Icon className="h-6 w-6" />
                }
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && isAuthenticated && (
        <div className="md:hidden bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-700 dark:border-gray-700 px-4 py-3 space-y-1 shadow-sm">
          {navLinks.map((link) => (
            <NavLink
              key={link.path}
              to={link.path}
              onClick={() => setMenuOpen(false)}
              className={mobileLinkClass}
            >
              {link.name}
            </NavLink>
          ))}
        </div>
      )}
    </header>
  );
};

export default Header;
