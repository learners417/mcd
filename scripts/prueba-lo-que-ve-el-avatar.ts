// ============================================================================
//  MCD · Lo que el avatar ve — ejecutando los normalizadores
//
//  POR QUÉ EXISTE. `normalize.ts` es la única traducción de GHL crudo a lo que
//  la doctora lee en pantalla: quién espera respuesta, en qué etapa está cada
//  venta, quién no vino a su sesión. Hasta el 16 de noviembre NINGUNA lente lo
//  ejecutaba. Medido ese día con tres defectos puestos a propósito —la bandeja
//  sin marcar los mensajes sin leer, toda venta abierta contando como paciente,
//  y el que no vino contando como que vino— las 74 lentes daban VERDE con los
//  tres.
//
//  Corre con:  node --experimental-transform-types
// ============================================================================
import {
  toPersona, toConversacion, toCita, toVenta, stageNameIndex, toMensaje,
} from '../src/lib/ghl/normalize.ts'

let fallas = 0
function pide(afirmacion: string, ok: boolean, detalle = '') {
  console.log(`  ${ok ? '✓' : '✗'} ${afirmacion}${ok ? '' : ' — ' + detalle}`)
  if (!ok) fallas++
}

console.log('\nLO QUE VE EL AVATAR\n')

// --- la bandeja: quién espera respuesta ------------------------------------
pide('una conversación con 3 sin leer marca 3',
  toConversacion({ id: 'c', unreadCount: 3 }).sinLeer === 3,
  `marcó ${toConversacion({ id: 'c', unreadCount: 3 }).sinLeer}`)
pide('y con uno, marca uno (no cero)',
  toConversacion({ id: 'c', unreadCount: 1 }).sinLeer === 1)
pide('una leída marca cero', toConversacion({ id: 'c', unreadCount: 0 }).sinLeer === 0)
pide('y una sin el campo marca cero, no `NaN`',
  toConversacion({ id: 'c' }).sinLeer === 0)
pide('el canal de WhatsApp se nombra WhatsApp',
  toConversacion({ id: 'c', lastMessageType: 'TYPE_WHATSAPP' }).canal === 'WhatsApp')
pide('la fecha en milisegundos se vuelve ISO del mismo instante',
  toConversacion({ id: 'c', lastMessageDate: 1763251200000 }).fecha
    === new Date(1763251200000).toISOString())

// --- las sesiones: quién vino y quién no -----------------------------------
const estados: Array<[string, string]> = [
  ['new', 'agendada'], ['booked', 'agendada'], ['confirmed', 'confirmada'],
  ['showed', 'realizada'], ['noshow', 'no_vino'], ['cancelled', 'cancelada'],
  ['invalid', 'cancelada'],
]
for (const [crudo, esperado] of estados) {
  pide(`una cita \`${crudo}\` queda como \`${esperado}\``,
    toCita({ id: 'a', appointmentStatus: crudo }).estado === esperado,
    `quedó ${toCita({ id: 'a', appointmentStatus: crudo }).estado}`)
}
pide('el que NO vino nunca cuenta como que vino',
  toCita({ id: 'a', appointmentStatus: 'noShow' }).estado === 'no_vino',
  'un no_vino contado como realizada infla la tasa de asistencia')
pide('y un estado que GHL no manda queda agendada, no realizada',
  toCita({ id: 'a', appointmentStatus: 'lo-que-sea' }).estado === 'agendada')

// --- las ventas: en qué etapa está cada una --------------------------------
const idx = stageNameIndex([{ stages: [
  { id: 's1', name: 'Interesada' },
  { id: 's2', name: 'Conversando por WhatsApp' },
  { id: 's3', name: 'Llamada agendada' },
  { id: 's4', name: 'Paciente' },
] }])
pide('el índice de etapas sale de los pipelines', idx['s4'] === 'Paciente')
const etapa = (status: string, stage: string) =>
  toVenta({ id: 'v', pipelineStageId: stage, status }, idx).etapa

pide('una venta abierta en Interesada es interesada', etapa('open', 's1') === 'interesada')
pide('abierta en Conversando es conversando', etapa('open', 's2') === 'conversando')
pide('abierta en Llamada agendada es agendada', etapa('open', 's3') === 'agendada')
pide('ganada es paciente, esté donde esté', etapa('won', 's1') === 'paciente')
pide('UNA ABIERTA EN INTERESADA NO ES PACIENTE', etapa('open', 's1') !== 'paciente',
  'toda venta abierta contando como paciente: el tablero miente')
pide('ni una abierta en Conversando', etapa('open', 's2') !== 'paciente')
pide('ni una abierta en Llamada agendada', etapa('open', 's3') !== 'paciente')
pide('el estado crudo de GHL queda guardado para auditar',
  toVenta({ id: 'v', pipelineStageId: 's1', status: 'open' }, idx).estadoGhl === 'open')
pide('y el nombre crudo de la etapa también, por si el mapa falla',
  toVenta({ id: 'v', pipelineStageId: 's4', status: 'open' }, idx).etapaGhl === 'Paciente')
pide('una etapa que no está en el índice no borra su id',
  toVenta({ id: 'v', pipelineStageId: 'sX', status: 'open' }, idx).etapaGhl === 'sX')
pide('el valor llega como número, no como texto',
  toVenta({ id: 'v', pipelineStageId: 's1', monetaryValue: '150' }, idx).valor === 150)

// Lo que HOY hace y es decisión de producto, no de la batería: una venta
// `lost` o `abandoned` parada en la etapa «Paciente» se muestra como
// paciente, porque el nombre de la etapa se evalúa con un `||` y gana sobre
// el status. El comentario del archivo dice lo contrario («señal DURA
// primero»). Queda clavado acá para que el cambio sea un clic de Javo y no un
// descuido: si algún día se decide que el status manda, esta línea se da
// vuelta a propósito.
pide('HOY: una venta perdida en la etapa Paciente se sigue mostrando paciente',
  etapa('lost', 's4') === 'paciente',
  'cambió el criterio sin pasar por el mapa')

// --- las personas y los mensajes -------------------------------------------
pide('el nombre se arma con nombre y apellido',
  toPersona({ id: 'p', firstName: 'Ana', lastName: 'Ruiz' }).nombre === 'Ana Ruiz')
pide('con solo el nombre, no queda un espacio colgando',
  toPersona({ id: 'p', firstName: 'Ana' }).nombre === 'Ana')
pide('sin nombre ninguno, cae a `contactName`',
  toPersona({ id: 'p', contactName: 'Ana R.' }).nombre === 'Ana R.')
pide('y sin nada, «Sin nombre» y no `undefined`',
  toPersona({ id: 'p' }).nombre === 'Sin nombre')
pide('los tags llegan como lista, nunca `undefined`',
  Array.isArray(toPersona({ id: 'p' }).tags))
pide('un mensaje entrante es de la persona',
  toMensaje({ id: 'm', direction: 'inbound' }).entrante === true)
pide('y uno saliente es de la doctora',
  toMensaje({ id: 'm', direction: 'outbound' }).entrante === false)
pide('el texto sale de `body` o de `message`',
  toMensaje({ id: 'm', message: 'hola' }).texto === 'hola')

console.log(fallas === 0
  ? `\n✓ lo que ve el avatar: sano\n`
  : `\n✗ ${fallas} fallas en lo que ve el avatar\n`)
process.exit(fallas === 0 ? 0 : 1)
