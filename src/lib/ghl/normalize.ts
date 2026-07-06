// ============================================================================
//  MCD · Capa GHL · Normalizadores
//  GHL crudo → formas simples para el avatar. Acá vive la traducción de
//  vocabulario: nunca "lead/pipeline/opportunity" hacia la UI.
// ============================================================================

// --- Persona (Contact) -------------------------------------------------------
export type Persona = {
  id: string
  nombre: string
  telefono: string | null
  email: string | null
  origen: string | null        // ej: campaña CTWA
  creada: string               // ISO
  tags: string[]
}

export function toPersona(c: any): Persona {
  return {
    id: c.id,
    nombre: [c.firstName, c.lastName].filter(Boolean).join(' ') || c.contactName || 'Sin nombre',
    telefono: c.phone ?? null,
    email: c.email ?? null,
    origen: c.source ?? null,
    creada: c.dateAdded ?? c.createdAt ?? new Date().toISOString(),
    tags: c.tags ?? [],
  }
}

// --- Conversación (WhatsApp / KAI) ------------------------------------------
export type Conversacion = {
  id: string
  contactId: string | null
  nombre: string
  ultimoMensaje: string
  fecha: string                // ISO
  sinLeer: number              // >0 = espera respuesta del sanador
  canal: string                // WhatsApp | SMS | etc
}

export function toConversacion(c: any): Conversacion {
  return {
    id: c.id,
    contactId: c.contactId ?? null,
    nombre: c.fullName || c.contactName || 'Sin nombre',
    ultimoMensaje: c.lastMessageBody ?? '',
    fecha: c.lastMessageDate
      ? new Date(Number(c.lastMessageDate) || c.lastMessageDate).toISOString()
      : new Date().toISOString(),
    sinLeer: Number(c.unreadCount ?? 0),
    canal: c.lastMessageType?.includes('WHATSAPP') ? 'WhatsApp' : (c.type ?? 'Mensaje'),
  }
}

// --- Cita (Calendar Event) ---------------------------------------------------
export type Cita = {
  id: string
  titulo: string
  contactId: string | null
  inicio: string               // ISO
  fin: string | null
  estado: 'agendada' | 'confirmada' | 'realizada' | 'no_vino' | 'cancelada'
}

const ESTADO_MAP: Record<string, Cita['estado']> = {
  new: 'agendada', booked: 'agendada', confirmed: 'confirmada',
  showed: 'realizada', noshow: 'no_vino', cancelled: 'cancelada', invalid: 'cancelada',
}

export function toCita(e: any): Cita {
  const raw = String(e.appointmentStatus ?? e.status ?? 'booked').toLowerCase()
  return {
    id: e.id,
    titulo: e.title ?? 'Sesión',
    contactId: e.contactId ?? null,
    inicio: e.startTime ?? e.start_time ?? new Date().toISOString(),
    fin: e.endTime ?? e.end_time ?? null,
    estado: ESTADO_MAP[raw] ?? 'agendada',
  }
}

// --- Etapa de venta (Opportunity) --------------------------------------------
// Las etapas del pipeline del Snapshot se mapean a 4 palabras del avatar.
// El nombre real de la etapa GHL viene del Snapshot de Javo; este mapa se
// ajusta UNA vez cuando el Snapshot esté congelado.
export type EtapaVenta = 'interesada' | 'conversando' | 'agendada' | 'paciente'

export type Venta = {
  id: string
  contactId: string | null
  nombre: string
  etapa: EtapaVenta
  etapaGhl: string             // nombre crudo de la etapa, por si el mapa falla
  estadoGhl: string            // open | won | lost | abandoned (señal dura)
  valor: number
  actualizada: string          // ISO
}

export function toVenta(o: any, stageNames: Record<string, string>): Venta {
  const stageName = (stageNames[o.pipelineStageId] ?? '').toLowerCase()
  const status = String(o.status ?? 'open').toLowerCase() // open|won|lost|abandoned

  // Señal DURA primero: el status de GHL. La regex del nombre de etapa es respaldo.
  let etapa: EtapaVenta = 'interesada'
  if (status === 'won' || /(paciente|ganad|won|cliente)/.test(stageName)) etapa = 'paciente'
  else if (/(agenda|llamada|cita)/.test(stageName)) etapa = 'agendada'
  else if (/(convers|calific|whats)/.test(stageName)) etapa = 'conversando'

  return {
    id: o.id,
    contactId: o.contactId ?? o.contact?.id ?? null,
    nombre: o.name ?? o.contact?.name ?? 'Sin nombre',
    etapa,
    etapaGhl: stageNames[o.pipelineStageId] ?? o.pipelineStageId ?? '',
    estadoGhl: status,
    valor: Number(o.monetaryValue ?? 0),
    actualizada: o.updatedAt ?? o.createdAt ?? new Date().toISOString(),
  }
}

/** pipelines crudos → { stageId: stageName } para toVenta */
export function stageNameIndex(pipelines: any[]): Record<string, string> {
  const idx: Record<string, string> = {}
  for (const p of pipelines) for (const s of p.stages ?? []) idx[s.id] = s.name
  return idx
}
