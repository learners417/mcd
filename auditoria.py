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
import re, os, sys, glob, subprocess, ast

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
    """El archivo, sin comentarios, EN EL LENGUAJE DE ESE ARCHIVO.

    Hasta el 15 de noviembre esto era `solo_codigo(rd(f))` a secas: el `//`
    de TypeScript y nada más, para cualquier archivo. `solo_sql` y
    `solo_almohadilla` existían al lado, pero había que acordarse de
    llamarlos a mano. Una lente nueva sobre una migración o sobre
    `globals.css` entraba por acá y nacía ciega sin que nadie lo notara, que
    es exactamente la forma que TCD encontró viva ese mismo día en su
    `index.html` y su `index.css`. Ahora la extensión elige el limpiador, y
    una lente de abajo no deja entrar ningún lenguaje cuyo comentario esta
    batería no sepa escribir.
    """
    return solo_del_lenguaje(rd(f), f)

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

def solo_almohadilla(s):
    """El archivo sin los comentarios de `#`, al final y de línea entera.

    `.gitignore` también lleva comentarios, y la lente que lo mira existe
    para una sola cosa: que `.env.local` —el entorno con las claves— no
    entre al repo. Medido el 15 de noviembre: con `# .env.local` en lugar de
    `.env.local`, la batería entera dio VERDE y «el entorno con las claves
    no entra al repo» entre ellas. `git ls-files` solo lo caza DESPUÉS, con
    el archivo ya subido, que es tarde. La misma forma que TCD cerró el
    mismo día en .sql, .py y .sh.
    """
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
            if c == '#': corte = i; break
            i += 1
        out.append(l[:corte])
    return '\n'.join(out)


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

def solo_bloque(s):
    """El `.css`: ahí el comentario es SOLO `/* */`.

    No se puede reusar `solo_sql` —se comería `--surface: var(--bg-card)`,
    que es una propiedad y no un comentario— ni `solo_codigo`, que en CSS
    cortaría la barra de una URL dentro de un `url()`.
    """
    return re.sub(r'/\*[\s\S]*?\*/', '', s)


def solo_xml(s):
    """El `.html` y el `.md`: ahí el comentario es `<!-- -->`, y es el único
    lugar donde un mecanismo puede esconderse sin que se vea al abrir el
    archivo."""
    return re.sub(r'<!--[\s\S]*?-->', '', s)


# El comentario no se escribe igual en todos los lenguajes, así que la
# extensión elige el limpiador. Un lenguaje que no esté acá no entra: la
# lente del final lo exige por el ÁRBOL.
_MARCAS = {
    '.ts': 'codigo', '.tsx': 'codigo', '.js': 'codigo', '.jsx': 'codigo',
    '.mjs': 'codigo', '.cjs': 'codigo',
    '.sql': 'sql',
    '.gitignore': 'almohadilla', '.sh': 'almohadilla', '.bash': 'almohadilla',
    '.py': 'almohadilla', '.yml': 'almohadilla', '.yaml': 'almohadilla',
    '.css': 'bloque', '.html': 'xml', '.md': 'xml',
    '.json': 'nada', '.txt': 'nada',
}


def _ext(archivo):
    _i = archivo.rfind('.')
    return archivo[_i:].lower() if _i > archivo.rfind('/') else ''


def solo_del_lenguaje(s, archivo=''):
    """El texto sin los comentarios DE SU LENGUAJE. Sin nombre de archivo se
    asume TypeScript, que es lo que lee casi toda la batería."""
    _q = _MARCAS.get(_ext(archivo), 'codigo')
    return {'codigo': solo_codigo, 'sql': solo_sql,
            'almohadilla': solo_almohadilla, 'bloque': solo_bloque,
            'xml': solo_xml, 'nada': lambda _x: _x}[_q](s)


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
    ign_crudo = rd('.gitignore')
    ign = solo_almohadilla(ign_crudo)
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
# ── Y LO QUE TCD LEE DE VERDAD, NO LO QUE ESTA LISTA DICE ────────────────
#
# LO QUE SE MIDIÓ (16 de noviembre de 2026): el `CONTRATO` de arriba es una
# LISTA, escrita a mano acá. Lo que TCD lee es otra copia, escrita a mano en
# el otro repo (`data?.…` en `api/mcd-bridge.ts`, y el MCD FALSO de
# `prueba-el-puente-de-las-dos-apps.ts`). Nadie ataba las tres.
#
# Medido poniendo el defecto: se renombró `primer_cobro` a
# `fecha_primer_cobro` en la respuesta de acá y se arregló esta lista —que es
# el movimiento natural de quien renombra el campo—. **Las 74 lentes de acá
# en verde, `tsc` limpio, `next build` limpio, y las 15 del puente en TCD
# también en verde.** En producción, el puente de TCD leería `undefined` y
# contestaría `cobro_verificado: false` para TODO cliente que cobró: el
# Cinturón Rojo no llega nunca y el candado del día 31 no se abre nunca, en
# silencio y para siempre.
#
# Esta lista no puede ver eso: el nombre nuevo entra en ella y queda
# consistente consigo misma. Lo único que lo ve es comparar con EL TEXTO del
# otro repo. Así que acá se exige lo contrario de lo de arriba: no que los
# cinco nombres estén, sino que **nada de lo que TCD lee falte** de lo que
# esta ruta escribe de verdad.
#
# El renombre se hace editando MCD, así que esta mitad —la que corre cuando
# se está trabajando acá— es la que lo caza en el momento.


