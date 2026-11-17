-- ============================================================================
--  MCD · Las TRES TABLAS que el código pedía y ninguna migración creaba
--  Fecha: 2026-11-17
--
--  CÓMO SE ENCONTRARON. La prueba del esquema real (16 nov, 23:40) compara el
--  nombre de cada columna que el código pide con la columna que existe. Pero
--  su recorrido empezaba con:
--
--      if (tabla in vistas or tabla not in objetos): continue
--
--  …así que una tabla que NO EXISTE no se medía: se saltaba. De las 14 tablas
--  que el código nombra, SEIS no estaban en el esquema, y la lente que dice
--  medirlo daba verde. Es la tercera vez que la ausencia es el defecto.
--
--  Tres de las seis son de MCD y son estas. Las otras tres no van acá:
--    · `comprobantes` no es tabla, es el bucket privado de storage, y la
--      migración 20260707 sí lo crea (falso positivo del recorrido, corregido).
--    · `profiles` y `clinica_artefactos` viven en el OTRO proyecto Supabase,
--      el de TCD, y por eso no se pueden crear acá. Ver el apunte del mapa.
--
--  Todo es additivo (CREATE ... IF NOT EXISTS). Rollback:
--    DROP TABLE IF EXISTS public.notifications, public.patient_notes,
--                         public.agent_config;
-- ============================================================================

-- 1) CONFIGURACIÓN DEL ASISTENTE · pantalla «Tu Asistente ✨»
--    `practitioner_id` es la CLAVE PRIMARIA a propósito: la pantalla guarda
--    con `.upsert({ practitioner_id, … })` sin `onConflict`, y supabase-js
--    resuelve el conflicto por la clave primaria. Con un `id` propio, cada
--    Guardar insertaría una fila nueva y `maybeSingle()` al leer reventaría
--    con más de una.
create table if not exists public.agent_config (
  practitioner_id uuid primary key references public.practitioners(id) on delete cascade,
  tono            text,
  reglas          text,
  firma           text,
  updated_at      timestamptz default now()
);

-- 2) NOTAS DEL PACIENTE · ficha del paciente, bloque de notas
create table if not exists public.patient_notes (
  id              uuid primary key default gen_random_uuid(),
  patient_id      uuid not null references public.patients(id) on delete cascade,
  practitioner_id uuid not null references public.practitioners(id) on delete cascade,
  body            text not null,
  created_at      timestamptz default now()
);
create index if not exists idx_patient_notes_patient
  on public.patient_notes(patient_id, created_at desc);

-- 3) NOTIFICACIONES · la campanita del encabezado
--    Las escribe `src/lib/notify.ts` con la service role key (el webhook de
--    GHL no tiene sesión), y las LEE el sanador con su sesión.
create table if not exists public.notifications (
  id              uuid primary key default gen_random_uuid(),
  practitioner_id uuid not null references public.practitioners(id) on delete cascade,
  tipo            text not null,              -- mensaje | cita | paciente
  titulo          text not null,
  cuerpo          text,
  link            text,
  leida           boolean not null default false,
  created_at      timestamptz default now()
);
create index if not exists idx_notifications_practitioner
  on public.notifications(practitioner_id, created_at desc);

-- ============================================================================
--  RLS · cada sanador solo lo suyo, igual que las seis de la 20260706.
--
--  Acá no es decorado y conviene decir por qué: las tres consultas de
--  `notifications` NO filtran por sanador —el GET hace `select('*')` y el POST
--  hace `update({leida:true}).eq('leida', false)` a secas—. Se apoyan enteras
--  en la política. Sin RLS, un sanador vería las notificaciones de todos y al
--  apretar «marcar todas leídas» marcaría las de todos.
-- ============================================================================
alter table public.agent_config   enable row level security;
alter table public.patient_notes  enable row level security;
alter table public.notifications  enable row level security;

drop policy if exists "own agent config" on public.agent_config;
create policy "own agent config" on public.agent_config
  for all using (auth.uid() = practitioner_id) with check (auth.uid() = practitioner_id);

drop policy if exists "own patient notes" on public.patient_notes;
create policy "own patient notes" on public.patient_notes
  for all using (auth.uid() = practitioner_id) with check (auth.uid() = practitioner_id);

drop policy if exists "own notifications" on public.notifications;
create policy "own notifications" on public.notifications
  for all using (auth.uid() = practitioner_id) with check (auth.uid() = practitioner_id);
