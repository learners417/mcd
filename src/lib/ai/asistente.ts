// ============================================================================
//  MCD · El Asistente · Las tareas concretas que la IA resuelve para la doctora.
//  NO es un chatbot genérico: son acciones puntuales con contexto de SU negocio.
// ============================================================================
import { chat } from './proxy'

type Config = { tono?: string; reglas?: string; firma?: string; marca?: string; especialidad?: string }

// Vocabulario prohibido de la marca (nunca en outputs al paciente)
const PROHIBIDO = 'Nunca uses las palabras: coach, coaching, escalar, embudo, funnel, marketing, gurú.'

/** Redactar una respuesta de WhatsApp a partir de la conversación + intención. */
export async function redactarRespuesta(params: {
  historial: string; intencion: string; config: Config
}) {
  const { historial, intencion, config } = params
  const sys = `Sos el asistente de ${config.marca ?? 'una profesional de la salud'}${config.especialidad ? ` (${config.especialidad})` : ''}.
Redactás mensajes de WhatsApp para responder a personas interesadas o pacientes.
Tono: ${config.tono ?? 'cálido y profesional'}. ${config.reglas ? 'Reglas: ' + config.reglas : ''}
Escribí en español neutro (tú/tienes), natural, breve (2-4 frases), humano, sin sonar a robot ni a vendedor.
${PROHIBIDO} ${config.firma ? 'Cerrá con: ' + config.firma : 'No agregues firma.'}
Devolvé SOLO el mensaje, sin comillas ni preámbulo.`
  return chat([
    { role: 'system', content: sys },
    { role: 'user', content: `Conversación hasta ahora:\n${historial}\n\nLo que quiero responder: ${intencion}` },
  ], { temperature: 0.7 })
}

/** Resumir una conversación larga en 2-3 líneas para la doctora. */
export async function resumirConversacion(historial: string) {
  return chat([
    { role: 'system', content: 'Resumí esta conversación de WhatsApp en 2-3 líneas: quién es, qué quiere, y en qué punto está. Español neutro, directo, sin adornos.' },
    { role: 'user', content: historial },
  ], { temperature: 0.3 })
}

/** Sugerir el próximo paso comercial (sin vender agresivo). */
export async function sugerirProximoPaso(historial: string) {
  return chat([
    { role: 'system', content: `Sos un asesor de ventas consultivo (estilo NEPQ de Jeremy Miner). Mirá la conversación y decí en 1-2 frases cuál es el mejor próximo paso para avanzar sin presionar. ${PROHIBIDO}` },
    { role: 'user', content: historial },
  ], { temperature: 0.5 })
}

/** Redactar un protocolo a partir de una descripción libre. */
export async function generarProtocolo(descripcion: string, especialidad?: string) {
  const sys = `Sos asistente de ${especialidad ?? 'un profesional de la salud'}. A partir de una descripción, generá un protocolo de tratamiento estructurado.
Devolvé SOLO un JSON válido, sin markdown, con esta forma exacta:
{"title":"...","description":"...","steps":[{"label":"Semana 1 — ...","done":false}, ...]}
Entre 4 y 8 pasos, cada label empieza con la semana o etapa. Español neutro.`
  const raw = await chat([
    { role: 'system', content: sys },
    { role: 'user', content: descripcion },
  ], { temperature: 0.5 })
  try {
    return JSON.parse(raw.replace(/```json|```/g, '').trim())
  } catch {
    return null
  }
}