def _claves_del_objeto(_t, _i):
    """Las claves de primer nivel del objeto literal que ABRE en `_t[_i]`.

    A mano y no con una regex porque el valor de una clave trae comas,
    paréntesis y llaves (`lista.reduce((s, c) => …, 0)`), y porque las de un
    `type` se separan con `;` y llevan `?`.
    """
    if _i >= len(_t) or _t[_i] != '{': return None
    _prof, _j, _q, _partes, _ini = 0, _i, None, [], _i + 1
    while _j < len(_t):
        _c = _t[_j]
        if _q:
            if _c == '\\': _j += 2; continue
            if _c == _q: _q = None
            _j += 1; continue
        if _c in '\'"`': _q = _c; _j += 1; continue
        if _c in '{[(': _prof += 1
        elif _c in '}])':
            _prof -= 1
            if _prof == 0: _partes.append(_t[_ini:_j]); break
        elif _c in ',;' and _prof == 1: _partes.append(_t[_ini:_j]); _ini = _j + 1
        _j += 1
    _out = set()
    for _p in _partes:
        _m = re.match(r'^([A-Za-z_$][\w$]*)\s*\??\s*(?::|$)', _p.strip())
        if _m: _out.add(_m.group(1))
    return _out


def _objeto_mayor(_t, _abridor, _minimo=3):
    """El objeto más grande de los que siguen a `_abridor`: la respuesta BUENA.

    Los otros `NextResponse.json({…})` de la ruta son `{ error }`, de una
    sola clave.
    """
    _objs = []
    for _m in re.finditer(re.escape(_abridor), _t):
        _k = _m.end()
        while _k < len(_t) and _t[_k] in ' \n\t': _k += 1
        _cl = _claves_del_objeto(_t, _k)
        if _cl and len(_cl) >= _minimo: _objs.append(_cl)
    return max(_objs, key=len) if _objs else None


# `puente` ya viene sin comentarios: un campo nombrado en un comentario no
# viaja en el JSON.
_emiteM = _objeto_mayor(puente, 'NextResponse.json(')
check('se pudo leer qué campos escribe esta ruta de verdad', bool(_emiteM),
      'no se encontró el objeto de la respuesta buena en el puente')
if _emiteM:
    _faltanLista = [c for c in CONTRATO if c not in _emiteM]
    check('y los cinco de la lista están entre los que escribe, no solo en el texto',
          not _faltanLista, 'faltan: ' + ', '.join(_faltanLista))


_TCD = os.environ.get('TCD_REPO') or '../tcd1'
if os.path.isdir(_TCD):
    check('el lado de TCD tiene su propia prueba de la ida y vuelta',
          os.path.exists(_TCD + '/scripts/prueba-el-puente-de-las-dos-apps.ts'),
          'falta scripts/prueba-el-puente-de-las-dos-apps.ts en el repo de TCD')

    # Y acá está lo que esa prueba NO puede ver: su MCD falso es una copia a
    # mano de esta respuesta, congelada en el otro repo. Si acá se renombra un
    # campo, el falso sigue mandando el viejo, el handler de TCD sigue
    # leyéndolo, y las 15 lentes de allá siguen verdes contra un MCD que ya
    # no existe. Lo único que lo ve es comparar los dos textos.
    _pteT = cod(rd(_TCD + '/api/mcd-bridge.ts'))
    _pruT = cod(rd(_TCD + '/scripts/prueba-el-puente-de-las-dos-apps.ts'))
    _leeT = set(re.findall(r'\bdata\s*\??\.\s*([A-Za-z_$][\w$]*)', _pteT))
    _mtipoT = re.search(r'type RespuestaDeMCD\s*=\s*', _pteT)
    _tipoT = (_claves_del_objeto(_pteT, _mtipoT.end()) or set()) if _mtipoT else set()
    _fingeT = _objeto_mayor(_pruT, 'json: async () => (') or set()

    # Una lente que no encontró qué comparar está ciega, no verde.
    check('se pudo leer qué campos lee TCD del puente', bool(_leeT) and bool(_fingeT),
          f'lee={sorted(_leeT)} finge={sorted(_fingeT)}')

    if _emiteM and _leeT:
        _huerfanos = sorted((_leeT | _tipoT) - _emiteM)
        check('esta ruta escribe todos los campos que TCD lee del puente',
              not _huerfanos,
              ', '.join(_huerfanos) + ' — TCD los lee y acá no se escriben: '
              'el puente contesta «todavía no cobró» para el que SÍ cobró')
        _viejos = sorted(_fingeT - _emiteM)
        check('y el MCD falso de la prueba de TCD no finge un campo que acá ya no existe',
              not _viejos,
              ', '.join(_viejos) + ' — las 15 lentes de TCD pasan contra un MCD que no existe')
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
# Y las pruebas que se ejecutan, a mano y sin la batería entera, para cuando
# se está tocando `normalize.ts` o `crypto.ts` y se quiere la vuelta en dos
# segundos. Si no están acá, nadie se acuerda de cómo se corren.
check('`npm run pruebas` corre las pruebas sueltas',
      '"pruebas"' in pkg and 'experimental-transform-types' in pkg)

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
_FUENTE_SC = ('.ts', '.tsx', '.js', '.jsx', '.sql', '.gitignore')
_LIMPIADORES_SC = ('rdc(', 'cod(', 'solo_codigo(', 'solo_sql(',
                   'solo_almohadilla(')
