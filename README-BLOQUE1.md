# MCD · BLOQUE 1 — La capa GHL (el motor de la máscara)

## Qué se agregó en este bloque
```
supabase/migrations/20260707_mcd_ghl_layer.sql   ← conexiones + cache + cobros + bucket
src/lib/ghl/client.ts                            ← cliente API v2 (server-only)
src/lib/ghl/normalize.ts                         ← GHL crudo → vocabulario del avatar
src/lib/ghl/sync.ts                              ← pull → cache Supabase (10 min frescura)
src/app/api/ghl/sync/route.ts                    ← POST: sincronizar (con ?force=1)
src/app/api/ghl/health/route.ts                  ← GET: ¿la conexión GHL responde?
src/app/api/cobros/route.ts                      ← POST: cobro + screenshot obligatorio
src/app/api/admin/conectar-cliente/route.ts      ← TU onboarding (subcuenta + Snapshot)
```

## La arquitectura en una línea
**GHL (la verdad) → sync server-side → cache en Supabase → UI simple.**
El token jamás toca el browser. La UI lee de `ghl_cache` por RLS.

## Modelo conceptual (fijado en memoria)
- **Dos apps desde el Día 0.** TCD = ganar dinero. MCD = recuperar tiempo.
- **Dos motores en MCD:** Orden (pacientes actuales, D0) + Dinero (leads, se enciende con la campaña).
- **Cobros = evidencia.** Sin screenshot no hay cobro. Misma fuente que el X/10 de TCD.

## Puesta en marcha (en orden)

### 1. Migración — STAGING PRIMERO ⚠️
```bash
supabase db push   # contra staging. Recién después, prod.
```
Corre después de `20260706_mcd_mvp.sql` (usa `practitioners`).

### 2. Env
Completá `.env.local` con las nuevas variables GHL (ver `.env.local.example`)
y cargalas también en Vercel. `GHL_AGENCY_TOKEN`, `SUPABASE_SERVICE_ROLE_KEY`
y los PIT son secretos server-side: jamás `NEXT_PUBLIC_`.

### 3. Conectar el primer cliente (vos, como prueba)
Subcuenta ya existente en tu agencia:
```bash
curl -X POST https://TU-APP.vercel.app/api/admin/conectar-cliente \
  -H "Content-Type: application/json" \
  -H "Cookie: <tu sesión>" \
  -d '{"practitioner_id":"<uuid del user>","location_id":"<loc GHL>","private_token":"<PIT subcuenta>"}'
```
O crear subcuenta nueva CON el Snapshot (modo B): mandá `create:{name,email}` en vez
de `location_id`. El PIT se genera a mano en GHL y se agrega con una segunda llamada.

### 4. Verificar en 10 segundos
Logueado en la app, abrí en el navegador:
```
/api/ghl/health   → { ok: true, calendarios: [...] }  = la máscara respira
```

### 5. Primer sync
```
POST /api/ghl/sync?force=1
```
Después revisá la tabla `ghl_cache` en Supabase: tiene que haber rows de
contacts / conversations / appointments / opportunities con payload normalizado.

## Nota sobre el mapa de etapas
`normalize.ts` mapea las etapas del pipeline de tu Snapshot a las 4 palabras
del avatar (interesada → conversando → agendada → paciente) por regex sobre el
nombre de la etapa. Cuando congeles el Snapshot, pasame los nombres exactos de
las etapas y lo dejamos determinístico (mapa por ID, no por regex).

## Qué viene — Bloque 2
Pantalla **Hoy** (la bandeja diaria: conversaciones esperando + llamadas del día)
+ módulo **Personas**. Leen de `ghl_cache`, cero llamadas a GHL desde la UI.
