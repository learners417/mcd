# MCD · CHECKLIST DE DEPLOY — revisión final 2026-07-09

## Verificado en esta revisión (con herramientas reales, no a ojo)
- ✅ TypeScript estricto: 0 errores (compilado contra tipos de Next 14 + Supabase)
- ✅ Las 4 migraciones corren limpias contra Postgres 16 real, EN ORDEN, y son
     idempotentes (correrlas dos veces no rompe nada)
- ✅ Vista `mis_numeros`: los 6 números calculan correcto con datos sembrados
- ✅ Trigger de alta: crea practitioner CON email (necesario para el puente TCD)
- ✅ Cifrado de tokens: cifra/descifra OK, passthrough de tokens legacy OK,
     clave incorrecta rechazada OK
- ✅ Bugs corregidos en esta pasada:
     · webhook: el sync ahora se espera (en Vercel serverless, un
       fire-and-forget muere al responder — jamás corría)
     · portal del paciente: leía la tabla muerta `sessions`; ahora lee la
       agenda REAL de GHL mapeando paciente→contacto (`ghl_contact_id`)
     · portal: `params` compatible con Next 14 y 15
     · pantalla Cobros NUEVA: sin ella, /api/cobros existía pero el avatar no
       tenía forma de registrar un cobro → el X/10 jamás se movía en producción

## Deploy, paso a paso

### 1. Integrar al repo
Copiá `src/` y `supabase/` sobre tu `miclinica-app`. NO copies package.json ni
tsconfig (usá los tuyos). Dependencias requeridas:
```bash
npm install @supabase/ssr @supabase/supabase-js
```

### 2. Migraciones — STAGING → PROD, en este orden exacto
```
20260706_mcd_mvp.sql
20260707_mcd_ghl_layer.sql
20260708_mcd_ghl_audit.sql
20260709_mcd_final_fixes.sql
```
```bash
supabase db push        # primero contra staging. Probás. Recién después prod.
```

### 3. Variables de entorno (local + Vercel, TODAS)
| Variable | Qué es |
|---|---|
| NEXT_PUBLIC_SUPABASE_URL | del proyecto miclinica-digital |
| NEXT_PUBLIC_SUPABASE_ANON_KEY | ídem |
| SUPABASE_SERVICE_ROLE_KEY | server-only |
| GHL_AGENCY_TOKEN | token de agencia (Agency Pro) |
| GHL_COMPANY_ID | ID de tu agencia |
| GHL_SNAPSHOT_ID | Snapshot maestro |
| TOKEN_ENCRYPTION_KEY | ⚠️ generar y GUARDAR en tu gestor de contraseñas |
| GHL_WEBHOOK_SECRET | string largo aleatorio |
| TCD_INTEGRATION_KEY | la misma va después en el env de TCD |
| ADMIN_EMAIL | tu email de login |

Generar la clave de cifrado:
```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

### 4. Git + Vercel
```bash
git checkout -b mcd-mvp        # branch, no directo a main
git add . && git commit -m "feat: MCD MVP — máscara GHL + cobros con evidencia + puente TCD"
git push origin mcd-mvp
```
Vercel: preview deploy automático del branch. Cargar las env → Redeploy.
Cuando el smoke test pase, merge a main.

### 5. Smoke test en el preview (5 minutos, en orden)
1. `/login` → entrar
2. `/dashboard` → carga con los 6 números (en cero, sin errores)
3. `/pacientes` → crear un paciente → "Ver portal ↗" abre el portal con marca
4. `/cobros` → registrar un cobro de prueba CON screenshot → aparece en la
   lista → el dashboard suma ingresos y X/10
5. Conectar TU subcuenta GHL: POST `/api/admin/conectar-cliente`
6. `/api/ghl/health` → `{ ok: true, calendarios: [...] }`
7. POST `/api/ghl/sync?force=1` → revisar `ghl_cache` en Supabase
8. `/dashboard` de nuevo → conversaciones/citas reales de GHL

### 6. Configurar el webhook EN EL SNAPSHOT (una sola vez)
Workflow → acción webhook → `https://TU-APP.vercel.app/api/ghl/webhook?secret=<GHL_WEBHOOK_SECRET>`
en los triggers: mensaje entrante · cita creada · etapa de oportunidad cambiada.
Viaja solo a cada subcuenta nueva.