# Y esto se mide con el ÁRBOL, no con el texto. Medido el 15 de noviembre:
# la versión de texto —`^nombre = ….rd(…)`— se come una CADENA que apenas
# contenga `rd(` (la fixture de la lente de la puerta, de abajo, la marcaba
# como una lectura) y no ve tres formas de recibir un archivo crudo que no
# son `nombre = …`: la tupla (`_a, _b = rd(x), rd(y)`), el casillero
# (`_d['k'] = rd(x)`) y el atributo. El árbol ve las llamadas de verdad y
# todos los nombres que reciben, y no ve ninguna cadena.
_LIMPIADORES_AST = ('rdc', 'cod', 'solo_codigo', 'solo_sql', 'solo_almohadilla',
                    'solo_bloque', 'solo_xml', 'solo_del_lenguaje')


def _crudas_de(fuente):
    """Cada nombre que recibe un archivo FUENTE leído crudo, con su línea."""
    _arb = ast.parse(fuente)
    _padre = {}
    for _n in ast.walk(_arb):
        for _h in ast.iter_child_nodes(_n): _padre[_h] = _n
    _out = []
    for _n in ast.walk(_arb):
        if not isinstance(_n, (ast.Assign, ast.AnnAssign)) or _n.value is None:
            continue
        _hay_crudo = False
        for _c in ast.walk(_n.value):
            if not (isinstance(_c, ast.Call) and isinstance(_c.func, ast.Name)
                    and _c.func.id == 'rd'):
                continue
            if (_c.args and isinstance(_c.args[0], ast.Constant)
                    and not str(_c.args[0].value).endswith(_FUENTE_SC)):
                continue                      # package.json y los generados
            _p, _limpio = _padre.get(_c), False
            while _p is not None and _p is not _n:
                if (isinstance(_p, ast.Call) and isinstance(_p.func, ast.Name)
                        and _p.func.id in _LIMPIADORES_AST):
                    _limpio = True; break
                _p = _padre.get(_p)
            if not _limpio: _hay_crudo = True
        if not _hay_crudo: continue
        _destinos = _n.targets if isinstance(_n, ast.Assign) else [_n.target]
        for _t in _destinos:
            for _nm in ast.walk(_t):
                if isinstance(_nm, ast.Name):
                    _out.append((_nm.id, _n.lineno))
    return _out


_yo_sc = rd('auditoria.py').split('\n')          # crudo a propósito: es Python, no fuente de la app
_crudas_sc = []
_sin_declarar = [f'línea {_ln}: {_nm}'
                 for _nm, _ln in _crudas_de('\n'.join(_yo_sc))
                 if not _nm.endswith('_crudo')]
check('todo lo que se lee crudo de un archivo fuente se llama `*_crudo`',
      not _sin_declarar, '; '.join(_sin_declarar))

# Y probada contra su propio fallo, con las formas que la de texto no veía.
_VIEJA_ASIG = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*\brd\(.*)$')
_FIX_ROJAS = [
    "_a, _b = rd('src/app/page.tsx'), rd('src/lib/x.ts')",   # la tupla
    "_d = {}\n_d['k'] = rd('src/app/page.tsx')",             # el casillero
    "_z = rd('src/app/page.tsx')",                           # la de siempre
]
_FIX_VERDES = [
    "_t = solo_codigo(rd('src/app/page.tsx'))",              # ya viene limpio
    "_u = rdc('src/app/page.tsx')",
    "_l = [f for f in TSX if 'x' in solo_codigo(rd(f))]",    # envuelto, en comprensión
    "_p = rd('package.json')",                               # no es un archivo fuente
    "_s = \"def rd(f):\\n    return open(f).read()\"",         # una CADENA, no una lectura
    "_q_crudo = rd('src/app/page.tsx')",                     # declarado
]
_no_rojas = [_f for _f in _FIX_ROJAS
             if not [1 for _nm, _ in _crudas_de(_f) if not _nm.endswith('_crudo')]]
