# Web3 — Wallet custodial para padres

## Contexto

Integración invisible entre el sistema Django y los contratos en Base Sepolia.
Los padres usan la app Web2 sin cambios. La wallet y los tokens existen en segundo plano.
Cada cooperadora tiene su propio DAO clone (EIP-1167) deployado por la Factory.
El token COOP es compartido entre todas las cooperadoras.

---

## Requerimientos funcionales

### RF-01 — Generación automática de wallet
- Al crear un usuario con `rol = Rol.PADRE`, el sistema genera automáticamente un par de claves Ethereum.
- Se guarda `wallet_address` (dirección pública) y `wallet_private_key_encrypted` (clave privada encriptada con Fernet) en `Usuario`.
- Si el usuario PAD ya tiene `wallet_address`, no se regenera.
- Si la cooperadora no tiene `dao_address` todavía, la wallet se genera pero no se registra en el DAO.

### RF-02 — Reveal-once de la private key
- El campo `key_revealed` (BooleanField, default=False) indica si el padre ya vio su key.
- `GET /api/mi-wallet/` devuelve `address + private_key` solo si `key_revealed=False`, luego la marca como revelada.
- Llamadas siguientes devuelven solo `address` (private_key=null).
- La private key **nunca** aparece en ningún otro endpoint ni serializer.
- Motivo de custodiar la key: red de seguridad si el padre pierde su contraseña de wallet.

### RF-03 — Mint de token al registrar un pago
- Al registrar un pago mensual o anual, se mintea 1 token COOP al padre del alumno.
- No se mintea en pagos de tipo `donacion`.
- El mint se envía a `wallet_address` del padre asociado al alumno inscripto.
- `token_minteado` y `token_mint_tx` en `Pago` registran el resultado.

### RF-04 — Provisioning automático de DAO clone
- Al activar una cooperadora (PENDING → TRIAL o ACTIVE), el signal `provisionar_dao_clone` llama a `Factory.crear()`.
- El clone deployado queda autorizado como minter en el Token v2.
- El clone queda registrado en el MetaDAO.
- El `dao_address` se guarda en la cooperadora.

### RF-05 — Reintentos de mint fallido
- Management command `retry_mint_tokens` busca pagos con `token_minteado=False` y reintenta.

---

## Modelo de datos

### `Usuario`
```
wallet_address                CharField(42, null, blank)
wallet_private_key_encrypted  TextField(null, blank)
key_revealed                  BooleanField(default=False)
```

### `Pago`
```
token_minteado   BooleanField(default=False)
token_mint_tx    CharField(66, null, blank)
```

### `Cooperadora`
```
dao_address   CharField(42, null, blank)
```

---

## Flujo completo

```
Platform admin activa cooperadora (PENDING → TRIAL)
  → pre_save guarda _prev_status
  → post_save detecta transición
  → Factory.crear(nombre, backend_wallet, ciclo, presidente_platform)
  → clone EIP-1167 deployado en Base Sepolia
  → clone autorizado como minter en Token v2
  → clone registrado en MetaDAO
  → dao_address guardado en Cooperadora

TES crea usuario PAD
  → post_save signal generar_wallet_padre
  → genera par de claves Ethereum (web3.py)
  → encripta private key con Fernet + WALLET_ENCRYPTION_KEY
  → guarda wallet_address y wallet_private_key_encrypted
  → registra wallet en clone DAO (agregarMiembro con rol PADRE)

PAD hace primer login
  → Home muestra WalletRevealBanner (si wallet_address y !key_revealed)
  → PAD hace clic "Ver mi wallet"
  → GET /api/mi-wallet/ → devuelve address + private_key desencriptada
  → key_revealed=True guardado en DB
  → banner desaparece en próxima carga

TES registra pago de cuota (mensual o anual)
  → post_save signal mint_token_on_pago
  → obtiene wallet_address del padre del alumno
  → firma tx con BACKEND_WALLET_PRIVATE_KEY
  → llama clone_dao.mintTokenPadre(wallet_address_padre)
  → guarda token_minteado=True y token_mint_tx en Pago
  → 1 COOP visible en MetaMask del padre
```

---

## Variables de entorno requeridas

| Variable | Descripción |
|---|---|
| `BACKEND_WALLET_PRIVATE_KEY` | Clave privada de la wallet `mintAutorizado` |
| `WALLET_ENCRYPTION_KEY` | Clave Fernet para encriptar las private keys de los padres |
| `BASE_SEPOLIA_RPC_URL` | RPC de Base Sepolia |
| `FACTORY_CONTRACT_ADDRESS` | Address de la CooperadoraDAOFactory |
| `PRESIDENTE_PLATFORM_ADDRESS` | Address del admin de plataforma (owner de los clones) |

---

## Contratos en producción (Base Sepolia, mayo 2026)

| Contrato | Address |
|---|---|
| CooperadoraToken v2 (COOP) | `0x0b5cca51576512ec65cce5aa7fd276ead565e210` |
| CooperadoraDAO (implementation) | `0x109e8272b80e2a33c83097495aa3f7ca315e7b8e` |
| MetaCooperadoraDAO | `0x184174dd5e61add571a4628cb089a937c2ab0f73` |
| CooperadoraDAOFactory | `0x77831b5081c629ba0a5487cd4975530e5b500fc6` |
| Wallet admin/mintAutorizado | `0xa6ebab87a0a5890a5abb8d9efc93ee534878161c` |

### Contratos legacy (Escuela 27 original)
| Contrato | Address |
|---|---|
| CooperadoraToken v1 | `0xa6dba267ad78b5179b5cd1ced6fc80cbd5a7a7e0` |
| CooperadoraDAO | `0x77c6740a2031fa0684ea88edc9c6019fa0e7bd2b` |

---

## Scripts útiles

```bash
# Verificar flujo completo end-to-end
python scripts/verificar_flujo_completo.py

# Exportar private key de un padre (para soporte)
python scripts/exportar_wallet_padre.py

# Reintentar mints fallidos
python manage.py retry_mint_tokens
```
