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

def rdc(f):
    """El archivo, sin comentarios. Para medir un MECANISMO."""
    return solo_codigo(rd(f))

_SIN_COMENTARIOS: dict = {}

def cod(s):
    """El mismo texto YA LEÍDO, sin comentarios.

    Para medir un mecanismo sobre contenido que la lente ya tiene en una
    variable. Medido el 14 de noviembre a las 11:30: con la lista de pantallas
    protegidas vaciada y la de verdad dejada en un comentario encima, las 57
    lentes daban VERDE y las diez pantallas de cliente quedaban abiertas sin
    sesión. La regla es la misma que en TCD: una afirmación de PRESENCIA de
    algo con forma de código se mide sin comentarios; una de AUSENCIA se mide
    en el archivo crudo, que es más estricto.
    """
    if s not in _SIN_COMENTARIOS: _SIN_COMENTARIOS[s] = solo_codigo(s)
    return _SIN_COMENTARIOS[s]

def solo_sql(s):
    """El SQL sin comentarios: los de `--` y los de bloque.

    `solo_codigo` saca el `//` de TypeScript y no el `--` de SQL, así que las
    lentes de las migraciones —el `not null` del comprobante, el índice por
    `lower(email)`— se cumplían con una línea comentada. Medido el mismo día.
    """
    s = re.sub(r'/\*[\s\S]*?\*/', '', s)
    out = []
    for l in s.split('\n'):
        i, n, q = 0, len(l), None
        corte = len(l)
        while i < n:
            c = l[i]
            if q:
                if c == '\\': i += 2; continue
                if c == q: q = None
                i += 1; continue
            if c in '\'"': q = c; i += 1; continue
            if c == '-' and i + 1 < n and l[i+1] == '-': corte = i; break
            i += 1
        out.append(l[:corte])
    return '\n'.join(out)

def _sin_comentario_al_final(l):
    """Saca el `//` del final de UNA línea, sin tocar las barras que viven
    dentro de un texto, de una expresión regular o de una URL.

    El agujero que quedaba después del 13 de noviembre. `solo_codigo` sacaba
    el comentario de bloque y el de línea entera, pero no el del final, así
    que el nombre de la guarda dejado al final de la línea seguía contando
    como código. Medido el 14 de noviembre en la ruta del puente: con la
    comparación en tiempo constante cambiada por un `!==` pelado y
    `timingSafeEqual` y `.length !==` dejados en un comentario al final de esa
    misma línea, las 53 lentes daban VERDE. La misma forma apareció en TCD el
    mismo día, con la devolución del crédito.
    """
    i, n, q = 0, len(l), None
    while i < n:
        c = l[i]
        if q:                                  # dentro de un texto
            if c == '\\': i += 2; continue
            if c == q: q = None
            i += 1; continue
        if c == '\\': i += 2; continue         # /\/\/ de una regex
        if c in '\'"`': q = c; i += 1; continue
        if c == '/' and i + 1 < n and l[i+1] == '/':
            if i > 0 and l[i-1] == ':': i += 2; continue   # https://
            return l[:i]
        i += 1
    return l

def solo_codigo(s):
    """El archivo sin comentarios: los de bloque, los de línea entera y los
    del final de la línea.

    Una lente que marca en rojo al comentario que explica por qué algo se
    sacó, ensena a borrar la explicación. La misma decisión que en TCD.
    """
    s = re.sub(r'/\*[\s\S]*?\*/', '', s)
    s = re.sub(r'^\s*//.*$', '', s, flags=re.M)
    return '\n'.join(_sin_comentario_al_final(l) for l in s.split('\n'))

def es_de_navegador(s):
    """¿Este archivo se ejecuta en el navegador?

    La directiva de Next puede llevar comentarios y líneas en blanco arriba
    —es válido y es lo normal cuando alguien le pone una licencia o una nota—,
    así que mirar SOLO la primera línea es una lente ciega. Medido el 13 de
    noviembre: con un comentario encima, una pantalla de navegador que importa
    el service role pasaba en verde. Se mira el prólogo entero.
    """
    for linea in s.split('\n'):
        l = linea.strip()
        if not l or l.startswith('//') or l.startswith('/*') or l.startswith('*'):
            continue
        return l.startswith("'use client'") or l.startswith('"use client"')
    return False