_mal_rojas = [_f for _f in _FIX_VERDES
              if [1 for _nm, _ in _crudas_de(_f) if not _nm.endswith('_crudo')]]
check(f'la lente del nombre se pone roja con las {len(_FIX_ROJAS)} formas de recibir un crudo',
      not _no_rojas, '; '.join(_no_rojas))
check('y deja pasar lo ya limpio, lo que no es fuente y la cadena que dice `rd(`',
      not _mal_rojas, '; '.join(_mal_rojas))
check('la de texto era ciega con la tupla y con la cadena (por eso se cambió)',
      not _VIEJA_ASIG.match(_FIX_ROJAS[0])
      and bool(_VIEJA_ASIG.match(_FIX_VERDES[4])),
      'si la vieja ya las veía, este cambio no hacía falta')

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

# Y el limpiador del `#`, probado contra su propio fallo: con `.env.local`
# comentado, la lente de las claves tiene que ponerse ROJA.
_PRUEBA_ALM = """# dependencias
node_modules/
# .env.local
.vercel
COLOR = '#080808'  # el fondo"""
_limpio_alm = solo_almohadilla(_PRUEBA_ALM)
check('solo_almohadilla saca el comentario de `#`, al final y de línea entera',
      '.env.local' not in _limpio_alm and 'el fondo' not in _limpio_alm,
      'con `# .env.local` la batería daba verde y el entorno con las claves '
      'quedaba sin regla')
check('y no se lleva la ruta viva ni el color que vive en un texto',
      'node_modules/' in _limpio_alm and '.vercel' in _limpio_alm
      and "'#080808'" in _limpio_alm)


# ── Y las dos que cuidan la puerta y los lenguajes ───────────────────────
#
# Lo de arriba sirve si TODO entra por la misma puerta. Medido en TCD el 15
# de noviembre: tres de sus lentes leían `index.html` y `src/index.css` con
# `open(...).read()`, por donde no pasa ni el limpiador ni la lente de la
# presencia, y con el mecanismo comentado —`<!-- -->` y `/* */`— las tres
# daban VERDE. Acá no pasa hoy, y estas dos lentes son para que siga así.
# Se miden con el ÁRBOL, que no se come un comentario ni una cadena.


def _puertas_de(fuente):
    """Cada `open(` que no viva adentro de `rd()`."""
    _a = ast.parse(fuente)
    _rd = next((_n for _n in ast.walk(_a)
                if isinstance(_n, ast.FunctionDef) and _n.name == 'rd'), None)
    _dentro = (set(range(_rd.lineno, (_rd.end_lineno or _rd.lineno) + 1))
               if _rd else set())
    return [_n.lineno for _n in ast.walk(_a)
            if isinstance(_n, ast.Call) and isinstance(_n.func, ast.Name)
            and _n.func.id == 'open' and _n.lineno not in _dentro]


def _leidas_de(fuente):
    """Las extensiones que la batería lee de verdad, por el árbol."""
    _ext_leidas = set()
    for _n in ast.walk(ast.parse(fuente)):
        if (isinstance(_n, ast.Call) and isinstance(_n.func, ast.Name)
                and _n.func.id in ('rd', 'rdc') and _n.args
                and isinstance(_n.args[0], ast.Constant)):
            _v = str(_n.args[0].value)
            if '.' in _v.split('/')[-1]: _ext_leidas.add(_ext(_v))
    return _ext_leidas


_yo_fuente = rd('auditoria.py')          # crudo a propósito: es Python, no fuente de la app
_puertas = _puertas_de(_yo_fuente)
check('ningún archivo se lee con `open()`: la puerta es `rd()`',
      not _puertas,
      f'líneas {_puertas} — por ahí no pasa ni el limpiador ni la lente de la presencia')
_sin_marca = sorted(_e for _e in _leidas_de(_yo_fuente) if _e not in _MARCAS)
check('la batería no lee ningún lenguaje cuyo comentario no sepa escribir',
      not _sin_marca, f'{_sin_marca} — declararlo en _MARCAS con su limpiador')

# Y las dos, probadas contra su propio fallo: con el defecto puesto tienen
# que ponerse ROJAS.
_FALSA_PUERTA = ("def rd(f):\n    return open(f).read()\n"
                 "_x = open('src/app/page.tsx').read()\n")
check('la lente de la puerta se pone roja con un `open()` afuera de `rd()`',
      _puertas_de(_FALSA_PUERTA) == [3] and not _puertas_de(
          "def rd(f):\n    return open(f).read()\n_y = rd('src/app/page.tsx')\n"))
check('y la de los lenguajes, con uno que no sabe comentar',
      '.ini' in _leidas_de("_z = rd('config.ini')\n")
      and '.ini' not in _MARCAS)

