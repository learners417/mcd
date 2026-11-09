#!/usr/bin/env python3
"""
auditoria.py — LA BATERÍA COMPLETA DE MCD.

Regla de la casa, la misma que en TCD: nada sale a producción sin esto en
verde.  Corre:  python3 auditoria.py   (desde la raíz del repo, con
node_modules instalado).  Con  --rapido  se saltea el build, que es lo único
que tarda.

═══ POR QUÉ ESTA BATERÍA EXISTE, Y POR QUÉ RECIÉN AHORA ═══

MCD es el negocio recurrente: TCD vende una vez, MCD cobra todos los meses.
Su propio README de auditoría lo dice en la primera línea — «un bug acá no es
un bug, es churn» — y aun así el repo no tenía NINGUNA prueba. Ni una. El
package.json tenía tres scripts (dev, build, start) y ninguno miraba si el
código es correcto: ni `tsc --noEmit`.

Así que esta es la primera, y lo que protege no se eligió por gusto. Cada
lente de acá abajo defiende algo que YA ESTÁ BIEN HOY y que, si se rompe, el
que paga lo paga: su llave, su plata, su token, su lista completa. Lo que se
midió antes de escribirlas está anotado en cada sección.
"""
import re, os, sys, glob, subprocess

RAPIDO = '--rapido' in sys.argv
F = 0

def check(nombre, ok, detalle=''):
    global F
    print(('  ✓ ' if ok else '  ✗ ') + nombre + (f' — {detalle}' if detalle and not ok else ''))
    if not ok:
        F += 1

def rd(f):
    return open(f, encoding='utf-8', errors='replace').read()

def solo_codigo(s):
    """El archivo sin comentarios.

    Una lente que marca en rojo al comentario que explica por qué algo se
    sacó, ensena a borrar la explicación. La misma decisión que en TCD.
    """
    s = re.sub(r'/\*[\s\S]*?\*/', '', s)
    return re.sub(r'^\s*//.*$', '', s, flags=re.M)

TSX = sorted(glob.glob('src/**/*.ts', recursive=True) + glob.glob('src/**/*.tsx', recursive=True))
RUTAS = sorted(glob.glob('src/app/api/**/route.ts', recursive=True))
SQL = sorted(glob.glob('supabase/migrations/*.sql'))


# ═══════════════════════════════════════════════════════════════════════════
print('\n════ 1 · EL CÓDIGO COMPILA ════')
# Lo primero que faltaba: nadie corría el compilador. Hoy pasa limpio, y esta
# lente es lo que hace que siga pasando limpio.
r = subprocess.run(['npx', 'tsc', '--noEmit'], capture_output=True, text=True)
check('`tsc --noEmit` en verde', r.returncode == 0,
      (r.stdout + r.stderr).strip().split('\n')[0][:160])

if RAPIDO:
    print('  ⧗ el build se saltea con --rapido')
else:
    rb = subprocess.run(['npx', 'next', 'build'], capture_output=True, text=True,
                        env={**os.environ, 'NEXT_TELEMETRY_DISABLED': '1'})
    check('`next build` en verde', rb.returncode == 0,
          (rb.stdout + rb.stderr).strip().split('\n')[-1][:160])


# ═══════════════════════════════════════════════════════════════════════════
print('\n════ 2 · NINGUNA PANTALLA SIN LLAVE ════')
#
# LO QUE SE MIDIÓ: la lista de rutas protegidas es un array escrito a mano en
# `src/lib/supabase/middleware.ts`. Hoy están las diez carpetas de `(app)/` y
# está completa. Pero es a mano: agregar una pantalla y olvidarse de la lista
# la deja abierta sin sesión, y lo que hay detrás de esas pantallas son los
# pacientes de un cliente. Esto es lo que vuelve imposible ese olvido.
#
mw = rd('src/lib/supabase/middleware.ts')
m = re.search(r'isProtected\s*=\s*\[(.*?)\]', mw, re.S)
check('la lista de rutas protegidas sigue existiendo', bool(m))
protegidas = set(re.findall(r"'([^']+)'", m.group(1))) if m else set()

base = 'src/app/(app)'
pantallas = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))) if os.path.isdir(base) else []
check('hay pantallas de cliente que proteger', len(pantallas) > 0)
sin_llave = [p for p in pantallas if f'/{p}' not in protegidas]
check(f'las {len(pantallas)} pantallas de `(app)` piden sesión',
      not sin_llave, 'abiertas sin sesión: ' + ', '.join(sin_llave))

# Y el portal del paciente NO pide sesión, a propósito: entra con su token y
# no tiene cuenta. Si alguien lo mete en la lista, el paciente queda afuera de
# su propio protocolo.
check('el portal del paciente sigue abierto por su token, no por sesión',
      '/portal' not in protegidas)