def cuerpos_de_handler(codigo):
    """Cada handler exportado de una ruta, con su cuerpo y lo que llama.

    Pedir la guarda en el archivo entero deja pasar un handler sin guarda al
    lado de otro que la tiene. Y la guarda puede estar factorizada en una
    función local del mismo archivo —`mensajes` lo hace con su `auth()`, y
    está bien hecho—, así que se sigue una vuelta de llamadas locales.
    """
    locales = dict(re.findall(r'(?:async )?function (\w+)\s*\([^)]*\)\s*\{([\s\S]*?)\n\}', codigo))
    ps = [(m.group(1), m.start()) for m in
          re.finditer(r'export async function (GET|POST|PATCH|PUT|DELETE)', codigo)]
    for i, (h, s) in enumerate(ps):
        e = ps[i + 1][1] if i + 1 < len(ps) else len(codigo)
        cuerpo = codigo[s:e]
        visto = cuerpo
        for nombre, c in locales.items():
            if re.search(r'\b' + nombre + r'\s*\(', cuerpo):
                visto += '\n' + c
        yield h, cuerpo, visto


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
# Sin comentarios, y es el agujero que se midió el 14 de noviembre a las
# 11:30: con la lista vaciada —`([] as string[]).some(...)`— y la de verdad
# dejada en un comentario UNA LÍNEA ENCIMA, `re.search` encontraba primero la
# del comentario, daba las diez por protegidas, y las diez pantallas de
# cliente quedaban abiertas sin sesión. `tsc` limpio, `next build` limpio y
# las 57 lentes en verde. Lo que hay detrás de esas pantallas son los
# pacientes de un cliente.
mw_crudo = rd('src/lib/supabase/middleware.ts')
mw = cod(mw_crudo)
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
# El crudo se guarda para las afirmaciones de AUSENCIA —pedir que algo no
# esté NI en un comentario es más estricto—, y lo que TIENE que estar se mide
# sobre el SQL sin sus `--`: una línea comentada no crea una columna.
sql_crudo = '\n'.join(rd(f) for f in SQL)
sql_todo = solo_sql(sql_crudo)
tabla = re.search(r'create table if not exists public\.cobros \((.*?)\n\);', sql_todo, re.S)
check('la tabla `cobros` sigue declarada', bool(tabla))
if tabla:
    check('un cobro no puede existir sin su comprobante (`receipt_path not null`)',
          bool(re.search(r'receipt_path\s+text\s+not null', tabla.group(1))))
    check('y su monto es positivo, no cero', 'amount_usd > 0' in tabla.group(1))
check('nadie volvió nullable el comprobante en una migración posterior',
      not re.search(r'alter\s+column\s+receipt_path\s+drop\s+not\s+null', sql_crudo, re.I))

puente_crudo = rd('src/app/api/integrations/tcd/route.ts')
puente = cod(puente_crudo)
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
# Y una segunda cosa estaba desparejo acá mismo, medida el 13 de noviembre:
# esta lente leía el archivo CRUDO. El propio comentario de abajo ya explica
# que leer crudo da verde con la comparación rota; esta no lo aplicaba. Con la
# guarda sacada y el comentario que la nombra en su lugar, las diez rutas
# daban verde. Ahora se lee sin comentarios, handler por handler.
GUARDAS = ('auth.getUser', 'x-integration-key', 'GHL_WEBHOOK_SECRET')
sin_guarda, sin_corte = [], []
for f in RUTAS:
    for h, _cuerpo, visto in cuerpos_de_handler(solo_codigo(rd(f))):
        quien = f.replace('src/app/api/', '') + ' ' + h
        if not any(g in visto for g in GUARDAS):
            sin_guarda.append(quien)
        elif not re.search(r'status:\s*(401|403)', visto):
            sin_corte.append(quien)
_handlers = sum(1 for f in RUTAS for _ in cuerpos_de_handler(solo_codigo(rd(f))))
check(f'los {_handlers} handlers de las {len(RUTAS)} rutas piden algo antes de contestar',
      not sin_guarda, ', '.join(sin_guarda))
check('y el que pregunta, corta: contesta 401 o 403 cuando no pasa',
      not sin_corte, ', '.join(sin_corte))

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
# Lo que TIENE que estar se mide en el código; lo que NO tiene que estar, en
# el archivo crudo. Una clave filtrada dentro de un comentario está filtrada
# igual, así que esa última lente mira el archivo entero a propósito.
cripto = solo_codigo(rd('src/lib/crypto.ts'))
cripto_crudo = rd('src/lib/crypto.ts')
check('el cifrado del token sigue siendo AES-256-GCM', 'aes-256-gcm' in cripto)
check('y su clave vive solo en el entorno',
      'process.env.TOKEN_ENCRYPTION_KEY' in cripto)