# Y que la extensión elija de verdad el limpiador, porque usar el de al lado
# rompe distinto: `solo_sql` sobre un `.css` se come `--surface`, que es una
# propiedad; `solo_codigo` sobre un `.sql` no ve el `--`.
_CSS = "[data-theme=\"light\"] {\n  --surface: var(--bg-card);\n  /* --color-ink: #EAE4D9; */\n}"
_HTML = '<html data-theme="light">\n<!-- data-theme="dark" lo decide el cliente -->'
_SQLM = "alter table pagos enable row level security;\n-- create index on pagos(lower(email));"
_IGN = "node_modules/\n# .env.local\n.vercel"
check('el `.css` pierde el `/* */` y NO la propiedad de dos guiones',
      '--color-ink' not in solo_del_lenguaje(_CSS, 'src/app/globals.css')
      and '--surface: var(--bg-card)' in solo_del_lenguaje(_CSS, 'src/app/globals.css'),
      'con el limpiador del SQL, `--surface` se iba con el comentario')
check('el `.html` pierde el `<!-- -->` y no el atributo vivo',
      'data-theme="dark"' not in solo_del_lenguaje(_HTML, 'mockup/mcd-mockup.html')
      and 'data-theme="light"' in solo_del_lenguaje(_HTML, 'mockup/mcd-mockup.html'))
check('el `.sql` y el `.gitignore` siguen cada uno con su marca',
      'lower(email)' not in solo_del_lenguaje(_SQLM, 'supabase/x.sql')
      and 'enable row level security' in solo_del_lenguaje(_SQLM, 'supabase/x.sql')
      and '.env.local' not in solo_del_lenguaje(_IGN, '.gitignore')
      and 'node_modules/' in solo_del_lenguaje(_IGN, '.gitignore'))
check('y sin nombre de archivo sigue siendo TypeScript',
      'encryptToken' not in solo_del_lenguaje('// encryptToken(algo)\nconst a = 1;'))



# ═══════════════════════════════════════════════════════════════════════════
print('\n════ 10 · EL CÓDIGO SE EJECUTA, NO SOLO SE LEE ════')
#
# QUÉ PASARÍA SIN ÉL: la batería lee texto. Los nueve bloques de arriba miran
# el código escrito —que una cadena esté, que una función nombre `startAfterId`,
# que `aes-256-gcm` aparezca— y eso alcanza para cuidar la FORMA. No alcanza
# para cuidar la CUENTA.
#
# MEDIDO EL 16 DE NOVIEMBRE, y por eso existe este bloque: diez defectos
# puestos a propósito en los archivos de verdad, uno por vez, con las 74
# lentes corriendo contra cada uno. OCHO NO LOS VIO NADIE:
#
#   · la etiqueta del GCM leída un byte corta → ningún token guardado se
#     vuelve a poder leer: se le cae el WhatsApp al cliente,
#   · el IV fijo en doce ceros → nonce repetido en AES-GCM: el PIT se puede
#     despejar y falsificar,
#   · el descifrado devolviendo lo guardado sin descifrar → GHL recibe el
#     texto cifrado como token y contesta 401 a todos,
#   · `page.length < 100` cambiado por `<= 100` → corta SIEMPRE en la primera
#     página: el cliente con 300 contactos ve 100, en silencio, que es
#     textualmente lo que el bloque 6 dice que existe para evitar,
#   · la bandeja marcando cero sin leer siempre → la doctora no ve que la
#     esperan y deja de contestar,
#   · toda venta abierta contando como paciente → el tablero miente,
#   · el que no vino contando como que vino → la tasa de asistencia infla,
#   · el hilo anidado de GHL sin desanidar → la conversación se dibuja vacía.
#
# Los dos que SÍ se vieron eran de texto: el `429` borrado de la condición del
# reintento y un segundo `const MAX_ITEMS`. O sea: la batería veía las letras
# y no la cuenta. Estas pruebas ejecutan la cuenta.
#
# Corren con el TypeScript que Node 22 entiende solo (`--experimental-transform-types`),
# a propósito: MCD no gana ninguna dependencia nueva por tener pruebas.
#
_PRUEBAS = sorted(glob.glob('scripts/prueba-*.ts'))
check('hay pruebas que se ejecutan', len(_PRUEBAS) >= 3,
      f'solo {len(_PRUEBAS)} en scripts/prueba-*.ts')

for _p in _PRUEBAS:
    _r = subprocess.run(['node', '--experimental-transform-types', _p],
                        capture_output=True, text=True)
    _salida = (_r.stdout or '') + (_r.stderr or '')
    _rojas = [l.strip() for l in _salida.splitlines() if '✗' in l]
    check(f'{os.path.basename(_p)} pasa', _r.returncode == 0,
          '; '.join(_rojas)[:400] or _salida.strip().splitlines()[-1:] and _salida.strip().splitlines()[-1][:300])