check('y el login también', '/login' not in protegidas)


# ═══════════════════════════════════════════════════════════════════════════
print('\n════ 3 · LA PLATA TIENE UNA SOLA FUENTE ════')
#
# LO QUE SE MIDIÓ: la auditoría del 8 de julio dejó `cobros` como LA verdad y
# `payments`/`sessions` obsoletas. Hoy nadie las lee — comprobado. Esta lente
# es para que no vuelvan.
#
lee_viejas = [f for f in TSX
              if re.search(r"from\(['\"](payments|sessions)['\"]\)", solo_codigo(rd(f)))]
check('nadie lee `payments` ni `sessions` — las obsoletas quedaron obsoletas',
      not lee_viejas, ', '.join(lee_viejas))

# Y el nombre del número que viaja a TCD tiene que ser cierto.
#
# `cobros_verificados` cuenta FILAS de `cobros`, sin filtrar por nada. Es
# honesto SOLO mientras una fila no pueda existir sin su comprobante: la
# columna `receipt_path` es `not null`. El día que alguien la haga nullable,
# ese número empieza a mentir y el cinturón Rojo de TCD se otorga sin
# evidencia. Las dos mitades van juntas o no van.
sql_todo = '\n'.join(rd(f) for f in SQL)
tabla = re.search(r'create table if not exists public\.cobros \((.*?)\n\);', sql_todo, re.S)
check('la tabla `cobros` sigue declarada', bool(tabla))
if tabla:
    check('un cobro no puede existir sin su comprobante (`receipt_path not null`)',
          bool(re.search(r'receipt_path\s+text\s+not null', tabla.group(1))))
    check('y su monto es positivo, no cero', 'amount_usd > 0' in tabla.group(1))
check('nadie volvió nullable el comprobante en una migración posterior',
      not re.search(r'alter\s+column\s+receipt_path\s+drop\s+not\s+null', sql_todo, re.I))

puente = rd('src/app/api/integrations/tcd/route.ts')
check('el puente cuenta cobros de `cobros`, que es la fuente',
      "from('cobros')" in puente)


# ═══════════════════════════════════════════════════════════════════════════
print('\n════ 4 · CADA PUERTA PIDE SU LLAVE ════')
#
# LO QUE SE MIDIÓ: las diez rutas de API tienen guarda — nueve por sesión o
# admin, y el puente y el webhook por clave. Eso está bien hoy. Lo que estaba
# desparejo es CÓMO se compara la clave: el webhook usa `timingSafeEqual` y el
# puente usaba `!==` pelado. Se igualó, y esto lo deja igualado.
#
GUARDAS = ('auth.getUser', 'x-integration-key', 'GHL_WEBHOOK_SECRET')
sin_guarda = [f for f in RUTAS if not any(g in rd(f) for g in GUARDAS)]
check(f'las {len(RUTAS)} rutas de API piden algo antes de contestar',
      not sin_guarda, ', '.join(sin_guarda))

for ruta, env in (('src/app/api/integrations/tcd/route.ts', 'TCD_INTEGRATION_KEY'),
                  ('src/app/api/ghl/webhook/route.ts', 'GHL_WEBHOOK_SECRET')):
    # Sin comentarios: el comentario que EXPLICA por qué la comparación es en
    # tiempo constante nombra `timingSafeEqual`, así que mirar el archivo crudo
    # daba verde aunque la comparación de verdad hubiera vuelto al `!==`.
    # Medido: el 9 de noviembre, reintroduciendo el defecto a propósito.
    txt = solo_codigo(rd(ruta))
    check(f'{os.path.basename(os.path.dirname(ruta))}: la clave se compara en tiempo constante',
          'timingSafeEqual' in txt)
    check(f'{os.path.basename(os.path.dirname(ruta))}: sin la clave en el entorno, no entra nadie',
          f'process.env.{env}' in txt and re.search(r'status:\s*401', txt) is not None)
    # Comparar largos antes evita que timingSafeEqual tire excepción con
    # buffers de distinto tamaño — que sería un 500 en vez de un 401.
    check(f'{os.path.basename(os.path.dirname(ruta))}: un largo distinto da 401, no un error',
          '.length !==' in txt)


# ═══════════════════════════════════════════════════════════════════════════
print('\n════ 5 · EL TOKEN DEL CLIENTE NO VIAJA EN CLARO ════')
#
# LO QUE SE MIDIÓ: cada PIT de GHL da acceso total a la subcuenta de un
# cliente — sus pacientes y su WhatsApp. Desde julio se guardan cifrados
# (AES-256-GCM, `src/lib/crypto.ts`) con la clave solo en el entorno. Esta
# lente cuida las dos puntas: que se siga cifrando al escribir, y que el
# service role nunca cruce al navegador.
#
cripto = rd('src/lib/crypto.ts')
check('el cifrado del token sigue siendo AES-256-GCM', 'aes-256-gcm' in cripto)
check('y su clave vive solo en el entorno',
      'process.env.TOKEN_ENCRYPTION_KEY' in cripto)
