-- ============================================================================
--  MCD · REVISIÓN FINAL pre-deploy
--  Fecha: 2026-07-09 · ⚠️ STAGING PRIMERO. Additiva e idempotente.
-- ============================================================================

-- Mapeo paciente (MCD) → contacto (GHL). Permite que el portal del paciente
-- muestre SU próxima cita desde la agenda real. Se completa a mano o en un
-- futuro matcher por teléfono/email.
alter table public.patients
  add column if not exists ghl_contact_id text;
create index if not exists idx_patients_ghl_contact
  on public.patients(ghl_contact_id);
