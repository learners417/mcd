-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║  LAS DOS COLUMNAS QUE EL CÓDIGO PEDÍA Y EL ESQUEMA NO TENÍA              ║
-- ╚══════════════════════════════════════════════════════════════════════════╝
--
-- Medido el 16 de noviembre de 2026 a las 23:40, corriendo las cuatro
-- migraciones contra un PostgreSQL de verdad y preguntándole después a
-- `information_schema` qué columnas quedaron: de los 45 pares tabla.columna
-- que el código nombra, DOS no existían.
--
-- No es un detalle de prolijidad. PostgREST no ignora la columna que no
-- conoce: contesta 400 con `42703` y la sentencia ENTERA no se ejecuta.
--
--   · `patients.phone` — la ficha del paciente la pide en su `select`, así que
--     el select falla, `data` llega en null y la pantalla hace
--     `if (!p) return notFound()`. Resultado medido: 404 en la ficha de
--     CUALQUIER paciente. Y el emparejado con los contactos de GHL
--     (`src/lib/ghl/sync.ts`) lee la misma columna, así que tampoco empareja.
--
--   · `practitioners.inversion_mensual` — la pide el Tablero, el Admin y
--     «Mi marca». En «Mi marca» viaja DENTRO del mismo `update` que la marca,
--     la especialidad, el color y el link del calendario: al rechazarse la
--     sentencia se caen los cinco campos. Medido contra PostgreSQL: el sanador
--     escribe su marca, aprieta Guardar, la base no cambia nada y la pantalla
--     no muestra ningún error.
--
-- `if not exists` a propósito: si la base viva ya las tiene puestas a mano
-- desde el panel de Supabase, este archivo no hace nada y queda como la
-- constancia de que el esquema del repo también las tiene. Una instalación
-- nueva —que es lo que significa vender esto— ya no nace rota.
--
-- Las dos nacen nulas y sin valor por defecto, que es contra lo que el código
-- está escrito: `p.phone ? ... : ''` en la ficha, `me?.inversion_mensual ?? ''`
-- en el formulario de marca y `?? 0` en el Tablero.

alter table public.patients
  add column if not exists phone text;

alter table public.practitioners
  add column if not exists inversion_mensual numeric;

comment on column public.patients.phone is
  'Teléfono del paciente. Hoy ninguna pantalla lo escribe: lo lee la ficha para mostrarlo y el emparejado con GHL para encontrar al contacto por los últimos 8 dígitos.';
comment on column public.practitioners.inversion_mensual is
  'USD que el sanador pone por mes en anuncios. Lo escribe él en «Mi marca»; el Tablero lo usa para las tarjetas Invertido y Retorno.';
