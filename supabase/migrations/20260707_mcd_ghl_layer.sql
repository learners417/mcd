-- ============================================================================
--  MCD · BLOQUE 1 · Capa GHL (la máscara) + Cobros con evidencia
--  Fecha: 2026-07-07
--
--  ⚠️  STAGING PRIMERO. Additiva, no pisa nada. Corre DESPUÉS de
--      20260706_mcd_mvp.sql (usa la tabla practitioners).
-- ============================================================================

-- 1) CONEXIÓN GHL por sanador (1:1). El Private Integration Token de su
--    subcuenta vive acá. RLS activado SIN policies = ningún cliente del
--    browser puede leerla jamás; solo el service role (server-side).
create table if not exists public.ghl_connections (
  practitioner_id uuid primary key references public.practitioners(id) on delete cascade,
  location_id     text not null,           -- ID de la subcuenta GHL
  private_token   text not null,           -- PIT de la subcuenta (server-only)
  company_id      text,                    -- ID de la agencia (para endpoints agency)
  connected_at    timestamptz default now(),
  last_sync_at    timestamptz
);
alter table public.ghl_connections enable row level security;
-- (deliberadamente SIN policies: deny-all para anon/authenticated)

-- 2) CACHE de recursos GHL. Un row por (sanador, recurso). El payload es el
--    JSON crudo normalizado por la capa de servicio. La UI SIEMPRE lee de acá
--    (rápido), nunca pega directo a GHL desde el cliente.
create table if not exists public.ghl_cache (
  id              uuid primary key default gen_random_uuid(),
  practitioner_id uuid not null references public.practitioners(id) on delete cascade,
  resource        text not null,           -- contacts | conversations | appointments | opportunities | pipelines | calendars
  payload         jsonb not null default '[]'::jsonb,
  fetched_at      timestamptz not null default now(),
  unique (practitioner_id, resource)
);
alter table public.ghl_cache enable row level security;
-- El sanador puede LEER su cache (la UI la consulta directo por RLS).
-- Escribe SOLO el service role desde la capa de sync.
drop policy if exists "read own ghl cache" on public.ghl_cache;
create policy "read own ghl cache" on public.ghl_cache
  for select using (auth.uid() = practitioner_id);

-- 3) COBROS con evidencia (screenshot del comprobante — misma lógica que los
--    cinturones de TCD: hito real y verificable). Fuente de verdad de
--    "Ingresos del mes" y del contador X/10.
create table if not exists public.cobros (
  id              uuid primary key default gen_random_uuid(),
  practitioner_id uuid not null references public.practitioners(id) on delete cascade,
  patient_id      uuid references public.patients(id) on delete set null,
  amount_usd      numeric(10,2) not null check (amount_usd > 0),
  concept         text,                            -- "Sesión inicial", "Programa 12 semanas"
  receipt_path    text not null,                   -- path en el bucket 'comprobantes' (OBLIGATORIO)
  paid_at         timestamptz not null default now(),
  created_at      timestamptz default now()
);
create index if not exists idx_cobros_practitioner on public.cobros(practitioner_id);
alter table public.cobros enable row level security;
drop policy if exists "own cobros" on public.cobros;
create policy "own cobros" on public.cobros
  for all using (auth.uid() = practitioner_id) with check (auth.uid() = practitioner_id);

-- 4) STORAGE: bucket privado para comprobantes. Cada sanador escribe/lee solo
--    en su carpeta {practitioner_id}/...
insert into storage.buckets (id, name, public)
values ('comprobantes', 'comprobantes', false)
on conflict (id) do nothing;

drop policy if exists "own comprobantes read" on storage.objects;
create policy "own comprobantes read" on storage.objects
  for select using (
    bucket_id = 'comprobantes'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "own comprobantes write" on storage.objects;
create policy "own comprobantes write" on storage.objects
  for insert with check (
    bucket_id = 'comprobantes'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

-- 5) Vista de conveniencia: los 6 números, calculados en la base.
--    (security_invoker: respeta el RLS del que consulta)
create or replace view public.mis_numeros
with (security_invoker = true) as
select
  p.id as practitioner_id,
  (select count(*) from public.patients pa
     where pa.practitioner_id = p.id and pa.status = 'activo')            as pacientes_activos,
  (select count(*) from public.cobros c
     where c.practitioner_id = p.id)                                      as cobros_totales,   -- contador X/10
  (select coalesce(sum(c.amount_usd),0) from public.cobros c
     where c.practitioner_id = p.id
       and c.paid_at >= date_trunc('month', now()))                       as ingresos_mes
from public.practitioners p;