check('la clave no está escrita en el repo',
      not re.search(r"TOKEN_ENCRYPTION_KEY\s*=\s*['\"][0-9a-fA-F]{32,}", cripto))

escriben_token = [f for f in TSX
                  if re.search(r"update\(\{[^}]*ghl_token|insert\(\{[^}]*ghl_token", solo_codigo(rd(f)))]
sin_cifrar = [f for f in escriben_token if 'encryptToken' not in rd(f)]
check('todo el que guarda un token lo cifra', not sin_cifrar, ', '.join(sin_cifrar))

# El service role en el navegador sería la base entera abierta.
en_cliente = []
for f in TSX:
    t = rd(f)
    if "'use client'" in t.split('\n')[0] or '"use client"' in t.split('\n')[0]:
        if 'createAdminClient' in solo_codigo(t) or 'SERVICE_ROLE' in solo_codigo(t):
            en_cliente.append(f)
check('ninguna pantalla del navegador toca el service role',
      not en_cliente, ', '.join(en_cliente))
check('y el service role se lee del entorno, en un solo archivo',
      sum(1 for f in TSX if 'SUPABASE_SERVICE_ROLE' in solo_codigo(rd(f))) == 1)


# ═══════════════════════════════════════════════════════════════════════════
print('\n════ 6 · LAS LISTAS LLEGAN COMPLETAS ════')
#
# LO QUE SE MIDIÓ: antes de julio, contactos y oportunidades se truncaban en
# 100 sin avisar — «faltan personas», que es lo que ve el cliente. Hoy las dos
# paginan. Un `limit` sin bucle vuelve a truncar en silencio, y en silencio es
# lo peor: nadie reporta un paciente que no apareció.
#
cliente = rd('src/lib/ghl/client.ts')
for nombre, fn in (('contactos', 'getContacts'), ('oportunidades', 'getOpportunities')):
    cuerpo = re.search(rf'export async function {fn}[\s\S]*?\n\}}', cliente)
    check(f'{nombre}: la función sigue existiendo', bool(cuerpo))
    if cuerpo:
        check(f'{nombre}: pide página tras página, no las primeras cien',
              'while' in cuerpo.group(0))
        check(f'{nombre}: y tiene un techo, para no colgarse pidiendo para siempre',
              'MAX_ITEMS' in cuerpo.group(0))
check('el techo está declarado una sola vez', cliente.count('const MAX_ITEMS') == 1)
check('y la llamada reintenta cuando GHL responde 429 o 5xx',
      '429' in cliente and 'retry' in cliente.lower())


# ═══════════════════════════════════════════════════════════════════════════
print('\n════ 7 · NINGÚN SECRETO ESCRITO EN EL REPO ════')
#
# Lo que entra al repo queda en el historial de git para siempre: un secreto
# pegado una vez no se borra sacándolo, hay que rotarlo. Más barato que no
# entre.
#
SOSPECHOSOS = [
    (r'sk-[A-Za-z0-9]{20,}', 'una clave de OpenAI o Anthropic'),
    (r'eyJ[A-Za-z0-9_-]{30,}\.[A-Za-z0-9_-]{30,}', 'un JWT de Supabase'),
    (r'pit-[0-9a-f-]{20,}', 'un token de GHL'),
]
encontrados = []
for f in TSX + SQL:
    t = rd(f)
    for patron, que in SOSPECHOSOS:
        if re.search(patron, t):
            encontrados.append(f'{f}: {que}')
check('no hay claves ni tokens escritos en el código',
      not encontrados, '; '.join(encontrados))

# Y el archivo del entorno no puede entrar al repo, porque de git no vuelve:
# un `.env.local` subido una vez obliga a rotar TODAS las claves.
#
# LO QUE SE MIDIÓ: MCD no tenía `.gitignore`. El primer commit con `git add -A`
# se llevó 10.496 archivos —`node_modules` y `.next` enteros— y GitHub lo
# rechazó. Sin ese rechazo, el repo quedaba con 2,2 millones de líneas que
# nadie escribió, y nada impedía que la próxima vez entrara el `.env.local`.
check('el repo tiene `.gitignore`', os.path.exists('.gitignore'))
if os.path.exists('.gitignore'):
    ign = rd('.gitignore')
    for linea, que in (('node_modules/', 'las dependencias'),
                       ('.next/', 'el build de Next'),
                       ('.env.local', 'el entorno con las claves'),
                       ('.vercel', 'la carpeta de Vercel')):
        check(f'{que} no entra al repo', linea in ign)