check('la clave no está escrita en el repo',
      not re.search(r"TOKEN_ENCRYPTION_KEY\s*=\s*['\"][0-9a-fA-F]{32,}", cripto_crudo))

# Esta lente MEDÍA PARA NADIE desde el 9 de noviembre. Buscaba la columna
# `ghl_token`, y esa columna no existe en este repo: el token del cliente se
# guarda en `private_token` de `ghl_connections`. `ghl_token` aparecía en un
# solo lugar de todo MCD — en esta línea—. La lista salía vacía, `sin_cifrar`
# también, y el verde no significaba nada. Medido el 14 de noviembre: con el
# `encryptToken` sacado del `upsert` de la ruta de alta —el token del cliente
# guardado en claro en la base— la batería daba sus 53 en verde.
#
# Dos cambios, no uno: la columna de verdad, y una lente que exige que la
# lista tenga a alguien. Una lista vacía es la forma en que una lente se
# apaga sola sin avisar.
_ESCRIBE_TOKEN = re.compile(
    r"(?:upsert|insert|update)\(\s*\{[\s\S]{0,600}?private_token\s*:")
escriben_token = [f for f in TSX if _ESCRIBE_TOKEN.search(solo_codigo(rd(f)))]
check('la lente del token mira a alguien: alguien guarda el `private_token`',
      len(escriben_token) >= 2, f'{len(escriben_token)} archivo(s)',
      )
# Y se mide en el VALOR que se escribe, no en el archivo: el `import
# { encryptToken }` de arriba ya alcanzaba para dar verde con el token
# guardado en claro tres líneas más abajo. Sin comentarios, además: el nombre
# del cifrado dejado en un comentario no cifra nada. Las dos cosas medidas el
# 14 de noviembre, con la llamada sacada del `upsert`.
def valores_de(codigo, clave):
    """Cada expresión que se le asigna a `clave:` en un objeto, entera.

    Se sigue hasta la coma que cierra ESA entrada, contando paréntesis,
    llaves y corchetes y sin mirar dentro de un texto, así que un valor de
    tres líneas con un ternario adentro vuelve completo.
    """
    for m in re.finditer(r'\b' + clave + r'\s*:', codigo):
        i, d, q, ini = m.end(), 0, None, m.end()
        while i < len(codigo):
            c = codigo[i]
            if q:
                if c == '\\': i += 2; continue
                if c == q: q = None
                i += 1; continue
            if c in '\'"`': q = c
            elif c in '([{': d += 1
            elif c in ')]}':
                if d == 0: break
                d -= 1
            elif c == ',' and d == 0: break
            i += 1
        yield codigo[ini:i].strip()

sin_cifrar = []
for f in escriben_token:
    for _v in valores_de(solo_codigo(rd(f)), 'private_token'):
        if _v in ('null', 'undefined') or 'encryptToken(' in _v: continue
        sin_cifrar.append(f'{f}: {_v[:40]}')
check('todo el que guarda un token lo cifra', not sin_cifrar, '; '.join(sin_cifrar))

# El service role en el navegador sería la base entera abierta.
en_cliente = []
for f in TSX:
    _t_crudo = rd(f)
    if es_de_navegador(_t_crudo):
        if 'createAdminClient' in cod(_t_crudo) or 'SERVICE_ROLE' in cod(_t_crudo):
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
# Sin comentarios: medido el 14 de noviembre a las 11:30, con el `while` de
# `getContacts` cambiado por una sola vuelta y el nombre dejado al final de la
# línea, las tres lentes de contactos daban verde y las listas volvían a
# truncarse en 100 —«faltan pacientes», en silencio, que es el defecto que
# este bloque existe para cuidar—.
cliente = rdc('src/lib/ghl/client.ts')
for nombre, fn in (('contactos', 'getContacts'), ('oportunidades', 'getOpportunities')):
    cuerpo = re.search(rf'export async function {fn}[\s\S]*?\n\}}', cliente)
    check(f'{nombre}: la función sigue existiendo', bool(cuerpo))
    if cuerpo:
        check(f'{nombre}: pide página tras página, no las primeras cien',
              'while' in cuerpo.group(0))
        check(f'{nombre}: y tiene un techo, para no colgarse pidiendo para siempre',
              'MAX_ITEMS' in cuerpo.group(0))
