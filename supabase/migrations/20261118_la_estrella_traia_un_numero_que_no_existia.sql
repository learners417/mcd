-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║  EL TABLERO PEDÍA UN SÉPTIMO NÚMERO Y LA VISTA TENÍA SEIS                ║
-- ╚══════════════════════════════════════════════════════════════════════════╝
--
-- Medido el 18 de noviembre de 2026, levantando las migraciones contra un
-- PostgreSQL 16 de verdad y preguntándole a `information_schema` qué columnas
-- quedaron en `public.mis_numeros`:
--
--     practitioner_id · pacientes_activos · cobros_totales · ingresos_mes
--     conversaciones_esperando · citas_hoy · personas_nuevas_semana
--
-- Siete columnas. El Tablero —`src/app/(app)/dashboard/page.tsx`— lee OCHO:
-- esas siete y `roi_mes`, que no existe en ningún `.sql` del repo. Y no lo lee
-- de adorno: es la condición del cartel de abajo, el que dice
--
--     «Este mes tu sistema facturó $X USD. Tu inversión en MiClínica se pagó
--      N×.»
--
-- `Number(n?.roi_mes ?? 0) > 0` con la columna ausente es `0 > 0`: falso
-- siempre. Esa rama no se dibujó nunca —desde el 8 de julio, cuando se
-- escribió la vista completa— y la pantalla degrada en silencio al cartel
-- corto, el que solo dice lo facturado. No hay error, no hay 400: PostgREST
-- devuelve las siete columnas que sí existen y la octava llega `undefined`.
--
-- Por qué se puede cerrar solo y no es un texto que espere un clic: el cartel
-- ya está escrito en el repo y no se toca ni una palabra. La CUENTA tampoco se
-- inventa — el mismo Tablero ya la hace a mano tres líneas más arriba, en la
-- tarjeta «Retorno»:
--
--     (Number(n?.ingresos_mes ?? 0) / Number(me?.inversion_mensual)).toFixed(1)
--
-- O sea: ingresos del mes ÷ inversión mensual, a un decimal. Esto es esa misma
-- cuenta, movida a la base para que las dos digan lo mismo. Es la forma que ya
-- apareció tres veces en estos repos —el contrato del puente el 16, los cinco
-- nombres del impreso, las políticas escritas dos veces el 18—: dos copias de
-- una cuenta y nadie atándolas.
--
-- Qué pasa cuando no hay inversión cargada: `nullif(...,0)` deja la división
-- en null y `coalesce` la baja a 0, así que `roi_mes > 0` sigue siendo falso y
-- el cartel largo no aparece. Nadie ve un «se pagó 0×» ni una división por
-- cero. Es el comportamiento de hoy, sin cambio visible, para el sanador que
-- todavía no cargó lo que invierte.
--
-- `security_invoker = true` se vuelve a escribir en el `create`: NO es
-- decorado y no se hereda. Una vista sin esa opción corre con los permisos de
-- SU DUEÑO y se saltea el RLS de `practitioners`, `patients`, `cobros` y
-- `ghl_cache`: cualquier sanador con sesión leería los números de todos
-- cambiando el filtro, porque el filtro vive en el cliente
-- (`.eq('practitioner_id', user?.id)`). Medido hoy: con la opción puesta, cada
-- sanador ve UNA fila —la suya— y sin sesión no se ve ninguna.

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
  ), 0)                                                                 as personas_nuevas_semana,

  -- 7. El séptimo, el que el Tablero pedía y no existía: ingresos del mes
  --    sobre lo invertido, a un decimal. Sin inversión cargada queda en 0 y el
  --    cartel largo no se dibuja, igual que hoy.
  coalesce(
    round(
      (select coalesce(sum(c.amount_usd),0) from public.cobros c
         where c.practitioner_id = p.id
           and c.paid_at >= date_trunc('month', now()))
      / nullif(p.inversion_mensual, 0)
    , 1)
  , 0)                                                                  as roi_mes

from public.practitioners p;

comment on view public.mis_numeros is
  'Los 7 numeros del Tablero, calculados en la base. security_invoker = true: '
  'respeta el RLS de practitioners/patients/cobros/ghl_cache, asi que cada '
  'sanador ve solo su fila. roi_mes = ingresos_mes / inversion_mensual, a un '
  'decimal, 0 cuando no hay inversion cargada.';