# ── Y LA LENTE QUE CUIDA A ESTAS PRUEBAS ──────────────────────────────────
#
# El bloque juzga cada prueba SOLO por su código de salida, igual que TCD.
# Y TCD encontró el agujero de eso el 16 de noviembre a las 07:25: una de sus
# 133 pruebas —`prueba-cadena.ts`— imprimía `✗` por escenario y terminaba en
# 0, así que cinco de sus seis escenarios fallaban y la batería daba verde.
# Acá se exige la forma que impide eso: contar fallas y salir con 1.
# ── EL ARNÉS: ¿Y ESTAS PRUEBAS, VEN EL DEFECTO? ───────────────────────────
#
# `scripts/probar-que-la-bateria-ve-el-defecto.py` pone los diez defectos de
# arriba sobre una copia del repo y exige que la lente NOMBRADA para cada uno
# se ponga roja. Si alguien ablanda una de estas pruebas, acá se entera.
# No corre cuando es el propio arnés el que está corriendo esta batería sobre
# su copia: si no, se llamaría a sí mismo para siempre.
if os.environ.get('MCD_SIN_ARNES') != '1':
    _arnes = subprocess.run([sys.executable, 'scripts/probar-que-la-bateria-ve-el-defecto.py'],
                            capture_output=True, text=True)
    _mal = [l.strip() for l in (_arnes.stdout + _arnes.stderr).splitlines() if '✗' in l]
    check('cada defecto conocido pone roja a la lente que lo nombra',
          _arnes.returncode == 0, '; '.join(_mal)[:500])
else:
    print('  · el arnés no se llama a sí mismo')

# ── EL ESQUEMA, LEVANTADO Y NO LEÍDO ──────────────────────────────────────
#
# QUÉ PASARÍA SIN ESTO: lo que acaba de pasar. Las 74 lentes leen el código y
# las tres pruebas de arriba ejecutan la cuenta, pero NADIE había corrido
# nunca las migraciones, y nadie comparaba el nombre de la columna que el
# código pide con el nombre de la columna que existe.
#
# MEDIDO EL 16 DE NOVIEMBRE A LAS 23:40, con las migraciones corridas contra
# un PostgreSQL de verdad: de los 45 pares tabla.columna que el código nombra,
# DOS no existían, y las dos se caen en silencio porque PostgREST contesta 400
# con `42703` y no ejecuta la sentencia entera:
#
#   · `patients.phone` → la ficha del paciente la pide en su select, el select
#     falla, `data` llega null y la pantalla hace `notFound()`: 404 en la ficha
#     de CUALQUIER paciente. Y el emparejado con GHL lee la misma columna.
#   · `practitioners.inversion_mensual` → viaja dentro del mismo `update` que
#     la marca, la especialidad, el color y el calendario: el sanador escribe
#     su marca, aprieta Guardar, la base no cambia NADA y la pantalla no
#     muestra ningún error.
#
# Por qué se levanta la base en vez de leer el `.sql`: el primer intento de
# medir esto con una expresión regular perdió `access_token` y `created_at` de
# `patients`, porque el comentario `--` del final de la línea se quedaba
# pegado al nombre de la columna siguiente. El esquema no se lee: se levanta,
# y después se le pregunta a `information_schema` qué quedó.
#
# Probada contra su propio fallo, tres veces: sacando `inversion_mensual` de
# la migración se ponen rojas tres lentes; sacando `phone`, dos; y rompiendo
# una migración, la de esa migración.
_ESQ = 'scripts/prueba-el-esquema-real.py'
if os.path.exists(_ESQ):
    _re_ = subprocess.run([sys.executable, _ESQ], capture_output=True, text=True)
    _sal = (_re_.stdout or '') + (_re_.stderr or '')
    _rj = [l.strip() for l in _sal.splitlines() if '✗' in l]
    if 'sin PostgreSQL local' in _sal:
        print('  ⚠ SIN MEDIR: no hay PostgreSQL local para levantar el esquema')
    else:
        check('las migraciones corren, el esquema tiene toda columna que el '
              'código pide, la RLS de cada tabla aísla a su sanador y el '
              'comprobante de cada cobro es de su dueño',
              _re_.returncode == 0, '; '.join(_rj)[:500] or _sal.strip()[-200:])

    # ── Y EL ARNÉS DE ESA PRUEBA: ¿VE LA TABLA QUE FALTA? ──────────────────
    #
    # Medido el 17 de noviembre a las 11:30: la prueba de arriba decía medir
    # «toda columna que el código nombra existe», y su recorrido se SALTEABA
    # la tabla que no existe (`if tabla not in objetos: continue`). Seis
    # tablas enteras ausentes y la lente en verde. Este arnés pone los ocho
    # defectos —la tabla borrada, la cubeta inventada, la RLS apagada, la
    # política sin dueño, la clave primaria movida y las dos formas de una
    # excepción inalcanzable— y exige que la lente nombrada se ponga roja.
    #
    # Y seis más, del 17 de noviembre: los de la RLS de TODAS las tablas.
    # Hasta ese día las únicas políticas ejercitadas eran las tres de la
    # campanita; las otras once tablas tenían su `create policy` escrita y
    # nunca corrida. El bloque nuevo de la prueba del esquema las sienta a
    # todas en la silla de un sanador —ve la suya, no escribe a nombre de
    # otro, no toca la fila ajena— y estos seis defectos rompen el
    # aislamiento de una tabla distinta de notifications cada uno, para que
    # lo vea el recorrido genérico y no una lente escrita a mano.
    #
    # Y tres del 18 de noviembre, de los ARCHIVOS: la cubeta de los
    # comprobantes puesta pública, su política dejando de preguntar de quién
    # es la carpeta —textualmente el agujero que TCD tenía vivo ese día en
    # sus dos cubetas públicas— y el portazo del otro lado, la escritura
    # cerrada, que rompe `/api/cobros` y con él el contador X/10.
    _ARN = 'scripts/probar-que-la-lente-de-la-tabla-ve-el-defecto.py'
    if os.environ.get('MCD_SIN_ARNES') != '1' and os.path.exists(_ARN):
        _a2 = subprocess.run([sys.executable, _ARN], capture_output=True, text=True,
                             env={**os.environ, 'MCD_SIN_ARNES': '1'})
        _m2 = [l.strip() for l in (_a2.stdout + _a2.stderr).splitlines() if '✗' in l]
        check('la lente de la tabla, la de la RLS y la de los archivos ven '
              'sus diecisiete defectos',
              _a2.returncode == 0, '; '.join(_m2)[:500])