check('el techo está declarado una sola vez', cliente.count('const MAX_ITEMS') == 1)
# Esta lente medía un COMENTARIO. Pedía la palabra «retry» en el archivo, y
# la única que había estaba en `// Retry en rate-limit o error de servidor`:
# en el código no aparece —el mecanismo se llama `attempt`—. Encontrado el 14
# de noviembre a las 11:30, al pasar el archivo a `rdc()`. Ahora se mide el
# mecanismo: que el 429 y el 5xx vuelvan a llamar, y que la vuelta tenga tope
# —sin tope, un GHL caído cuelga la pantalla del cliente para siempre—.
_fetch = re.search(r'async function ghlFetch\([\s\S]*?\n\}', cliente)
check('la llamada a GHL sigue teniendo un solo lugar donde reintentar', bool(_fetch))
if _fetch:
    _f = _fetch.group(0)
    # Y se mide DENTRO de la rama del 429, no en la función: abajo hay otro
    # `return ghlFetch(...)` —el del timeout— y con el del 429 comentado la
    # lente encontraba ése y daba verde. Medido el 14 de noviembre a las
    # 11:30, probando esta misma lente contra su propio fallo.
    _rama = re.search(r'if\s*\([^)]*429[\s\S]*?\n(\s*)\}', _f)
    check('y reintenta cuando GHL responde 429 o 5xx',
          bool(_rama) and bool(re.search(r'status\s*>=\s*5\d\d', _rama.group(0)))
          and 'ghlFetch(' in _rama.group(0),
          'la rama del 429 ya no vuelve a llamar')
    # El tope también se mide en la CONDICIÓN de esa rama: en la función hay
    # otro `attempt < 2` —el del timeout—, así que mirar la función entera
    # daba verde con el tope del 429 sacado. Probado igual que el de arriba.
    check('y el reintento tiene tope, para no colgar la pantalla del cliente',
          bool(_rama) and bool(re.search(r'attempt\s*<\s*\d',
                                         _rama.group(0).split('{', 1)[0])),
          'sin tope, un GHL caído reintenta para siempre')


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
    t_crudo = rd(f)          # crudo a propósito: una clave en un comentario está filtrada igual
    for patron, que in SOSPECHOSOS:
        if re.search(patron, t_crudo):   # crudo a propósito: la ausencia se mide entera
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
# `puente` ya viene sin comentarios desde el bloque 3; este nombre se queda
# porque las tres lentes de abajo lo dicen en su explicación.
puente_codigo = puente

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

# ── Y la lente que cuida a las otras: el limpiador de comentarios ─────────
#
# El 13 de noviembre dos lentes daban verde con la guarda sacada porque leían
# el archivo crudo. El 14 se midió lo que quedaba abierto después de eso: el
# comentario del FINAL de la línea. Con la comparación del puente cambiada por
# un `!==` pelado y `timingSafeEqual` dejado al final de esa misma línea, las
# 53 lentes daban verde. Si `solo_codigo` deja de sacar ese comentario, todo
# este archivo vuelve a ser decorativo, así que se prueba acá.
_prueba_sc = """const url = 'https://x.dev//y';
const re = /^https?:\\/\\//i;
if (key !== expected) { // timingSafeEqual(Buffer.from(key)) y .length !==
// encryptToken(algo)
const vivo = encryptToken(token);"""
_limpio_sc = solo_codigo(_prueba_sc)
check('solo_codigo saca el comentario del final de la línea',
      'timingSafeEqual' not in _limpio_sc and '.length !==' not in _limpio_sc
      and 'encryptToken(algo)' not in _limpio_sc)
check('y no se lleva la URL, la regex ni el código de al lado',
      'https://x.dev//y' in _limpio_sc and 'https?:' in _limpio_sc
      and 'encryptToken(token)' in _limpio_sc,
      'una barra dentro de un texto o de una regex no es un comentario')

