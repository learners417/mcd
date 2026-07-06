# MCD · MVP — paquete de integración

Máscara de GHL simplificada. TCD enseña, **MCD opera**, el cliente nunca codea.

## Qué trae este paquete
- `mockup/mcd-mockup.html` — cómo se ve (abrilo en el navegador; toggle Sanador/Paciente)
- `supabase/migrations/20260706_mcd_mvp.sql` — schema del MVP (additivo, staging-first)
- `src/` — la vertical completa en Next.js 14 (App Router)

## Vertical que prueba el producto
1. Sanador se loguea → **/dashboard** (métricas: activos, ingresos del mes, próximas sesiones)
2. **/pacientes** — carga un paciente (genera su `access_token`)
3. **/protocolos** — crea un protocolo (un paso por línea)
4. Asigna protocolo → paciente entra a **/portal/[token]** y ve todo con la marca del sanador
5. **/agenda** — calendario de GHL embebido (URL guardada en `practitioners.ghl_calendar_url`)

---

## Cómo integrarlo en `miclinica-app`

### 0. Dependencias (si no están)
```bash
npm install @supabase/ssr @supabase/supabase-js
```

### 1. Copiar archivos
Copiá `src/` sobre el `src/` del repo. Si ya tenés `lib/supabase/client.ts` o
`server.ts` del patrón de TCD, **NO los pises** sin mirar — este `server.ts`
agrega `createAdminClient()` (lo necesita el portal). Fusioná esa función.

> Si tu proyecto NO usa carpeta `src/`, mové todo un nivel arriba
> (`app/`, `lib/`, `components/`, `middleware.ts` en la raíz) y ajustá el alias `@/`.

### 2. Variables de entorno
Copiá `.env.local.example` → `.env.local` y completá las 3 keys
(Supabase → Settings → API). La **service_role** va también en Vercel,
pero NUNCA como `NEXT_PUBLIC_`.

### 3. Base de datos — ⚠️ STAGING PRIMERO
Regla tuya, la respeto:
```bash
# apuntá el CLI a tu proyecto STAGING, no a producción
supabase db push
```
Antes de correrlo: revisá tus 10 tablas v2.0 por choque de nombres
(`patients`, `protocols`, `sessions`, `payments`). Si ya existen con otra
estructura, frená y reconciliamos el SQL. No corras esto a ciegas en prod.

### 4. Probar local
```bash
npm run dev
# → http://localhost:3000  (redirige a /dashboard, pide login)
```
Creá un usuario en Supabase → Auth, logueate, cargá 1 paciente + 1 protocolo,
abrí "Ver portal ↗".

---

## Subir a GitHub
```bash
cd miclinica-app
git add .
git commit -m "feat: MVP MCD — panel sanador + portal paciente + métricas"
git push origin main
```

## Deploy en Vercel
Ya está conectado. Con el push, Vercel redeploya solo. Solo asegurate de tener
en **Vercel → Settings → Environment Variables** las 3 keys (incluida
`SUPABASE_SERVICE_ROLE_KEY`). Si las agregás después del deploy, hacé
**Redeploy** para que las tome.

---

## Notas de alcance (MVP consciente)
- **Portal por token:** simple para el MVP. El token va en la URL; sirve para
  arrancar, no es seguridad de banco. Cuando escale, se pasa a magic-link.
- **Cobro:** sale del embed de GHL por ahora. `payments` ya está lista para
  cuando conectes cobro nativo (MercadoPago/Payoneer).
- **Métricas:** se calculan en vivo desde la base. Cero planillas.
