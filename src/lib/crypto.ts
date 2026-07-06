// ============================================================================
//  MCD · Cifrado de tokens GHL (AES-256-GCM, server-only)
//  La DB guarda "enc:v1:<base64(iv|tag|ciphertext)>". La clave vive SOLO en
//  el env del servidor (TOKEN_ENCRYPTION_KEY = 64 chars hex = 32 bytes).
//  Generarla:  node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
//  Si se pierde la clave, los tokens no se recuperan: guardala en un lugar
//  seguro FUERA del repo (Vercel env + tu gestor de contraseñas).
// ============================================================================
import crypto from 'crypto'

const PREFIX = 'enc:v1:'

function getKey(): Buffer {
  const hex = process.env.TOKEN_ENCRYPTION_KEY
  if (!hex || hex.length !== 64) {
    throw new Error('TOKEN_ENCRYPTION_KEY falta o no tiene 64 chars hex (32 bytes)')
  }
  return Buffer.from(hex, 'hex')
}

export function encryptToken(plain: string): string {
  const iv = crypto.randomBytes(12)
  const cipher = crypto.createCipheriv('aes-256-gcm', getKey(), iv)
  const ct = Buffer.concat([cipher.update(plain, 'utf8'), cipher.final()])
  const tag = cipher.getAuthTag()
  return PREFIX + Buffer.concat([iv, tag, ct]).toString('base64')
}

/** Passthrough si el valor no está cifrado (migración suave de datos viejos). */
export function decryptToken(stored: string): string {
  if (!stored.startsWith(PREFIX)) return stored
  const buf = Buffer.from(stored.slice(PREFIX.length), 'base64')
  const iv = buf.subarray(0, 12)
  const tag = buf.subarray(12, 28)
  const ct = buf.subarray(28)
  const decipher = crypto.createDecipheriv('aes-256-gcm', getKey(), iv)
  decipher.setAuthTag(tag)
  return Buffer.concat([decipher.update(ct), decipher.final()]).toString('utf8')
}