_rastreados = subprocess.run(['git', 'ls-files'], capture_output=True, text=True).stdout.split('\n')
_colados = [f for f in _rastreados
            if f.startswith(('node_modules/', '.next/')) or f.endswith('.env.local')]
check('y ninguno está rastreado hoy', not _colados,
      f'{len(_colados)} archivo(s) colado(s)')


# ═══════════════════════════════════════════════════════════════════════════
print('\n════ 8 · LAS DOS APPS SE NOMBRAN IGUAL ════')
#
# El puente tiene un lado en cada repo. Esta lente mira SOLO el lado de acá:
# que el contrato que TCD consume no cambie de nombre sin que nadie se entere.
# El lado de TCD —y la ida y vuelta de verdad— es el turno 7.
#
CONTRATO = ['cobros_verificados', 'total_usd', 'primer_cobro', 'nombre', 'email']
faltan = [c for c in CONTRATO if c not in puente]
check('el puente sigue devolviendo los cinco campos que TCD lee',
      not faltan, 'faltan: ' + ', '.join(faltan))
check('y sigue pidiendo el email por querystring', "searchParams.get('email')" in puente)
check('y contesta 404 cuando el cliente no está en MCD', 'status: 404' in puente)

# ── LA BÚSQUEDA DEL CLIENTE, QUE ERA EL AGUJERO ─────────────────────────
#
# LO QUE SE MIDIÓ (9 de noviembre, turno 7): la columna `email` de
# `practitioners` existe —la agregó la migración del 8 de julio— y su índice
# es `on practitioners(lower(email))`. Pero la búsqueda era
# `.eq('email', email)`: distingue mayúsculas y no usa ese índice. Una sola
# mayúscula guardada en la columna y este endpoint contesta 404.
#
# Y ese 404 no se lee como «no lo encuentro»: del otro lado del puente se
# traduce a «todavía no cobró». El cliente que vendió se queda sin su
# cinturón Rojo y con el día 31 trabado, en silencio y para siempre. El
# agujero no estaba en los nombres del contrato, estaba un renglón antes.
#
puente_codigo = solo_codigo(puente)

# Cada una de estas tres se probó contra su propio fallo reintroduciendo el
# defecto en el archivo: con el `.eq` pelado como única búsqueda, las tres
# se ponen rojas.
check('la búsqueda del cliente no distingue mayúsculas',
      bool(re.search(r"\.ilike\(\s*'email'", puente_codigo)))
check('y lo que vuelve de `ilike` se verifica entero (`_` y `%` son comodines)',
      bool(re.search(r"email\?\.toLowerCase\(\)\s*===\s*email", puente_codigo)))
check('y una fila que no está no revienta la ruta (`maybeSingle`, no `single`)',
      '.maybeSingle()' in puente_codigo and not re.search(r"\.single\(\)", puente_codigo))
check('el índice por `lower(email)` sigue existiendo para esa búsqueda',
      bool(re.search(r'practitioners\(lower\(email\)\)', sql_todo)))
check('y la columna `email` sigue en `practitioners`',
      bool(re.search(r'add column if not exists email text', sql_todo)))

# ── EL LADO DE TCD, PROBADO ──────────────────────────────────────────────
#
# Esta batería no puede ejecutar el handler de TCD: vive en el otro repo. Lo
# que sí puede es exigir que ESA prueba exista, porque es la única que
# ejecuta la ida y vuelta. Sin ella, el contrato se cuida de un solo lado —que
# es exactamente como estaba antes del turno 7.
# Si TCD no está clonado al lado, no hay nada que mirar y no se inventa un
# fallo: una lente que se pone roja por el estado del disco de quien la corre
# ensena a ignorar la batería.
_TCD = '../tcd1'
if os.path.isdir(_TCD):
    check('el lado de TCD tiene su propia prueba de la ida y vuelta',
          os.path.exists(_TCD + '/scripts/prueba-el-puente-de-las-dos-apps.ts'),
          'falta scripts/prueba-el-puente-de-las-dos-apps.ts en el repo de TCD')
else:
    print('  · TCD no está clonado al lado — su mitad del puente no se mira desde acá')


# ═══════════════════════════════════════════════════════════════════════════
print('\n════ 9 · LA BATERÍA SE PUEDE CORRER ════')
#
# Una batería que no está en el package.json se corre una vez y se olvida.
#
pkg = rd('package.json')
check('`npm run lint` compila', '"lint"' in pkg and 'tsc --noEmit' in pkg)
check('`npm run bateria` corre esto', '"bateria"' in pkg)


print('\n' + ('════ BATERÍA EN VERDE ════' if F == 0 else f'════ {F} FALLA(S) ════') + '\n')
sys.exit(0 if F == 0 else 1)
