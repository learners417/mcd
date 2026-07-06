-- ============================================================================
--  MCD · AUDITORÍA · Correcciones del Bloque 1
--  Fecha: 2026-07-08
--
--  ⚠️  STAGING PRIMERO. Additiva e idempotente. Corre después de
--      20260706_mcd_mvp.sql y 20260707_mcd_ghl_layer.sql.
-- ============================================================================

-- 1) FIX: el token puede estar pendiente (subcuenta creada, PIT aún no
--    generado). Antes se guardaba el string 'PENDIENTE' → 401 en cadena.
alter table public.ghl_connections
  alter column private_token drop not null;
-- limpiar centinelas si quedó alguno
update public.ghl_connections set private_token = null
  where private_token = 'PENDIENTE';

-- 2) PUENTE TCD↔MCD: las dos apps viven en proyectos Supabase distintos y se
--    mapean por EMAIL. practitioners necesita la columna.
alter table public.practitioners
  add column if not exists email text;
create index if not exists idx_practitioners_email on public.practitioners(lower(email));

-- backfill desde auth.users
update public.practitioners p
  set email = u.email
  from auth.users u
  where u.id = p.id and p.email is null;

-- trigger actualizado: guardar email al crear el usuario
create or replace function public.handle_new_practitioner()
returns trigger language plpgsql security definer as $$
begin
  insert into public.practitioners (id, full_name, brand_name, email)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'full_name','Sanador'),
    coalesce(new.raw_user_meta_data->>'full_name',''),
    new.email
  )
  on conflict (id) do update set email = excluded.email;
  return new;
end; $$;

-- 3) UNA SOLA FUENTE DE VERDAD PARA LA PLATA: cobros (con comprobante).
--    payments y sessions del Bloque 0 quedan OBSOLETAS — no se borran (regla
--    additiva) pero nada debe leerlas ni escribirlas.
comment on table public.payments is
  'OBSOLETA (auditoría 2026-07-08). La fuente de verdad de ingresos es public.cobros (con comprobante obligatorio). No leer ni escribir.';
comment on table public.sessions is
  'OBSOLETA (auditoría 2026-07-08). La fuente de verdad de la agenda es GHL (via ghl_cache, resource=appointments). No leer ni escribir.';

-- 4) LA VISTA COMPLETA: los 6 números del avatar, calculados en la base,
--    incluyendo los que salen de la cache de GHL (JSON).
drop view if exists public.mis_numeros;
create or replace view public.mis_numeros
with (security_invoker = true) as
select
  p.id as practitioner_id,

  -- 1. Pacientes activos (entrega)
  (select count(*) from public.patients pa
     where pa.practitioner_id = p.id and pa.status = 'activo')          as pacientes_activos,

  -- 2. Cobros verificados = el X del X/10 (cinturón Rojo en TCD)
  (select count(*) from public.cobros c
     where c.practitioner_id = p.id)                                    as cobros_totales,

  -- 3. Ingresos del mes (solo cobros con comprobante)
  (select coalesce(sum(c.amount_usd),0) from public.cobros c
     where c.practitioner_id = p.id
       and c.paid_at >= date_trunc('month', now()))                     as ingresos_mes,

  -- 4. Conversaciones esperando respuesta (de la cache GHL)
  coalesce((
    select count(*)
    from public.ghl_cache gc,
         jsonb_array_elements(gc.payload) e
    where gc.practitioner_id = p.id
      and gc.resource = 'conversations'
      and (e->>'sinLeer')::int > 0
  ), 0)                                                                 as conversaciones_esperando,

  -- 5. Citas de hoy (de la cache GHL)
  coalesce((
    select count(*)
    from public.ghl_cache gc,
         jsonb_array_elements(gc.payload) e
    where gc.practitioner_id = p.id
      and gc.resource = 'appointments'
      and (e->>'estado') in ('agendada','confirmada')
      and (e->>'inicio')::timestamptz >= date_trunc('day', now())
      and (e->>'inicio')::timestamptz <  date_trunc('day', now()) + interval '1 day'
  ), 0)                                                                 as citas_hoy,

  -- 6. Personas nuevas esta semana (de la cache GHL)
  coalesce((
    select count(*)
    from public.ghl_cache gc,
         jsonb_array_elements(gc.payload) e
    where gc.practitioner_id = p.id
      and gc.resource = 'contacts'
      and (e->>'creada')::timestamptz >= now() - interval '7 days'
  ), 0)                                                                 as personas_nuevas_semana

from public.practitioners p;