else:
    check('existe la prueba del esquema real', False, f'falta {_ESQ}')

for _p in _PRUEBAS:
    _codigo = rdc(_p)
    check(f'{os.path.basename(_p)} sale con 1 cuando algo falla',
          'process.exit(fallas === 0 ? 0 : 1)' in _codigo,
          'sin esa línea, imprime ✗ y termina en 0: la batería la da por buena')
    check(f'{os.path.basename(_p)} cuenta sus fallas al afirmar',
          'if (!ok) fallas++' in _codigo,
          'una prueba que no suma la falla no la puede reportar')


# ── EL INVENTARIO DEL ENTORNO: LO QUE EL CÓDIGO PIDE, ESCRITO ────────────
#
# Medido el 17 de noviembre a las 07:25, después de encontrar lo mismo en TCD.
# MCD no tiene `.env.example`: su lista de variables es la tabla de
# README-DEPLOY.md, y esa tabla se titula «TODAS». No lo era: el código leía
# tres que no estaban —`NEXT_PUBLIC_APP_URL`, `AI_PROXY_URL` y `AI_MODEL`—, y
# las dos últimas no estaban en NINGÚN README. La del proxy es la que importa:
# con la variable vacía el asistente no se apaga, le pega al proxy escrito por
# defecto en `src/lib/ai/proxy.ts`, así que nadie se enteraría de que la
# dirección que creía haber cargado no está cargada.
#
# Las puertas: la directa, la de corchetes, y la que pasa por una variable en
# el medio (`const env = process.env`), que es la que en TCD dejaba ciega a la
# lente de las claves. Se mide sobre el archivo SIN comentarios: una variable
# nombrada en un comentario no es una variable leída.
_DEL_ANDAMIO = ('NODE_ENV', 'PORT', 'NEXT_RUNTIME')
_DIRECTA_ENV = re.compile(
    r'process\s*\.\s*env\s*'
    r'(?:\.\s*([A-Z][A-Z0-9_]*)|\[\s*[\'"]([A-Z][A-Z0-9_]*)[\'"]\s*\])')
