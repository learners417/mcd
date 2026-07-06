# MCD · AUDITORÍA DEL BLOQUE 1 — 2026-07-08

Por qué importa: MCD es el negocio recurrente. TCD vende una vez; MCD cobra
todos los meses, para siempre. Un bug acá no es un bug — es churn.

## 🔴 Corregido — crítico
1. **Doble fuente de verdad de la plata.** `payments` (Bloque 0) y `cobros`
   (Bloque 1) coexistían. Ahora: `cobros` (con comprobante) es LA verdad.
   `payments` y `sessions` quedan obsoletas (comentadas en la DB, no borradas).
   El dashboard ya no las lee.
2. **Tokens GHL en texto plano.** Cada PIT da acceso total a la subcuenta de
   un cliente (pacientes, WhatsApp). Ahora se guardan cifrados AES-256-GCM
   (`src/lib/crypto.ts`). La clave vive SOLO en el env → ni con acceso a la
   DB se leen. ⚠️ Generar TOKEN_ENCRYPTION_KEY y guardarla fuera del repo.
3. **Las apps no se hablaban.** El primer cobro (~D45) se registra en MCD,
   pero el cinturón Rojo se otorga en TCD (otro proyecto Supabase). Nuevo
   puente: `GET /api/integrations/tcd?email=...` con header
   `x-integration-key`. TCD consulta cobros verificados → X/10 y cinturón
   Rojo automáticos. UN comprobante, dos apps.
4. **Centinela 'PENDIENTE' como token** → 401 en cadena. Ahora la columna es
   nullable y el sync sale limpio con mensaje claro.

## 🟡 Corregido — robustez
5. **Paginación** en contacts y opportunities (antes: truncaba en 100,
   silenciosamente — la doctora vería "faltan personas").
6. **Timeout 15s + retry con backoff** en 429/5xx.
7. **Detección de "paciente"**: primero `status=won` de GHL (señal dura),
   la regex del nombre de etapa queda de respaldo.
8. **Dashboard** lee `mis_numeros` + agenda real de GHL.

## 🟢 Agregado
9. **Webhook receiver** (`/api/ghl/webhook?secret=...`): GHL avisa (mensaje,
   cita, etapa) → cache invalidada + sync inmediato. Configurarlo UNA vez en
   el Snapshot → viaja solo a cada subcuenta nueva.
10. **Vista `mis_numeros` completa**: los 6 números del avatar en SQL,
    incluidos los que salen del JSON de la cache GHL.

## Migración nueva
`supabase/migrations/20260708_mcd_ghl_audit.sql` — additiva, STAGING primero.
Incluye: token nullable, columna email en practitioners (mapea las dos apps),
tablas obsoletas comentadas, vista completa.

## Env nuevas (agregar en .env.local y Vercel)
- `TOKEN_ENCRYPTION_KEY` (64 hex — generarla y GUARDARLA en tu gestor)
- `GHL_WEBHOOK_SECRET`
- `TCD_INTEGRATION_KEY` (la misma clave va en el env de TCD)

## Pendiente consciente (no es deuda oculta)
- Mapa de etapas determinístico: cuando congeles el Snapshot, pasame los
  nombres exactos de las etapas del pipeline.
- El lado TCD del puente: 20 líneas en Sanar OS que consultan el endpoint y
  otorgan el Rojo. Se hace en el repo de TCD, no acá.
- Comprobantes: hoy son inmutables (no hay delete). Es a propósito —
  la evidencia no se edita. Si algún día hace falta corregir un cobro,
  se agrega uno de ajuste, no se borra.
