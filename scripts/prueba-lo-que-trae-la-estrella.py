#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LO QUE TRAE LA ESTRELLA: EL CAMPO QUE SE LEE POR NOMBRE Y NO EXISTE     ║
# ╚══════════════════════════════════════════════════════════════════════════╝
#
# POR QUÉ EXISTE ESTA LENTE.
#
# `prueba-el-esquema-real.py` compara el nombre de cada columna que el código
# PIDE —la que va escrita dentro de `select('a, b, c')`— con el nombre de la
# columna que existe. Tiene dos huecos escritos en su propia cabecera, y los
# dos se juntan en el mismo lugar:
#
#   · «No valida las columnas de una VISTA (`mis_numeros`)».
#   · Un `select('*')` no nombra ninguna columna, así que no hay nada que
#     comparar: la lente lo saltea y queda en verde.
#
# Pero el código SÍ nombra las columnas de un `select('*')`: las nombra
# después, al leer el resultado por propiedad (`n?.roi_mes`). Y ahí nadie
# miraba. Medido el 18 de noviembre de 2026, levantando las seis migraciones
# contra un PostgreSQL 16 y preguntándole a `information_schema`: el Tablero
# —la pantalla que el sanador abre todos los días— lee OCHO campos de
# `mis_numeros` y la vista tiene SIETE. El octavo, `roi_mes`, no estaba en
# ningún `.sql` del repo.
#
# Y no era un campo de adorno: es la condición del cartel de abajo, «Tu
# inversión en MiClínica se pagó N×». `Number(undefined ?? 0) > 0` es falso
# siempre, así que esa rama no se dibujó nunca desde el 8 de julio y la
# pantalla degradaba en silencio al cartel corto. Ningún error, ningún 400:
# PostgREST devuelve las siete que existen y la octava llega `undefined`.
#
# Es la MISMA forma que la ausencia de tablas del 17 y la de columnas del 16:
# lo que falta no se mide, se saltea. Por eso esta lente no pregunta «¿coincide
# lo que el código pide?» sino «¿existe cada campo que el código LEE?».
#
# LO QUE MIDE, EN TRES CUERPOS:
#
#   1 · Todo campo leído por propiedad sobre el resultado de un `select('*')`
#       es una columna de verdad de esa tabla o vista. El esquema no se lee: se
#       LEVANTA, por el mismo motivo que la otra lente (el comentario `--` al
#       final de la línea se pega al nombre siguiente).
#   2 · Toda vista de `public` declara `security_invoker` en el catálogo vivo
#       —no en el `.sql`—. Una vista sin esa opción corre con los permisos de
#       su dueño y se SALTEA el RLS de sus tablas base: el filtro del Tablero
#       vive en el cliente (`.eq('practitioner_id', user?.id)`), así que con la
#       vista abierta cualquier sanador con sesión leería los números de todos
#       cambiando un parámetro.
#   3 · Eso, ejercitado y no leído: dos sanadores sentados en su silla, cada
#       uno ve UNA fila y es la suya, sin sesión no se ve ninguna, y los
#       números que trae son los de él. Incluido `roi_mes`, contra la cuenta
#       que el Tablero ya hacía a mano en la tarjeta «Retorno».
#
# Corre: python3 scripts/prueba-lo-que-trae-la-estrella.py
# Su arnés: scripts/probar-que-la-lente-de-la-estrella-ve-el-defecto.py
import glob, os, re, shutil, socket, subprocess, sys, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fallas = 0


def ok(n, cond, det=''):
    global fallas
    if cond:
        print(f'  ✓ {n}')
    else:
        fallas += 1
        print(f'  ✗ {n}' + (f' — {det}' if det else ''))


# ── 1 · LEVANTAR EL POSTGRES ────────────────────────────────────────────────
def bin_pg():
    for d in sorted(glob.glob('/usr/lib/postgresql/*/bin'), reverse=True):
        if os.path.isfile(os.path.join(d, 'initdb')):
            return d
    return None


PGBIN = bin_pg()
if not PGBIN:
    print('sin PostgreSQL local: no se puede probar acá')
    sys.exit(0)

DATA = tempfile.mkdtemp()
SOCK = tempfile.mkdtemp()
# El puerto se pide al sistema y no se escribe a mano: el arnés corre esta
# lente muchas veces una detrás de la otra, y con puerto fijo la segunda
# arranca sin base y se pone roja por el motivo equivocado.
with socket.socket() as _s:
    _s.bind(('127.0.0.1', 0))
    PORT = str(_s.getsockname()[1])