# ── LA REGLA, QUE DEJÓ DE SER UNA LISTA ──────────────────────────────────
#
# Medido el 14 de noviembre a las 11:30: la batería entera —57 lentes, `tsc`
# limpio, `next build` limpio— daba VERDE con tres defectos puestos, cada uno
# con su nombre dejado en un comentario:
#
#   · la lista de pantallas protegidas vaciada  → las diez pantallas de
#     cliente abiertas sin sesión, con los pacientes detrás,
#   · el `while` de `getContacts` cambiado por una sola vuelta → las listas
#     truncadas en 100 otra vez, en silencio,
#   · `total_usd` sacado de la respuesta del puente → el cinturón de TCD
#     calculado sobre un `undefined`.
#
# Ninguna de las tres tenía la forma que la lente vieja miraba (`'nombre' in
# rd(…)`): las tres medían sobre una VARIABLE leída cruda más arriba. Así que
# la regla pasó a ser del lado de la variable, y se declara en el nombre:
#
#   1 · lo que se lee crudo de un archivo fuente se llama `*_crudo`,
#   2 · y sobre un `*_crudo` solo se afirma AUSENCIA. Toda PRESENCIA se mide
#       sobre el código: `rdc(archivo)`, `cod(texto)` o `solo_sql(sql)`.
#
# Pedir que algo NO esté ni en un comentario es más estricto, no menos, así
# que ésa es la única que puede leer crudo.
_FUENTE_SC = ('.ts', '.tsx', '.js', '.jsx', '.sql')
_LIMPIADORES_SC = ('rdc(', 'cod(', 'solo_codigo(', 'solo_sql(')
_ASIG_SC = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*\brd\(.*)$')
_LIT_SC = re.compile(r"""rd\(\s*['"]([^'"\n]+)['"]""")
_yo_sc = rd('auditoria.py').split('\n')          # crudo a propósito: es Python, no fuente de la app
_sin_declarar, _crudas_sc = [], []
for _n_sc, _l_sc in enumerate(_yo_sc, 1):
    if _l_sc.lstrip().startswith('#'): continue
    _m_sc = _ASIG_SC.match(_l_sc)
    if not _m_sc: continue
    _nombre, _der = _m_sc.group(1), _m_sc.group(2)
    if any(c in _der for c in _LIMPIADORES_SC): continue   # ya viene sin comentarios
    _lit = _LIT_SC.search(_der)
    if _lit and not _lit.group(1).endswith(_FUENTE_SC): continue   # package.json, .gitignore
    if not _nombre.endswith('_crudo'):
        _sin_declarar.append(f'línea {_n_sc}: {_nombre}')
check('todo lo que se lee crudo de un archivo fuente se llama `*_crudo`',
      not _sin_declarar, '; '.join(_sin_declarar))

# Y sobre un `*_crudo`, solo ausencias. Se miran las tres formas con las que
# una presencia se escribe: el `in`, el `re.search` y el `.count`.
_PRES_IN_SC = re.compile(r'(not\s+)?\bin\s+([A-Za-z_][A-Za-z0-9_]*_crudo)\b')
_PRES_RE_SC = re.compile(r're\.(?:search|findall|finditer|match)\([^\n]*?,\s*([A-Za-z_][A-Za-z0-9_]*_crudo)\b')
_PRES_CT_SC = re.compile(r'\b([A-Za-z_][A-Za-z0-9_]*_crudo)\.(?:count|index|find)\(')
for _n_sc, _l_sc in enumerate(_yo_sc, 1):
    _d_sc = _l_sc.lstrip()
    if _d_sc.startswith('#') or _d_sc.startswith('_PRES_') or _d_sc.startswith('_ASIG_'): continue
    if 'crudo a propósito' in _l_sc: continue        # declarado en su línea, y se lee
    for _m_sc in _PRES_IN_SC.finditer(_l_sc):
        if not _m_sc.group(1):
            _crudas_sc.append(f'línea {_n_sc}: presencia sobre {_m_sc.group(2)}')
    for _rx_sc in (_PRES_RE_SC, _PRES_CT_SC):
        for _m_sc in _rx_sc.finditer(_l_sc):
            if 'not re.' in _l_sc or 'not ' + _m_sc.group(1) in _l_sc: continue
            _crudas_sc.append(f'línea {_n_sc}: presencia sobre {_m_sc.group(1)}')
check('ninguna lente afirma PRESENCIA sobre un archivo crudo',
      not _crudas_sc, '; '.join(_crudas_sc))

# Y el limpiador del SQL, que es nuevo: el `--` de una migración comentada no
# crea una columna.
_PRUEBA_SQL = """create table cobros (
  receipt_path text not null,  -- amount_usd > 0
-- create index on practitioners(lower(email));
  nota text default '-- no es comentario'
);"""
_limpio_sql = solo_sql(_PRUEBA_SQL)
check('solo_sql saca el comentario de `--`, al final y de línea entera',
      'amount_usd > 0' not in _limpio_sql and 'lower(email)' not in _limpio_sql)
check('y no se lleva los guiones que viven dentro de un texto',
      "'-- no es comentario'" in _limpio_sql and 'receipt_path text not null' in _limpio_sql)



print('\n' + ('════ BATERÍA EN VERDE ════' if F == 0 else f'════ {F} FALLA(S) ════') + '\n')
sys.exit(0 if F == 0 else 1)
