# MCD v2 · LA VERSIÓN DEL LANZAMIENTO CONJUNTO
## G6 de la Cirugía Total — lista para los ~20 clientes · 2026-07-06

## Qué es esta versión
La app que el cliente abre el DÍA 1 junto con TCD. Dos motores:
- **Motor ORDEN (D0):** Hoy · Pacientes (con ficha) · Protocolos · Agenda · Cobros · Mi marca
- **Motor DINERO (D29):** Personas (el recorrido) · conversaciones esperando en Hoy

## Pantallas (verificadas con build real)
| Ruta | Qué hace |
|---|---|
| /dashboard (**Hoy**) | La bandeja diaria: conversaciones esperando + citas de hoy + los 6 números + la guía del primer día ("carga tus pacientes actuales") |
| /personas | Interesadas → Conversando → Agendadas → Pacientes (desde GHL, vocabulario humano) |
| /pacientes + /pacientes/[id] | Alta + FICHA: asignar protocolo, marcar avances (el paciente los ve al instante), copiar el link del portal, estado |
| /protocolos | Crear protocolos con pasos |
| /agenda | El calendario embebido (URL desde Mi marca) |
| /cobros | Registrar con comprobante obligatorio (alimenta X/10 y el Rojo) |
| /marca | Nombre, especialidad, color, calendario — su marca en el portal |
| /admin | SOLO vos: conectar subcuentas (Location + PIT cifrado), estado de cada cliente |
| /portal/[token] | Lo que ve SU paciente, con SU marca |

## Deploy (mismo flujo de siempre)
1. Subir este contenido al repo `mcd` (reemplazar `src/` completo). Vercel redeploya.
2. Env nueva en Vercel: `NEXT_PUBLIC_APP_URL=https://mcd-eight.vercel.app`
   (+ `ADMIN_EMAIL` con tu mail si aún no está — habilita /admin)
3. La base ya está (mcd-setup-completo.sql). Sin migraciones nuevas.

## El circuito del Día 1 (lo que la sesión 1 de TCD le pide)
1. Entra a MCD → Hoy le muestra la guía del primer paso
2. Carga sus pacientes actuales → asigna protocolo a cada uno
3. Copia el link del portal → se lo manda por WhatsApp a cada paciente
4. Su práctica ya vive en un solo lugar. Motor Orden: encendido.

## Los enganches con la Cirugía (para G7)
- TCD menú "🏥 Mi Clínica" → link directo a esta app (login separado v1, según la lista de congelamiento)
- El Rojo automático: TCD consulta `GET /api/integrations/tcd?email=...` (ya vivo)
- El D29 en TCD → link a /personas ("tu Motor Dinero acaba de encenderse")

## Pendiente consciente (no bloquea el acceso)
- Mapa determinístico de etapas cuando congeles el Snapshot (hoy: regex + status won)
- Tutoriales técnicos (dominio/calendario) — tu grabación, van linkeados desde TCD
- El matcher paciente↔contacto GHL automático (hoy: campo manual en la base)