for d in (DATA, SOCK):
    os.chmod(d, 0o777)
    subprocess.run(['chown', '-R', 'postgres', d], capture_output=True)


def apagar():
    subprocess.run(['su', 'postgres', '-c', f'{PGBIN}/pg_ctl -D {DATA} stop -m immediate'],
                   capture_output=True)
    shutil.rmtree(DATA, ignore_errors=True)
    shutil.rmtree(SOCK, ignore_errors=True)


import atexit
atexit.register(apagar)

subprocess.run(['su', 'postgres', '-c', f'{PGBIN}/initdb -D {DATA} -A trust -U postgres'],
               capture_output=True)
subprocess.run(['su', 'postgres', '-c',
                f"{PGBIN}/pg_ctl -D {DATA} -l {DATA}/log -o '-k {SOCK} -p {PORT}' start"],
               capture_output=True)


def psql(sql=None, archivo=None, tuplas=False):
    """psql por socket, sin contraseña, parando en el primer ERROR. El SQL va
    por archivo y no por `-c`: pasarlo por `su` con comillas lo parte."""
    banderas = '-tA -q ' if tuplas else '-q '
    if sql is not None:
        f = os.path.join(DATA, 'q.sql')
        with open(f, 'w', encoding='utf-8') as h:
            h.write(sql)
        subprocess.run(['chmod', '644', f], capture_output=True)
        archivo = f
    return subprocess.run(['su', 'postgres', '-c',
                           f'psql -h {SOCK} -p {PORT} -U postgres {banderas}'
                           f'-v ON_ERROR_STOP=1 -f {archivo}'],
                          capture_output=True, text=True)


if psql('select 1;').returncode != 0:
    print('sin PostgreSQL local: no se puede probar acá')
    sys.exit(0)

# ── 2 · EL ANDAMIAJE: lo que pone Supabase y el `.sql` da por existente ─────
psql('''
create role authenticated; create role anon; create role service_role;
create schema if not exists auth;
create table auth.users (id uuid primary key, email text,
                         raw_user_meta_data jsonb default '{}'::jsonb);
create or replace function auth.uid() returns uuid language sql stable
  as $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
create schema if not exists storage;
create table storage.buckets (id text primary key, name text, public boolean default false);
create table storage.objects (
  id uuid primary key default gen_random_uuid(),
  bucket_id text references storage.buckets(id),
  name text, owner uuid, created_at timestamptz default now());
create or replace function storage.foldername(name text) returns text[]
  language sql immutable as $$
    select (string_to_array(name, '/'))[1:greatest(array_length(string_to_array(name,'/'),1)-1,0)]
  $$;
grant usage on schema public, auth, storage to authenticated, anon, service_role;
''')

migs = sorted(glob.glob(os.path.join(RAIZ, 'supabase/migrations/*.sql')))
ok('hay migraciones que correr', bool(migs), 'no encontré supabase/migrations/*.sql')
for m in migs:
    r = psql(archivo=m)
    err = [l for l in (r.stdout + r.stderr).split('\n') if l.startswith('ERROR') or 'ERROR:' in l]
    ok(f'{os.path.basename(m)} corre contra PostgreSQL',
       r.returncode == 0 and not err, (err[0] if err else (r.stderr or '').strip()[:160]))

# Los permisos que Supabase da por defecto y las migraciones no escriben. Sin
# esto el ejercicio de abajo se caería por «permission denied» —el motivo
# equivocado— y haría creer que la vista no deja pasar al dueño.
psql('grant all on all tables in schema public to authenticated, anon, service_role;')

# ── 3 · EL CATÁLOGO VIVO ────────────────────────────────────────────────────
r = psql("select table_name || '.' || column_name from information_schema.columns "
         "where table_schema = 'public' order by 1;", tuplas=True)
COLUMNAS = set(l.strip() for l in r.stdout.split('\n') if l.strip())
r = psql("select table_name from information_schema.views where table_schema='public' "
         "union select table_name from information_schema.tables where table_schema='public';",
         tuplas=True)
OBJETOS = set(l.strip() for l in r.stdout.split('\n') if l.strip())
ok('la base contesta qué columnas quedaron', len(COLUMNAS) > 20, f'solo {len(COLUMNAS)}')

# ── 4 · LOS SITIOS DE `select('*')`, Y LO QUE SE LEE DE CADA UNO ────────────
METODOS = {
    'map', 'filter', 'length', 'forEach', 'sort', 'slice', 'find', 'some', 'every',
    'reduce', 'push', 'includes', 'join', 'at', 'concat', 'flat', 'flatMap',
    'indexOf', 'toString', 'then', 'catch', 'finally', 'keys', 'values', 'entries',
    'reverse', 'shift', 'pop', 'splice', 'findIndex', 'toLocaleString', 'toFixed',
}


