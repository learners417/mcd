// ============================================================================
//  MCD · El token del cliente, ida y vuelta de verdad
//
//  POR QUÉ EXISTE. El bloque 5 de la batería dice «el token del cliente no
//  viaja en claro», y hasta el 16 de noviembre lo decía LEYENDO el archivo:
//  que la cadena `aes-256-gcm` estuviera escrita y que la clave saliera del
//  entorno. Medido ese día con tres defectos puestos a propósito —la etiqueta
//  del GCM leída un byte corta, el IV fijo en ceros, y el descifrado
//  devolviendo lo guardado sin descifrar— las 74 lentes daban VERDE con los
//  tres. Ninguna ejecutaba el cifrado.
//
//  Esto lo ejecuta. Corre con:  node --experimental-transform-types
// ============================================================================
import { encryptToken, decryptToken } from '../src/lib/crypto.ts'
import crypto from 'crypto'

const CLAVE_A = 'a'.repeat(64)
const CLAVE_B = 'b'.repeat(64)
const PIT = 'pit-abc123.XyZ_token-de-subcuenta'

let fallas = 0
function pide(afirmacion: string, ok: boolean, detalle = '') {
  console.log(`  ${ok ? '✓' : '✗'} ${afirmacion}${ok ? '' : ' — ' + detalle}`)
  if (!ok) fallas++
}
function tira(afirmacion: string, fn: () => unknown) {
  try { fn(); pide(afirmacion, false, 'no tiró ningún error') }
  catch { pide(afirmacion, true) }
}

console.log('\nEL TOKEN CIFRADO\n')

process.env.TOKEN_ENCRYPTION_KEY = CLAVE_A

// 1 · la vuelta completa: lo que entra es lo que sale
const guardado = encryptToken(PIT)
pide('lo cifrado vuelve a ser el mismo token', decryptToken(guardado) === PIT,
  `volvió ${JSON.stringify(decryptToken(guardado))}`)

// 2 · y con acentos y signos, que es utf-8 y no ascii
const CON_TILDE = 'ñandú-éxito-✓-token'
pide('y un token con acentos vuelve igual', decryptToken(encryptToken(CON_TILDE)) === CON_TILDE)

// 3 · lo guardado NO contiene el token legible
pide('lo guardado no contiene el token en claro', !guardado.includes(PIT))
pide('y lleva el prefijo de versión', guardado.startsWith('enc:v1:'))

// 4 · dos veces el mismo token da dos cifrados distintos (IV aleatorio).
//     Con el IV fijo, AES-GCM repite el nonce: se despeja y se falsifica.
const a = encryptToken(PIT), b = encryptToken(PIT)
pide('dos cifrados del mismo token son distintos (el IV no se repite)', a !== b,
  'el IV es fijo: nonce repetido en AES-GCM')

// 5 · el IV de verdad son 12 bytes distintos, no doce ceros
const crudo = Buffer.from(guardado.slice('enc:v1:'.length), 'base64')
pide('el IV no son doce ceros', !crudo.subarray(0, 12).equals(Buffer.alloc(12)))

// 6 · la etiqueta del GCM sirve: un byte cambiado no descifra
const roto = Buffer.from(crudo)
roto[roto.length - 1] ^= 0xff
tira('un texto cifrado manoseado no descifra (la etiqueta del GCM sirve)',
  () => decryptToken('enc:v1:' + roto.toString('base64')))

// 6 bis · y CADA uno de los 16 bytes de la etiqueta cuenta.
//   Medido el 16 de noviembre: con la etiqueta leída un byte corta
//   —`subarray(12, 27)`— AES-GCM igual descifra, porque acepta etiquetas
//   truncadas. El token seguía yendo y viniendo, así que la vuelta completa de
//   arriba daba VERDE y el último byte de la etiqueta no lo verificaba nadie.
//   Esto lo ve: si algún byte de la etiqueta deja de mirarse, su vuelta pasa.
let etiquetaFloja = 0
for (let i = 12; i < 28; i++) {
  const t = Buffer.from(crudo)
  t[i] ^= 0xff
  try { decryptToken('enc:v1:' + t.toString('base64')); etiquetaFloja++ } catch { /* bien */ }
}
pide('los 16 bytes de la etiqueta se verifican, no 15', etiquetaFloja === 0,
  `${etiquetaFloja} byte(s) de la etiqueta no se miran: la etiqueta se lee truncada`)

// 7 · con otra clave no se abre
process.env.TOKEN_ENCRYPTION_KEY = CLAVE_B
tira('con otra clave no se abre', () => decryptToken(guardado))

// 8 · sin clave en el entorno, nadie cifra ni descifra a medias
delete process.env.TOKEN_ENCRYPTION_KEY
tira('sin la clave en el entorno, cifrar tira error', () => encryptToken(PIT))
process.env.TOKEN_ENCRYPTION_KEY = 'corta'
tira('y con una clave de largo equivocado, también', () => encryptToken(PIT))

// 9 · el passthrough de datos viejos sigue siendo SOLO para los no cifrados
process.env.TOKEN_ENCRYPTION_KEY = CLAVE_A
const viejo = 'pit-sin-cifrar-de-antes'
pide('un valor sin prefijo pasa igual (migración suave)', decryptToken(viejo) === viejo)
pide('y uno con prefijo NO pasa igual: se descifra', decryptToken(guardado) !== guardado)

// 10 · el formato: 12 de IV + 16 de etiqueta + el resto
const corto = encryptToken('x')
const c = Buffer.from(corto.slice('enc:v1:'.length), 'base64')
pide('el sobre es 12 de IV + 16 de etiqueta + el texto', c.length === 12 + 16 + 1,
  `mide ${c.length}, se esperaban ${12 + 16 + 1}`)

// 11 · contra la misma cuenta hecha de otra forma: descifrar a mano
const iv = c.subarray(0, 12), tag = c.subarray(12, 28), ct = c.subarray(28)
const d = crypto.createDecipheriv('aes-256-gcm', Buffer.from(CLAVE_A, 'hex'), iv)
d.setAuthTag(tag)
pide('y descifrado a mano con ese reparto da lo mismo',
  Buffer.concat([d.update(ct), d.final()]).toString('utf8') === 'x')

console.log(fallas === 0
  ? `\n✓ el token cifrado: ida y vuelta sana\n`
  : `\n✗ ${fallas} fallas en el token cifrado\n`)
process.exit(fallas === 0 ? 0 : 1)
