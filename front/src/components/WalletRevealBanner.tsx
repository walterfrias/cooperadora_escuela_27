import React, { useState } from 'react';
import { useAuth } from '../contex/UserContex';
import { API_URL } from '../config';

interface WalletData {
  address: string;
  revealed: boolean;
  private_key: string | null;
}

const WalletRevealBanner: React.FC = () => {
  const { authFetch } = useAuth();
  const [state, setState] = useState<'idle' | 'loading' | 'revealed' | 'error'>('idle');
  const [wallet, setWallet] = useState<WalletData | null>(null);
  const [copied, setCopied] = useState<'address' | 'key' | null>(null);

  const handleReveal = async () => {
    setState('loading');
    try {
      const res = await authFetch(`${API_URL}/api/mi-wallet/`);
      if (!res.ok) throw new Error();
      const data: WalletData = await res.json();
      setWallet(data);
      setState('revealed');
    } catch {
      setState('error');
    }
  };

  const copyToClipboard = async (text: string, field: 'address' | 'key') => {
    await navigator.clipboard.writeText(text);
    setCopied(field);
    setTimeout(() => setCopied(null), 2000);
  };

  if (state === 'idle') {
    return (
      <div className="bg-cyan-50 dark:bg-cyan-900/30 border border-cyan-200 dark:border-cyan-700 rounded-2xl p-6 mb-8">
        <div className="flex items-start gap-4">
          <span className="text-3xl">🪙</span>
          <div className="flex-1">
            <h3 className="font-bold text-gray-800 dark:text-gray-100 mb-1">
              Tu wallet COOP está lista
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
              Cada cuota que pagás genera un token COOP en tu wallet. Guardá tu clave privada
              en un lugar seguro: te la mostramos <strong>una sola vez</strong>.
            </p>
            <button
              onClick={handleReveal}
              className="px-5 py-2 bg-cyan-500 text-white text-sm rounded-lg hover:bg-cyan-600 transition-colors"
            >
              Ver mi wallet
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (state === 'loading') {
    return (
      <div className="bg-cyan-50 dark:bg-cyan-900/30 border border-cyan-200 dark:border-cyan-700 rounded-2xl p-6 mb-8 text-center text-gray-500">
        Cargando...
      </div>
    );
  }

  if (state === 'error') {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-2xl p-6 mb-8 text-sm text-red-600 dark:text-red-400">
        No se pudo cargar la wallet. Intentá de nuevo más tarde.
      </div>
    );
  }

  // state === 'revealed'
  return (
    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-300 dark:border-yellow-700 rounded-2xl p-6 mb-8">
      <div className="flex items-start gap-3 mb-4">
        <span className="text-2xl">⚠️</span>
        <p className="text-sm text-yellow-800 dark:text-yellow-300 font-medium">
          Guardá tu clave privada ahora. No la vamos a mostrar de nuevo.
          Quien tenga esta clave controla tu wallet.
        </p>
      </div>

      <div className="space-y-3">
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">Dirección (pública)</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-xs font-mono text-gray-800 dark:text-gray-100 break-all">
              {wallet?.address}
            </code>
            <button
              onClick={() => copyToClipboard(wallet!.address, 'address')}
              className="shrink-0 px-3 py-2 text-xs bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
            >
              {copied === 'address' ? '✓' : 'Copiar'}
            </button>
          </div>
        </div>

        {wallet?.private_key && (
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
              Clave privada — <span className="text-red-500 font-semibold">no compartir</span>
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-white dark:bg-gray-800 border border-red-200 dark:border-red-700 rounded-lg px-3 py-2 text-xs font-mono text-gray-800 dark:text-gray-100 break-all">
                {wallet.private_key}
              </code>
              <button
                onClick={() => copyToClipboard(wallet!.private_key!, 'key')}
                className="shrink-0 px-3 py-2 text-xs bg-red-50 dark:bg-red-900/30 hover:bg-red-100 dark:hover:bg-red-900/50 border border-red-200 dark:border-red-700 rounded-lg transition-colors text-red-600 dark:text-red-400"
              >
                {copied === 'key' ? '✓' : 'Copiar'}
              </button>
            </div>
          </div>
        )}
      </div>

      <p className="text-xs text-gray-400 dark:text-gray-500 mt-4">
        Para ver tu saldo COOP en MetaMask: importá la cuenta con la clave privada → agregá token en Base Sepolia
        con contrato <code className="font-mono">0x0b5cca51576512ec65cce5aa7fd276ead565e210</code>
      </p>
    </div>
  );
};

export default WalletRevealBanner;
