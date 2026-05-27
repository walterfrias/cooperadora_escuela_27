// AuthContext.tsx
import { createContext, useState, useEffect, useContext } from 'react';
import type { ReactNode } from 'react';
import { API_URL } from '../config';
import { useTenant } from './TenantContext';

// Definir los tipos
interface User {
  uuid: string;
  nombre: string;
  apellido: string;
  email: string;
  dni: string;
  rol: string;
  telefono?: string;
  activo?: boolean;
  wallet_address?: string | null;
  key_revealed?: boolean;
}

interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

interface RegisterData {
  nombre: string;
  apellido: string;
  dni: string;
  rol?: string;
  telefono?: string;
  // PAD
  email?: string;
  password?: string;
  // SOC
  dni_padre?: string;
  grado_id?: number;
  anio?: number;
  modalidad?: string;
}

interface RegisterResponse {
  uuid: string;
  nombre: string;
  apellido: string;
  email: string;
  dni: string;
  rol: string;
}

interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: any }>;
  registro: (userData: RegisterData) => Promise<{ success: boolean; data?: RegisterResponse; error?: any }>;
  logout: () => void;
  refreshAccessToken: () => Promise<string | null>;
  authFetch: (url: string, options?: RequestInit) => Promise<Response>;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isPresidente: boolean;
  isTesorero: boolean;
  isSecretario: boolean;
  isSocio: boolean;
  isPadre: boolean;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth debe usarse dentro de un AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const { slug } = useTenant();
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Recuperar sesión del localStorage al montar
  useEffect(() => {
    const storedAccess = localStorage.getItem('accessToken');
    const storedRefresh = localStorage.getItem('refreshToken');
    const storedUser = localStorage.getItem('user');
    if (storedAccess && storedRefresh && storedUser) {
      try {
        setAccessToken(storedAccess);
        setRefreshToken(storedRefresh);
        setUser(JSON.parse(storedUser) as User);
      } catch (error) {
        console.error('Error parsing stored user', error);
        localStorage.removeItem('user');
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
      }
    }
    setLoading(false);
  }, []);

  // Función para manejar respuestas fetch
  const handleResponse = async (response: Response): Promise<any> => {
    const data = await response.json();
    if (!response.ok) {
      throw data; // lanza el error (objeto con detalles)
    }
    return data;
  };

  // Login
  const login = async (email: string, password: string): Promise<{ success: boolean; error?: any }> => {
    try {
      const response = await fetch(`${API_URL}/api/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Tenant-Slug': slug },
        body: JSON.stringify({ email, password }),
      });
      const data = await handleResponse(response) as LoginResponse;
      setAccessToken(data.access);
      setRefreshToken(data.refresh);
      setUser(data.user);
      localStorage.setItem('accessToken', data.access);
      localStorage.setItem('refreshToken', data.refresh);
      localStorage.setItem('user', JSON.stringify(data.user));
      return { success: true };
    } catch (error) {
      return { success: false, error };
    }
  };

  // Crear usuario (solo Tesorero/Admin)
  const registro = async (userData: RegisterData): Promise<{ success: boolean; data?: RegisterResponse; error?: any }> => {
    try {
      const response = await authFetch(`${API_URL}/api/usuarios/crear/`, {
        method: 'POST',
        body: JSON.stringify(userData),
      });
      const data = await response.json();
      if (!response.ok) {
        return { success: false, error: data };
      }
      return { success: true, data };
    } catch (error) {
      return { success: false, error: { general: 'Error de conexión' } };
    }
  };

  // Logout
  const logout = (): void => {
    const storedRefresh = localStorage.getItem('refreshToken');
    if (storedRefresh) {
      fetch(`${API_URL}/api/logout/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: storedRefresh }),
      }).catch(() => {});
    }
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
  };

  // Refrescar token
  const refreshAccessToken = async (): Promise<string | null> => {
    const storedRefresh = localStorage.getItem('refreshToken');
    if (!storedRefresh) return null;
    try {
      const response = await fetch(`${API_URL}/api/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: storedRefresh }),
      });
      const data = await handleResponse(response);
      setAccessToken(data.access);
      localStorage.setItem('accessToken', data.access);
      if (data.refresh) {
        setRefreshToken(data.refresh);
        localStorage.setItem('refreshToken', data.refresh);
      }
      return data.access;
    } catch (error) {
      logout();
      return null;
    }
  };

  // Fetch autenticado
  const authFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
    const token = accessToken || localStorage.getItem('accessToken');
    const isFormData = options.body instanceof FormData;
    const headers = new Headers(options.headers || {});
    if (!isFormData) headers.set('Content-Type', 'application/json');
    if (token) headers.set('Authorization', `Bearer ${token}`);
    if (slug) headers.set('X-Tenant-Slug', slug);

    const response = await fetch(url, { ...options, headers });

    if (response.status === 403) {
      const data = await response.clone().json().catch(() => ({}));
      if (typeof data.detail === 'string' && data.detail.includes('uscripci')) {
        window.location.href = `/${slug}/suscripcion-bloqueada`;
      }
      return response;
    }

    if (response.status === 401) {
      const newToken = await refreshAccessToken();
      if (newToken) {
        const newHeaders = new Headers(options.headers || {});
        if (!isFormData) newHeaders.set('Content-Type', 'application/json');
        newHeaders.set('Authorization', `Bearer ${newToken}`);
        if (slug) newHeaders.set('X-Tenant-Slug', slug);
        return fetch(url, { ...options, headers: newHeaders });
      }
    }
    return response;
  };

  const value: AuthContextType = {
    user,
    accessToken,
    refreshToken,
    login,
    registro,
    logout,
    refreshAccessToken,
    authFetch,
    isAuthenticated: !!user,
    isAdmin: user?.rol === 'ADMIN',
    isPresidente: user?.rol === 'PRES',
    isTesorero: user?.rol === 'TES',
    isSecretario: user?.rol === 'SEC',
    isSocio: user?.rol === 'SOC',
    isPadre: user?.rol === 'PAD',
    loading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};