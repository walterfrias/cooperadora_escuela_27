import { createContext, useContext, useMemo } from 'react';
import type { ReactNode } from 'react';
import { useLocation } from 'react-router-dom';

interface TenantContextType {
  slug: string;
}

const TenantContext = createContext<TenantContextType>({ slug: '' });

export const useTenant = (): TenantContextType => useContext(TenantContext);

export const TenantProvider = ({ children }: { children: ReactNode }) => {
  const { pathname } = useLocation();

  const slug = useMemo(() => {
    const parts = pathname.split('/').filter(Boolean);
    if (!parts[0] || parts[0] === 'register') return '';
    return parts[0];
  }, [pathname]);

  return (
    <TenantContext.Provider value={{ slug }}>
      {children}
    </TenantContext.Provider>
  );
};