def sin_comentarios(s: str) -> str:
    """Un `.from('x')` dentro de un comentario no es una consulta, y un campo
    comentado no se lee."""
    s = re.sub(r'/\*[\s\S]*?\*/', '', s)
    return re.sub(r'^\s*//.*$', '', s, flags=re.M)


def fuentes():
    out = []
    for pat in ('src/**/*.ts', 'src/**/*.tsx', 'api/**/*.ts'):
        out += glob.glob(os.path.join(RAIZ, pat), recursive=True)
    return sorted(set(out))


def sitios(texto: str):
    """Cada `.from('X')` seguido de `.select('*')`, con la variable a la que se
    ataja el resultado y el TRAMO del archivo donde esa variable es ésta.

    El tramo importa y no es un detalle: en un archivo que ata dos veces
    `const { data } = ...`, juntar las lecturas de todo el archivo da campos de
    una tabla pedidos a la otra. Fue el primer falso positivo de esta lente, el
    18 de noviembre, midiendo el repo de TCD: `session_logs` y `hoja_de_ruta`
    ataban las dos a `data` en la misma pantalla y la lente pedía las columnas
    de una en la otra. Así que el tramo termina donde la MISMA variable se
    vuelve a atar.
    """
    out = []
    for m in re.finditer(r"\.from\(\s*['\"]([a-z_][a-z_0-9]*)['\"]\s*\)", texto):
        tabla = m.group(1)
        if not re.match(r"\s*\.\s*select\(\s*['\"]\*['\"]\s*\)", texto[m.end():m.end() + 60]):
            continue
        antes = texto[max(0, m.start() - 300):m.start()]
        atados = re.findall(r"data\s*:\s*([A-Za-z_$][A-Za-z_0-9$]*)", antes)
        if atados:
            var = atados[-1]
        elif re.search(r"\{\s*data\s*(?:,[^}]*)?\}\s*=\s*(?:await\s+)?$", antes) or \
             re.search(r"\{\s*data\s*(?:,[^}]*)?\}\s*=", antes):
            var = 'data'
        else:
            continue
        # el tramo: desde el sitio hasta que la variable se vuelva a atar
        resto = texto[m.end():]
        sig = re.search(r"(?:const|let|var)\s*\{[^}]*(?<![A-Za-z_0-9$])" +
                        re.escape(var) + r"(?![A-Za-z_0-9$])[^}]*\}\s*=", resto)
        tramo = resto[:sig.start()] if sig else resto
        campos = set(re.findall(r"(?<![A-Za-z_0-9$.])" + re.escape(var) +
                                r"\s*(?:\?\.|\.)\s*([a-z_][a-z_0-9]*)", tramo))
        out.append((tabla, var, sorted(campos - METODOS)))
    return out


hallados = 0
for f in fuentes():
    texto = sin_comentarios(open(f, encoding='utf-8').read())
    rel = os.path.relpath(f, RAIZ)
    for tabla, var, campos in sitios(texto):
        hallados += 1
        ok(f"{rel}: la tabla o vista «{tabla}» del select('*') existe",
           tabla in OBJETOS, 'no está en el esquema que dejaron las migraciones')
        if tabla not in OBJETOS:
            continue
        for c in campos:
            ok(f'{rel}: {tabla}.{c} — el campo que se lee por nombre existe',
               f'{tabla}.{c}' in COLUMNAS,
               f'`{var}?.{c}` llega undefined y la pantalla degrada en silencio')

ok("hay sitios de select('*') que medir", hallados > 0,
   "ningún `.from(...).select('*')` encontrado: la lente no estaría midiendo nada")

# ── 5 · TODA VISTA RESPETA EL RLS DE QUIEN CONSULTA ─────────────────────────
r = psql("select c.relname, coalesce((select option_value from "
         "pg_options_to_table(c.reloptions) where option_name='security_invoker'), 'sin poner') "
         "from pg_class c join pg_namespace n on n.oid = c.relnamespace "
         "where n.nspname = 'public' and c.relkind = 'v' order by 1;", tuplas=True)
vistas = [l.split('|') for l in r.stdout.split('\n') if '|' in l]
for nombre, invoker in vistas:
    ok(f'la vista {nombre} declara security_invoker (respeta el RLS del que consulta)',
       invoker.strip().lower() == 'true',
       f'está en «{invoker.strip()}»: corre con los permisos de su dueño y se '
       f'saltea el RLS de sus tablas base')

