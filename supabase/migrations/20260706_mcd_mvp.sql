-- ============================================================================
--  MCD · MVP · Migración additiva
--  Fecha: 2026-07-06
--
--  ⚠️  REGLA DE ORO (post-incidente Supabase):
--      1. Esto se corre PRIMERO en STAGING, nunca directo en producción.
--      2. Todo es CREATE ... IF NOT EXISTS — no borra ni pisa nada existente.
--      3. Antes de aplicar, revisá tus 10 tablas v2.0 por si hay choque de
--         nombres (patients / protocols / sessions / payments). Si ya existen
--         con otra estructura, NO corras esto: pasame el schema real y lo
--         reconcilio. Mejor perder 10 min que perder la base de nuevo.
--      4. Aplicá vía Supabase CLI:  supabase db push  (contra el proyecto staging)
-- ============================================================================

-- 1) SANADOR (dueño de la cuenta). 1:1 con auth.users.
--    Guarda la MARCA que ve el paciente en su portal.
create table if not exists public.practitioners (
  id           uuid primary key references auth.users(id) on delete cascade,
  full_name    text not null,
  brand_name   text,                       -- "Dra. Evelyn Bernal"
  specialty    text,                       -- "Medicina Regenerativa"
  brand_color  text default '#3D6B4F',
  logo_url     text,
  ghl_calendar_url text,                    -- URL del calendario de GHL a embeber
  created_at   timestamptz default now()
);

-- 2) PACIENTES del sanador. access_token = llave del portal (sin registro).
create table if not exists public.patients (
  id             uuid primary key default gen_random_uuid(),
  practitioner_id uuid not null references public.practitioners(id) on delete cascade,
  full_name      text not null,
  email          text,
  status         text not null default 'onboarding',  -- onboarding | activo | pausado
  access_token   uuid not null default gen_random_uuid(),  -- va en el link del portal
  created_at     timestamptz default now()
);
create index if not exists idx_patients_practitioner on public.patients(practitioner_id);
create unique index if not exists idx_patients_token on public.patients(access_token);

-- 3) PROTOCOLOS que crea el sanador (plantillas de tratamiento).
create table if not exists public.protocols (
  id              uuid primary key default gen_random_uuid(),
  practitioner_id uuid not null references public.practitioners(id) on delete cascade,
  title           text not null,
  description     text,
  steps           jsonb default '[]'::jsonb,  -- [{ "label": "...", "done": false }]
  created_at      timestamptz default now()
);
create index if not exists idx_protocols_practitioner on public.protocols(practitioner_id);

-- 4) ASIGNACIÓN protocolo → paciente.
create table if not exists public.patient_protocols (
  id           uuid primary key default gen_random_uuid(),
  patient_id   uuid not null references public.patients(id) on delete cascade,
  protocol_id  uuid not null references public.protocols(id) on delete cascade,
  progress     jsonb default '[]'::jsonb,  -- copia de steps con estado por paciente
  assigned_at  timestamptz default now()
);
create index if not exists idx_pp_patient on public.patient_protocols(patient_id);

-- 5) SESIONES (alimenta "próximas sesiones" y el calendario).
create table if not exists public.sessions (
  id              uuid primary key default gen_random_uuid(),
  practitioner_id uuid not null references public.practitioners(id) on delete cascade,
  patient_id      uuid references public.patients(id) on delete set null,
  title           text default 'Sesión',
  scheduled_at    timestamptz not null,
  status          text default 'agendada',  -- agendada | realizada | cancelada
  price_usd       numeric(10,2) default 0,
  created_at      timestamptz default now()
);
create index if not exists idx_sessions_practitioner on public.sessions(practitioner_id);

-- 6) PAGOS (alimenta "ingresos del mes").
create table if not exists public.payments (
  id              uuid primary key default gen_random_uuid(),
  practitioner_id uuid not null references public.practitioners(id) on delete cascade,
  patient_id      uuid references public.patients(id) on delete set null,
  amount_usd      numeric(10,2) not null,
  paid_at         timestamptz default now(),
  source          text default 'manual'     -- manual | ghl | mercadopago
);
create index if not exists idx_payments_practitioner on public.payments(practitioner_id);

-- ============================================================================
--  RLS · cada sanador solo ve lo suyo. El portal del paciente NO usa RLS de
--  usuario (entra por token) → esas lecturas van por un endpoint server-side
--  con la service role key (ver src/app/portal). NO exponer service key al cliente.
-- ============================================================================
alter table public.practitioners       enable row level security;
alter table public.patients            enable row level security;
alter table public.protocols           enable row level security;
alter table public.patient_protocols   enable row level security;
alter table public.sessions            enable row level security;
alter table public.payments            enable row level security;

-- practitioners: dueño = su propia fila
drop policy if exists "own practitioner" on public.practitioners;
create policy "own practitioner" on public.practitioners
  for all using (auth.uid() = id) with check (auth.uid() = id);

-- helper: ¿la fila pertenece al sanador logueado?
drop policy if exists "own patients" on public.patients;
create policy "own patients" on public.patients
  for all using (auth.uid() = practitioner_id) with check (auth.uid() = practitioner_id);

drop policy if exists "own protocols" on public.protocols;
create policy "own protocols" on public.protocols
  for all using (auth.uid() = practitioner_id) with check (auth.uid() = practitioner_id);

drop policy if exists "own sessions" on public.sessions;
create policy "own sessions" on public.sessions
  for all using (auth.uid() = practitioner_id) with check (auth.uid() = practitioner_id);

drop policy if exists "own payments" on public.payments;
create policy "own payments" on public.payments
  for all using (auth.uid() = practitioner_id) with check (auth.uid() = practitioner_id);

drop policy if exists "own patient_protocols" on public.patient_protocols;
create policy "own patient_protocols" on public.patient_protocols
  for all using (
    exists (select 1 from public.patients p
            where p.id = patient_protocols.patient_id and p.practitioner_id = auth.uid())
  );

-- Trigger: al crear un auth.user, crear su fila practitioner (opcional, cómodo)
create or replace function public.handle_new_practitioner()
returns trigger language plpgsql security definer as $$
begin
  insert into public.practitioners (id, full_name, brand_name)
  values (new.id, coalesce(new.raw_user_meta_data->>'full_name','Sanador'), coalesce(new.raw_user_meta_data->>'full_name',''))
  on conflict (id) do nothing;
  return new;
end; $$;

drop trigger if exists on_auth_user_created_mcd on auth.users;
create trigger on_auth_user_created_mcd
  after insert on auth.users
  for each row execute function public.handle_new_practitioner();