_ATAJO_ENV = re.compile(
    r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*([^;\n]*?\.env\b[^;\n]*)')


def _entorno_de(_texto):
    """Toda variable de entorno que este código lee, por cualquier puerta."""
    _v = {_m.group(1) or _m.group(2) for _m in _DIRECTA_ENV.finditer(_texto)}
    for _m in _ATAJO_ENV.finditer(_texto):
        # `const X = process.env.FOO` no es atajo: es lectura directa, ya
        # contada. Atajo es el que se queda con el objeto entero.
        if not re.search(r'\.env\b(?!\s*\.\s*[A-Z])', _m.group(2)): continue
        _v |= {_m2.group(1) or _m2.group(2) for _m2 in re.finditer(
            re.escape(_m.group(1)) +
            r'\s*(?:\.\s*([A-Z][A-Z0-9_]*)|\[\s*[\'"]([A-Z][A-Z0-9_]*)[\'"]\s*\])',
            _texto)}
    return _v


_leidas_env = {}
for _f_env in sorted(glob.glob('src/**/*.ts', recursive=True)
                     + glob.glob('src/**/*.tsx', recursive=True)):
    for _v_env in _entorno_de(rdc(_f_env)):
        _leidas_env.setdefault(_v_env, set()).add(_f_env)
_TABLA_ENV = 'README-DEPLOY.md'
# Sin comentarios: una variable nombrada dentro de un `<!-- -->` del README
# no está declarada, y la regla de la casa no deja afirmar sobre el crudo.
_tabla = rdc(_TABLA_ENV)
_declaradas_env = set(re.findall(r'^\|\s*([A-Z][A-Z0-9_]*)\s*\|', _tabla, re.M))
_sin_tabla = sorted(_v for _v in _leidas_env
                    if _v not in _DEL_ANDAMIO and not _v.startswith('VERCEL_')
                    and _v not in _declaradas_env)
check(f'toda variable que el código lee está en la tabla de {_TABLA_ENV}',
      not _sin_tabla,
      ', '.join(_sin_tabla) + ' — la que no está en la tabla no se carga en '
      'Vercel, y lo que vive de ella no anda')
_nadie_lee_env = sorted(_declaradas_env - set(_leidas_env))
check('y toda variable de esa tabla la lee alguien',
      not _nadie_lee_env,
      ', '.join(_nadie_lee_env) + ' — cargar una variable que nadie lee es '
      'creer que encendiste algo')
# La del puente se carga de los dos lados con el MISMO valor, así que las dos
# listas tienen que nombrarla: si TCD la pide y acá no figura, el puente queda
# con un solo lado cargado y contesta 401 para siempre.
check('la clave del puente está en las dos listas',
      'TCD_INTEGRATION_KEY' in _declaradas_env
      and 'TCD_INTEGRATION_KEY' in _leidas_env,
      'el puente se cae del lado que no la tenga')


# ── Y LA ÚNICA PREGUNTA QUE NINGUNA DE LAS DOS BATERÍAS SE HACÍA ──────────
#
# Los diez bloques de arriba miden el código. Ninguno medía que el código
# HAYA SALIDO: el contenedor de estas despertadas es de usar y tirar, y lo
# que queda commiteado y sin subir se pierde con él, dejando en el mapa una
# fila «cerrado · hash» que apunta a un commit que nadie tiene.
#
# MEDIDO EL 17 DE NOVIEMBRE DE 2026, y sobre este repo: una despertada leyó
# `origin/main` de MCD, lo vio tres commits atrás y dio por perdido el
# trabajo de las despertadas del 16 a las 23:50, del 17 a las 08:07 y del 17
# a las 11:42. Era falso: el `git fetch` había quedado rechazado, así que
# `refs/remotes/origin/main` era una FOTO VIEJA del remoto, guardada en
# disco, que `git status` y `git rev-parse` leen sin avisar de qué fecha es.
# El remoto de verdad —`git ls-remote`, por la red— estaba al día. El ref
# local miente en las dos direcciones, y las dos cuestan: atrás gasta un
# turno «recuperando» lo que ya está subido, y adelante —un `push` que falló
# con el ref ya movido— pierde el trabajo de verdad.
_SUB = 'scripts/prueba-el-trabajo-subido.py'
if os.path.exists(_SUB):
    _ps = subprocess.run([sys.executable, _SUB], capture_output=True, text=True)
    _ss = (_ps.stdout or '') + (_ps.stderr or '')
    if 'SIN MEDIR' in _ss:
        print('  ⚠ SIN MEDIR: el remoto no contestó, así que no se sabe si lo '
              'commiteado salió del repo')
    else:
        check('lo commiteado salió del repo, y el ref de origin no es una foto vieja',
              _ps.returncode == 0,
              '; '.join(l.strip() for l in _ss.splitlines() if '✗' in l)[:400])

    # Y su arnés: el defecto de esta lente no es texto en un archivo sino el
    # ESTADO DE GIT, así que no entra en el arnés de la batería. Se arma un
    # `--bare` y cuatro clones en una carpeta temporal y se le pone cada
    # defecto. El ejercicio 3 le encontró un agujero al primer intento de la
    # lente: `rev-list HEAD --not <sha>` revienta con «bad object» cuando ese
    # commit del remoto no está en este disco, que es el caso del ref viejo.
    _ARS = 'scripts/probar-que-la-lente-del-trabajo-subido-ve-el-defecto.py'
    if os.environ.get('MCD_SIN_ARNES') != '1' and os.path.exists(_ARS):
        _as = subprocess.run([sys.executable, _ARS], capture_output=True, text=True)
        check('la lente del trabajo subido ve sus cinco defectos del estado de git',
              _as.returncode == 0,
              '; '.join(l.strip() for l in (_as.stdout + _as.stderr).splitlines()
                        if '✗' in l)[:400])

print('\n' + ('════ BATERÍA EN VERDE ════' if F == 0 else f'════ {F} FALLA(S) ════') + '\n')
sys.exit(0 if F == 0 else 1)