# ── 6 · Y EJERCITADO: DOS SANADORES, CADA UNO SUS NÚMEROS ───────────────────
if 'mis_numeros' in OBJETOS:
    A = '11111111-1111-1111-1111-111111111111'
    B = '22222222-2222-2222-2222-222222222222'
    # La fila de `practitioners` NO se inserta: la pone el disparador
    # `on_auth_user_created_mcd` al nacer el `auth.users`. Insertarla a mano
    # reventaba por clave duplicada —primer fallo de esta lente, el 18 de
    # noviembre— y el rojo hablaba del sembrado, no del repo. Se siembra como
    # lo hace la app: nace el usuario, y después se carga lo invertido.
    sem = psql(f"""
insert into auth.users (id, email, raw_user_meta_data)
  values ('{A}', 'a@x.com', '{{"full_name":"Sanador A"}}'::jsonb),
         ('{B}', 'b@x.com', '{{"full_name":"Sanador B"}}'::jsonb);
update public.practitioners set inversion_mensual = 100 where id = '{A}';
update public.practitioners set inversion_mensual = 0   where id = '{B}';
insert into public.patients (practitioner_id, full_name, status)
  values ('{A}', 'Paciente de A', 'activo'), ('{A}', 'Otro de A', 'onboarding'),
         ('{B}', 'Paciente de B', 'activo');
insert into public.cobros (practitioner_id, amount_usd, receipt_path, paid_at)
  values ('{A}', 250, '{A}/uno.jpg', now()),
         ('{B}', 70,  '{B}/uno.jpg', now());
""")
    ok('el sembrado de los dos sanadores entra', sem.returncode == 0,
       (sem.stderr or '').strip()[-180:])
    ok('el disparador le dio su fila a cada sanador (son dos)',
       (psql("select count(*) from public.practitioners;", tuplas=True).stdout.strip() == '2'),
       'sin las dos filas, lo de abajo mide otra cosa')

    def como(rol, uid, consulta):
        """La misma consulta, sentada en una silla. `uid` en None es sin sesión."""
        pre = f'set role {rol};\n'
        if uid:
            pre += f"set request.jwt.claim.sub = '{uid}';\n"
        r = psql(pre + consulta, tuplas=True)
        return [l.strip() for l in r.stdout.split('\n') if l.strip()]

    filas_a = como('authenticated', A,
                   "select practitioner_id || '|' || pacientes_activos || '|' || "
                   "ingresos_mes || '|' || cobros_totales || '|' || roi_mes "
                   "from public.mis_numeros;")
    ok('el sanador A ve UNA fila en mis_numeros, y es la suya',
       len(filas_a) == 1 and filas_a[0].startswith(A),
       f'vio {len(filas_a)}: {filas_a[:3]}')
    if len(filas_a) == 1 and filas_a[0].count('|') == 4:
        partes = filas_a[0].split('|')
        ok('los pacientes activos que ve A son los suyos (1, no los 2 del total)',
           partes[1] == '1', f'vio {partes[1]}')
        ok('los ingresos del mes que ve A son los suyos (250, no los 320 del total)',
           partes[2].startswith('250'), f'vio {partes[2]}')
        ok('roi_mes es ingresos sobre inversion, la misma cuenta que la tarjeta '
           '«Retorno» del Tablero (250 / 100 = 2.5)',
           partes[4].startswith('2.5'), f'trajo {partes[4]}')

    filas_b = como('authenticated', B,
                   "select practitioner_id || '|' || roi_mes from public.mis_numeros;")
    ok('el sanador B ve UNA fila, y es la suya',
       len(filas_b) == 1 and filas_b[0].startswith(B), f'vio {len(filas_b)}: {filas_b[:3]}')
    if len(filas_b) == 1 and '|' in filas_b[0]:
        ok('sin inversion cargada, roi_mes es 0 y el cartel largo no se dibuja '
           '(nadie ve «se pago 0x» ni una division por cero)',
           filas_b[0].split('|')[1].startswith('0'), f'trajo {filas_b[0].split("|")[1]}')

    sin_sesion = como('anon', None, "select count(*) from public.mis_numeros;")
    ok('sin sesion no se ve ninguna fila de mis_numeros',
       sin_sesion == ['0'], f'conto {sin_sesion}')

print()
print(f'{"TODO EN VERDE" if fallas == 0 else str(fallas) + " EN ROJO"}')
sys.exit(0 if fallas == 0 else 1)
