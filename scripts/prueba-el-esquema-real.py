#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LAS COLUMNAS QUE EL CÓDIGO PIDE, CONTRA UN PostgreSQL DE VERDAD         ║
# ╚══════════════════════════════════════════════════════════════════════════╝
#
# Las 74 lentes de MCD leen el código y tres pruebas lo ejecutan, pero NADIE
# había corrido nunca las cuatro migraciones, y nadie comparaba el nombre de
# la columna que el código pide con el nombre de la columna que existe.
#
# Esa comparación no se puede hacer leyendo el `.sql` con una expresión
# regular: el 16 de noviembre, el primer intento de medir esto perdió
# `access_token` y `created_at` de `patients` porque el comentario `--` del
# final de la línea se quedaba pegado al nombre de la columna siguiente. Así
# que el esquema NO se lee: se LEVANTA. Las migraciones corren contra
# PostgreSQL y después se le pregunta a `information_schema` qué quedó.
#
# Por qué importa el nombre exacto: PostgREST no ignora la columna que no
# conoce —contesta 400 con `42703` y la sentencia ENTERA no se ejecuta—. Una
# sola columna inventada en un `select` deja la fila en `null`, y una en un
# `update` tira al suelo también los campos que sí existen, sin que la
# pantalla muestre un error.
#
# Dos cosas que esta prueba NO hace, a propósito:
#   · No valida las columnas de una VISTA (`mis_numeros`): la vista se arma de
#     un select y sus nombres no están en `information_schema` igual.
#   · No valida lo que va DENTRO de un json (`steps: [{label, done}]`): esas
#     claves no son columnas. Se distinguen porque viven en un objeto que no
#     es el primer argumento de `insert`/`update`.
import os, re, shutil, subprocess, sys, tempfile

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
    for d in sorted(__import__('glob').glob('/usr/lib/postgresql/*/bin'), reverse=True):
        if os.path.isfile(os.path.join(d, 'initdb')):
            return d
    return None

PGBIN = bin_pg()
if not PGBIN:
    print('sin PostgreSQL local: no se puede probar acá')
    sys.exit(0)

DATA = tempfile.mkdtemp()
SOCK = tempfile.mkdtemp()
# El puerto se pide al sistema en vez de escribirse a mano: con un puerto
# fijo, dos corridas seguidas se pisan —el arnés que prueba esta misma lente
# corre ocho veces una detrás de la otra— y la segunda arranca sin base, con
# TODAS las lentes rojas por el motivo equivocado.
import socket as _socket
with _socket.socket() as _s:
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
    """psql como lo corre el equipo: por socket, sin contraseña, parando en el
    primer ERROR. El SQL va por archivo y no por -c: pasarlo por `su` con
    comillas lo parte."""
    banderas = '-tA ' if tuplas else '-q '
    if sql is not None:
        f = os.path.join(DATA, 'q.sql')
        with open(f, 'w', encoding='utf-8') as h:
            h.write(sql)
        subprocess.run(['chmod', '644', f], capture_output=True)
        archivo = f
    r = subprocess.run(['su', 'postgres', '-c',
                        f'psql -h {SOCK} -p {PORT} -U postgres {banderas}'
                        f'-v ON_ERROR_STOP=1 -f {archivo}'],
                       capture_output=True, text=True)
    return r

arranque = psql('select 1;')
if arranque.returncode != 0:
    print('sin PostgreSQL local: no se puede probar acá')
    sys.exit(0)

# ── 2 · EL ANDAMIAJE ────────────────────────────────────────────────────────
# Lo mínimo para que las migraciones resuelvan: no es Supabase, son los tres
# roles y las dos tablas de sistema que el `.sql` da por existentes.
psql('''
create role authenticated;
create role anon;
create role service_role;
create schema if not exists auth;
-- `raw_user_meta_data` no es decorado: el disparador `on auth.users` de la
-- primera migracion saca de ahi el nombre del sanador. Sin la columna, el
-- disparador revienta y el andamiaje echaria la culpa al repo.
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
-- `storage.foldername` la pone Supabase, no PostgreSQL: parte el path del
-- archivo en carpetas. La politica del comprobante la usa para comparar la
-- primera carpeta con el id del sanador, asi que sin ella la migracion no
-- corre y el andamiaje mentiria sobre un error que no es del repo.
create or replace function storage.foldername(name text) returns text[]
  language sql immutable as $$
    select (string_to_array(name, '/'))[1:greatest(array_length(string_to_array(name,'/'),1)-1,0)]
  $$;
grant usage on schema public, auth, storage to authenticated, anon, service_role;
''')

# ── 3 · LAS MIGRACIONES CORREN ──────────────────────────────────────────────
import glob
migs = sorted(glob.glob(os.path.join(RAIZ, 'supabase/migrations/*.sql')))
ok('hay migraciones que correr', bool(migs), 'no encontré supabase/migrations/*.sql')
for m in migs:
    r = psql(archivo=m)
    err = [l for l in (r.stdout + r.stderr).split('\n') if l.startswith('ERROR') or 'ERROR:' in l]
    ok(f'{os.path.basename(m)} corre contra PostgreSQL',
       r.returncode == 0 and not err, (err[0] if err else (r.stderr or '').strip()[:160]))

# Los permisos de tabla que Supabase da por defecto y las migraciones no
# escriben: en el proyecto real hay un `alter default privileges` que le da
# todo sobre `public` a los tres roles. Sin esto, el ejercicio de RLS de abajo
# se caería por «permission denied» —el motivo equivocado— y haría creer que
# la política no deja pasar al dueño.
psql('grant all on all tables in schema public to authenticated, anon, service_role;')

# ── 4 · EL ESQUEMA QUE QUEDÓ, PREGUNTADO A LA BASE ──────────────────────────
r = psql("select table_name || '.' || column_name from information_schema.columns "
         "where table_schema = 'public' order by 1;", tuplas=True)
reales = set(l.strip() for l in r.stdout.split('\n') if l.strip())
r2 = psql("select table_name from information_schema.views where table_schema='public' "
          "union select table_name from information_schema.tables where table_schema='public';",
          tuplas=True)
objetos = set(l.strip() for l in r2.stdout.split('\n') if l.strip())
r3 = psql("select table_name from information_schema.views where table_schema='public';", tuplas=True)
vistas = set(l.strip() for l in r3.stdout.split('\n') if l.strip())
ok('la base contesta qué columnas quedaron', len(reales) > 20, f'solo {len(reales)}')

# ── 5 · LAS COLUMNAS QUE EL CÓDIGO PIDE ─────────────────────────────────────
def sin_comentarios(s: str) -> str:
    """El TypeScript sin comentarios. Un `.from('x')` dentro de un comentario
    no es una consulta, y un nombre de columna comentado tampoco se pide."""
    s = re.sub(r'/\*[\s\S]*?\*/', '', s)
    return re.sub(r'^\s*//.*$', '', s, flags=re.M)

def cierre(t: str, i: int) -> int:
    """El índice del paréntesis que cierra al que abre en i, contando los de
    adentro y sin mirar los que viven en un texto."""
    d, j, q = 0, i, None
    while j < len(t):
        c = t[j]
        if q:
            if c == '\\': j += 2; continue
            if c == q: q = None
        elif c in '\'"`': q = c
        elif c == '(': d += 1
        elif c == ')':
            d -= 1
            if d == 0: return j
        j += 1
    return -1

def cadena(t: str, i: int):
    """Los eslabones de la cadena que arranca en `.from(...)`: pares
    (método, argumento). Se camina eslabón por eslabón y NO por una ventana de
    N caracteres: la ventana se comía el `.map(label => ({label, done}))` de la
    línea siguiente y daba `protocols.label` y `protocols.done` como columnas
    que faltan, cuando son claves de un json."""
    out = []
    while True:
        m = re.compile(r'\s*\.\s*([A-Za-z_][A-Za-z_0-9]*)\s*\(').match(t, i)
        if not m: return out
        c = cierre(t, m.end() - 1)
        if c < 0: return out
        out.append((m.group(1), t[m.end():c]))
        i = c + 1

def columnas_del_select(arg: str):
    """Los nombres de un `select('a, b, tabla(c, d)')`.

    Lo que va entre paréntesis es OTRA tabla —el embebido de PostgREST—, así
    que no son columnas de ésta: por eso se sacan antes de partir por comas.
    Fue la segunda causa de falso positivo del primer intento:
    `protocols(title, description, steps)` daba `patient_protocols.description`.
    """
    a = arg.strip().strip('\'"`')
    if not a or '${' in a: return set()
    # El nombre que viene PEGADO a un parentesis es la tabla embebida, no una
    # columna: en `select('id, patients(full_name)')`, `patients` es otra
    # tabla. Se borra el nombre junto con su parentesis, o la lente pide una
    # columna `cobros.patients` que no puede existir.
    a = re.sub(r'[a-z_][a-z_0-9]*(?:!(?:inner|left))?\s*\(', '(', a)
    plano, d = [], 0
    for ch in a:
        if ch == '(': d += 1; continue
        if ch == ')': d -= 1; continue
        if d == 0: plano.append(ch)
    out = set()
    for c in ''.join(plano).split(','):
        c = c.strip()
        if ':' in c: c = c.split(':', 1)[1].strip()   # alias:columna
        c = c.lstrip('!').split('!')[0].strip()        # columna!inner
        if not c or c == '*' or not re.fullmatch(r'[a-z_][a-z_0-9]*', c): continue
        out.add(c)
    return out

def claves_del_objeto(arg: str):
    """Las claves del primer nivel de `{ a: 1, b: 2 }`. Solo el primer nivel:
    lo de más adentro es json, no columnas."""
    a = arg.strip()
    if not a.startswith('{'): return set()
    cuerpo, d, q, out = a[1:], 0, None, set()
    i, llave = 0, ''
    nivel = 0
    for ch in cuerpo:
        if q:
            if ch == q: q = None
            continue
        if ch in '\'"`': q = ch; continue
        if ch in '{[(': nivel += 1; continue
        if ch in '}])':
            if nivel == 0: break
            nivel -= 1; continue
        if nivel == 0: llave += ch
    for m in re.finditer(r'(?:^|,)\s*([a-z_][a-z_0-9]*)\s*:', llave):
        out.add(m.group(1))
    return out

FILTROS = {'eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'like', 'ilike', 'order', 'contains'}

# ── LA AUSENCIA QUE ERA EL DEFECTO ──────────────────────────────────────────
#
# Medido el 17 de noviembre a las 11:30. El recorrido de abajo empezaba con
# `if tabla in vistas or tabla not in objetos: continue`, así que una tabla
# que NO EXISTE no se medía: se saltaba, y la lente que dice «toda columna que
# el código nombra existe en el esquema» daba verde con SEIS tablas enteras
# ausentes. Tres eran de MCD —`agent_config`, `patient_notes` y
# `notifications`—, y las tres fallaban en silencio en producción: el Guardar
# del Asistente no guardaba, la nota del paciente no se escribía y la
# campanita no sonaba nunca.
#
# Así que primero se mide la TABLA y después la columna. Y el saltearse
# —que sigue siendo necesario para no pedirle columnas a algo que no está—
# ya no es silencioso: lo que se saltea queda anotado.
#
# `AJENAS` es la única forma de que una tabla ausente no ponga la batería
# roja, y se paga con un motivo escrito. Las dos que están acá viven en el
# proyecto Supabase de TCD, que es OTRO proyecto: MCD no las puede crear ni
# leer, y la consulta que las nombra no puede devolver una fila nunca.
AJENAS = {
    'profiles': 'del proyecto Supabase de TCD — «Mi marca» la lee para precargar '
                'la identidad del sanador, y no puede: otro proyecto',
    'clinica_artefactos': 'del proyecto Supabase de TCD — «Protocolos» la lee para '
                          'traer el método del Camino, y no puede: otro proyecto',
}

pedidas = {}
nombradas = {}     # tabla -> {archivos}
cubetas = {}       # bucket de storage -> {archivos}
for base, _, fs in os.walk(os.path.join(RAIZ, 'src')):
    if 'node_modules' in base: continue
    for f in sorted(fs):
        if not f.endswith(('.ts', '.tsx')): continue
        ruta = os.path.join(base, f)
        src = sin_comentarios(open(ruta, encoding='utf-8', errors='replace').read())
        rel = os.path.relpath(ruta, RAIZ)
        for m in re.finditer(r"\.from\(\s*['\"]([a-z_0-9]+)['\"]\s*\)", src):
            tabla = m.group(1)
            # `supabase.storage.from('comprobantes')` NO es una tabla: es una
            # cubeta. Medirla contra `information_schema` daba `comprobantes`
            # como tabla que falta, cuando la migración 20260707 sí la crea.
            if re.search(r'\.\s*storage\s*$', src[:m.start()]):
                cubetas.setdefault(tabla, set()).add(rel)
                continue
            nombradas.setdefault(tabla, set()).add(rel)
            if tabla in vistas or tabla not in objetos: continue
            for met, arg in cadena(src, m.end()):
                cols = set()
                if met == 'select': cols = columnas_del_select(arg)
                elif met in FILTROS:
                    mm = re.match(r"\s*['\"]([a-z_][a-z_0-9]*)['\"]", arg)
                    if mm: cols = {mm.group(1)}
                elif met in ('insert', 'update', 'upsert'): cols = claves_del_objeto(arg)
                for c in cols:
                    pedidas.setdefault((tabla, c), set()).add(os.path.relpath(ruta, RAIZ))

ok('el código nombra tablas que se pueden medir', len(nombradas) > 8,
   f'solo {len(nombradas)}')

ausentes = sorted(t for t in nombradas if t not in objetos and t not in AJENAS)
ok('toda tabla que el código nombra existe en el esquema', not ausentes,
   '; '.join(f'{t} ← {sorted(nombradas[t])[0]}' for t in ausentes[:4]))
for t in ausentes:
    print(f'      · {t} — nombrada en {", ".join(sorted(nombradas[t]))}')

# Una excepción que ya no es excepción es una tapa. Dos formas de serlo: que
# nadie la nombre (quedó de un borrado) o que la tabla SÍ exista (se creó y
# nadie sacó la excepción). Es la misma lente de la lista blanca del entorno,
# del 17 a las 07:25: una lista de perdón con entradas inalcanzables es la
# huella de una puerta ciega.
sobran = sorted(t for t in AJENAS if t not in nombradas or t in objetos)
ok('ninguna excepción de AJENAS es inalcanzable', not sobran,
   '; '.join(f'{t}: ' + ('nadie la nombra' if t not in nombradas else 'ya existe en el esquema')
             for t in sobran))

# Las cubetas, por la misma puerta: `.storage.from('x')` tiene que existir en
# `storage.buckets` o el upload contesta error y el cobro no se registra.
r = psql("select id from storage.buckets;", tuplas=True)
cubetas_reales = set(l.strip() for l in r.stdout.split('\n') if l.strip())
sin_cubeta = sorted(c for c in cubetas if c not in cubetas_reales)
ok('toda cubeta de storage que el código nombra existe', not sin_cubeta,
   '; '.join(f'{c} ← {sorted(cubetas[c])[0]}' for c in sin_cubeta[:3]))

ok('el código pide columnas que se pueden medir', len(pedidas) > 20, f'solo {len(pedidas)}')

faltantes = sorted((t, c, sorted(d)) for (t, c), d in pedidas.items()
                   if f'{t}.{c}' not in reales)
ok('toda columna que el código nombra existe en el esquema',
   not faltantes,
   '; '.join(f'{t}.{c} ← {d[0]}' for t, c, d in faltantes[:4]))
for t, c, d in faltantes:
    print(f'      · {t}.{c} — pedida en {", ".join(d)}')

# ── 6 · LAS DOS SENTENCIAS QUE SE CAÍAN, EJERCIDAS ──────────────────────────
# Que la columna exista es la lente de arriba. Esto es la otra mitad: las dos
# sentencias EXACTAS que hacen las pantallas, corridas contra la base, con una
# fila de prueba. Si alguien vuelve a nombrar una columna que no existe, acá se
# ve lo que el cliente ve: la ficha en 404 y el Guardar que no guarda.
SAN = '11111111-1111-1111-1111-111111111111'
psql(f"""
insert into auth.users(id, email, raw_user_meta_data)
  values ('{SAN}', 'dra@ejemplo.com', '{{"full_name":"Evelyn Bernal"}}'::jsonb);
update public.practitioners set brand_name = 'Marca vieja',
  specialty = 'Especialidad vieja', brand_color = '#3D6B4F' where id = '{SAN}';
insert into public.patients(practitioner_id, full_name, email)
  values ('{SAN}', 'Ana Pérez', 'ana@ejemplo.com');
""")
hay = psql("select count(*) from public.practitioners;", tuplas=True).stdout.strip()
ok('la fila de prueba entra (el disparador de auth.users crea al sanador)',
   hay == '1', f'quedaron {hay or "0"} sanadores')

# La ficha del paciente: su select entero, el que hacía 404 en todas.
r = psql("select id, full_name, email, phone, status, access_token, ghl_contact_id "
         "from public.patients limit 1;")
err = [l for l in (r.stdout + r.stderr).split('\n') if 'ERROR' in l]
ok('la ficha del paciente: su select corre (si no, es 404 en TODA ficha)',
   r.returncode == 0 and not err, (err[0] if err else '')[:160])

# «Mi marca»: su update entero. Lo que importa no es que no dé error, es que
# los OTROS cuatro campos queden guardados: van en la misma sentencia.
r = psql(f"""update public.practitioners set brand_name = 'Marca NUEVA',
  specialty = 'Especialidad NUEVA', brand_color = '#AA0000',
  ghl_calendar_url = 'https://cal/nuevo', inversion_mensual = 450
  where id = '{SAN}';""")
err = [l for l in (r.stdout + r.stderr).split('\n') if 'ERROR' in l]
ok('«Mi marca»: su update corre', r.returncode == 0 and not err,
   (err[0] if err else '')[:160])
quedo = psql(f"select brand_name || ' / ' || specialty || ' / ' || brand_color "
             f"|| ' / ' || coalesce(inversion_mensual::text,'sin dato') "
             f"from public.practitioners where id = '{SAN}';", tuplas=True).stdout.strip()
ok('«Mi marca»: lo que el sanador escribió QUEDA guardado, los cinco campos',
   quedo == 'Marca NUEVA / Especialidad NUEVA / #AA0000 / 450',
   f'la base quedó con «{quedo}»')

# ── 7 · LAS TRES TABLAS NUEVAS, EJERCIDAS COMO LAS USA LA PANTALLA ─────────
#
# Que la tabla exista es la lente de arriba. Esto es la otra mitad, y en estas
# tres hace falta más que en las otras: las tres consultas de `notifications`
# NO filtran por sanador —el GET hace `select('*')` y el POST hace
# `update({leida:true}).eq('leida', false)` a secas—, así que se apoyan
# ENTERAS en la política. Una tabla creada sin RLS deja al sanador viendo las
# notificaciones de todos, y al apretar «marcar todas leídas» marcando las de
# todos. Por eso acá entra un segundo sanador.
OTRO = '22222222-2222-2222-2222-222222222222'
psql(f"""insert into auth.users(id, email, raw_user_meta_data)
  values ('{OTRO}', 'otro@ejemplo.com', '{{"full_name":"Otro Sanador"}}'::jsonb);""")

# «Tu Asistente»: el Guardar se aprieta DOS veces. Con `practitioner_id` sin
# ser clave primaria, el segundo upsert insertaría otra fila y el
# `maybeSingle()` de la pantalla reventaría al leer.
for v in ('cálido y profesional', 'seco y directo'):
    r = psql(f"""insert into public.agent_config(practitioner_id, tono, reglas, firma, updated_at)
      values ('{SAN}', '{v}', 'sin precios por mensaje', 'Un abrazo', now())
      on conflict (practitioner_id) do update set tono = excluded.tono,
        reglas = excluded.reglas, firma = excluded.firma, updated_at = excluded.updated_at;""")
    err = [l for l in (r.stdout + r.stderr).split('\n') if 'ERROR' in l]
    ok(f'«Tu Asistente»: el Guardar corre («{v}»)', r.returncode == 0 and not err,
       (err[0] if err else '')[:160])
q = psql(f"select count(*) || '/' || max(tono) from public.agent_config "
         f"where practitioner_id = '{SAN}';", tuplas=True).stdout.strip()
ok('«Tu Asistente»: dos Guardar dejan UNA fila, con lo último escrito',
   q == '1/seco y directo', f'la base quedó con «{q}»')

# La nota del paciente: insert y el select exacto de la ficha.
pac = psql("select id from public.patients limit 1;", tuplas=True).stdout.strip()
r = psql(f"""insert into public.patient_notes(patient_id, practitioner_id, body)
  values ('{pac}', '{SAN}', 'Primera consulta: derivada por kinesiología.');""")
err = [l for l in (r.stdout + r.stderr).split('\n') if 'ERROR' in l]
ok('la nota del paciente: su insert corre', r.returncode == 0 and not err,
   (err[0] if err else '')[:160])
q = psql(f"select body from public.patient_notes where patient_id = '{pac}' "
         f"order by created_at desc limit 20;", tuplas=True).stdout.strip()
ok('la nota del paciente: queda escrita y la ficha la lee',
   q.startswith('Primera consulta'), f'la ficha leyó «{q}»')

# La campanita: dos notificaciones, una de cada sanador, escritas con la
# service role key (así las escribe `notify.ts` desde el webhook de GHL).
psql(f"""insert into public.notifications(practitioner_id, tipo, titulo, cuerpo, link)
  values ('{SAN}', 'mensaje', 'Mensaje nuevo de Ana', 'Hola doctora', '/personas'),
         ('{OTRO}', 'cita', 'Cita nueva', 'Mañana 10:00', '/agenda');""")

# Y ahora el GET de la campanita, con la sesión del primer sanador: su
# `select('*')` sin filtro, tal cual.
vistas_por_san = psql(f"""set role authenticated;
set request.jwt.claim.sub = '{SAN}';
select count(*) from public.notifications;""", tuplas=True).stdout.strip().split('\n')[-1]
ok('la campanita: el sanador ve SOLO sus notificaciones (su select no filtra)',
   vistas_por_san == '1', f'vio {vistas_por_san} de 2')

# El POST de «marcar todas leídas»: `.eq('leida', false)` a secas.
psql(f"""set role authenticated;
set request.jwt.claim.sub = '{SAN}';
update public.notifications set leida = true where leida = false;""")
ajena = psql(f"select leida from public.notifications where practitioner_id = '{OTRO}';",
             tuplas=True).stdout.strip()
ok('la campanita: «marcar todas leídas» no toca las del otro sanador',
   ajena == 'f', f'la del otro quedó leida = {ajena or "sin fila"}')
propia = psql(f"select leida from public.notifications where practitioner_id = '{SAN}';",
              tuplas=True).stdout.strip()
ok('la campanita: «marcar todas leídas» sí marca las propias', propia == 't',
   f'la propia quedó leida = {propia or "sin fila"}')

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LA RLS DE TODAS LAS TABLAS, EJERCITADA — no leída                       ║
# ╚══════════════════════════════════════════════════════════════════════════╝
#
# POR QUÉ ESTÁ ACÁ. Medido el 17 de noviembre de 2026: de las 99 lentes de
# MCD, las únicas que ejercitaban una política eran las tres de la campanita,
# veinte líneas más arriba. Las otras once tablas tenían su `create policy`
# escrita y NUNCA ejecutada. Y del lado de TCD lo mismo: una sola tabla
# —`profiles`— con su aislamiento ejercitado, de 42 que el navegador toca.
#
# LA TRAMPA QUE ESTO MIDE Y QUE NINGUNA LECTURA DEL `.sql` PUEDE VER: una
# política sobre una tabla con la RLS APAGADA no hace nada. PostgreSQL la
# acepta, la guarda, `pg_policies` la muestra, y no filtra ni una fila. No hay
# error y no hay aviso. Es la misma forma de todo lo que este repo encontró
# entre el 13 y el 17 de noviembre: la lente verde porque no pudo preguntar.
#
# Y por eso esto no lee el `.sql`: le pregunta al CATÁLOGO del PostgreSQL que
# ya está levantado acá arriba, con las seis migraciones corridas, y después
# se sienta en la silla de un sanador y mira. Dos sanadores, una fila de cada
# uno, y la sesión del primero:
#
#   · VE exactamente la suya, nunca la del otro.
#   · NO PUEDE escribir una fila a nombre del otro (el `with check`).
#   · NO PUEDE tocar la fila del otro (el `using` del update).
#
# Lo que se cayó al medirlo, antes de escribir nada: las doce tablas tienen la
# RLS encendida y once tienen su política bien acotada. La premisa de que
# faltara alguna era falsa. Lo que faltaba era quien lo mire.
print()
print('── la RLS de cada tabla, preguntada al catálogo y ejercitada ──')

# `ghl_connections` no tiene política A PROPÓSITO, y es correcto: sus seis
# usos pasan todos por el cliente `admin` (service role), que salta la RLS.
# Una política para `authenticated` ahí sería decorado. Queda declarada —con
# el motivo— y ATADA: si algún día aparece una, la línea sobra y la lente de
# abajo lo dice. Una excepción escondida es una tabla fuera de la medición
# para siempre; es lo que este repo ya se comió con la lista de pantallas
# protegidas del 14 de noviembre.
SOLO_SERVICE_ROLE = {
    'ghl_connections': 'sus seis usos pasan por el cliente admin (service '
                       'role), que salta la RLS: una política para '
                       'authenticated sería decorado',
}

# La columna que dice de quién es la fila.
DUENOS = ('practitioner_id',)

# La tabla sin columna de dueño, declarada: su política llega por un `exists`
# sobre otra tabla, así que el recorrido genérico no la puede sembrar y se
# ejercita a mano al final. Atada igual que las otras dos listas: el día que
# gane una columna de dueño, esta línea sobra y la lente lo dice.
SIN_DUENO = {
    'patient_protocols': 'su política llega por un exists sobre patients: se '
                         'ejercita a mano al final de este bloque',
}

_tablas_rls = [l.strip() for l in psql(
    "select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace "
    "where n.nspname = 'public' and c.relkind = 'r' and c.relrowsecurity "
    "order by 1;", tuplas=True).stdout.strip().split('\n') if l.strip()]
_todas = [l.strip() for l in psql(
    "select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace "
    "where n.nspname = 'public' and c.relkind = 'r' order by 1;",
    tuplas=True).stdout.strip().split('\n') if l.strip()]

# El canario primero: una lente que no encontró tablas se pone verde por no
# haber podido preguntar, que es peor que no tenerla.
ok('el catálogo contesta qué tablas hay', len(_todas) >= 10,
   f'solo {len(_todas)}: la lente no midió nada')

_sin_rls = sorted(set(_todas) - set(_tablas_rls))
ok('toda tabla de public tiene la RLS encendida', not _sin_rls,
   ', '.join(_sin_rls) + ' — sin RLS, la clave anónima que viaja en el bundle '
   'la lee entera')

_politicas = {}
for _l in psql("select tablename || '|' || count(*) from pg_policies "
               "where schemaname = 'public' group by tablename;",
               tuplas=True).stdout.split('\n'):
    if '|' in _l:
        _n, _c = _l.strip().split('|')
        _politicas[_n] = int(_c)
_inertes = sorted(t for t in _politicas if t not in _tablas_rls)
ok('ninguna política vive sobre una tabla con la RLS apagada', not _inertes,
   ', '.join(_inertes) + ' — PostgreSQL la acepta y no filtra NADA')
_sin_politica = sorted(t for t in _tablas_rls
                       if not _politicas.get(t) and t not in SOLO_SERVICE_ROLE)
ok('toda tabla con RLS tiene al menos una política, o está declarada',
   not _sin_politica,
   ', '.join(_sin_politica) + ' — con RLS y sin política la tabla queda '
   'CERRADA en silencio: la pantalla sale vacía y no hay error')
_sobran = sorted(t for t in SOLO_SERVICE_ROLE if _politicas.get(t))
ok('ninguna excepción de service role sigue declarada ya teniendo política',
   not _sobran, ', '.join(_sobran) + ' — ya tiene política: sacarla de '
   'SOLO_SERVICE_ROLE para que su aislamiento se ejercite')
# `_cols` se arma más abajo, así que esta atadura se evalúa al final, con
# las dos cosas que harían sobrar la declaración: que la tabla haya ganado
# una columna de dueño —y entonces el recorrido genérico ya la puede medir— o
# que haya dejado de tener RLS.
_ATAR_SIN_DUENO = True


def _como(_sanador, _sql):
    """La misma consulta, sentado en la silla de ese sanador."""
    return psql(f"set role authenticated;\n"
                f"set request.jwt.claim.sub = '{_sanador}';\n{_sql}", tuplas=True)


# El andamiaje de la fila: los obligatorios sin valor por defecto, rellenados
# por tipo. Si una tabla no se puede sembrar, se dice SIN MEDIR y se cuenta:
# no se da por buena.
_cols = {}
for _l in psql("select table_name || '|' || column_name || '|' || data_type || '|' "
               "|| is_nullable || '|' || coalesce(column_default, '-') "
               "from information_schema.columns where table_schema = 'public' "
               "order by table_name, ordinal_position;", tuplas=True).stdout.split('\n'):
    if _l.count('|') == 4:
        _t, _c, _ty, _nl, _de = _l.strip().split('|')
        _cols.setdefault(_t, []).append((_c, _ty, _nl == 'YES', _de))


# Las claves ajenas: una columna obligatoria que apunta a otra tabla no se
# puede rellenar con un uuid inventado —la base lo rechaza y la tabla queda
# sin medir, que fue lo que pasó con `patient_notes` al primer intento—. Se
# busca una fila de la tabla apuntada, y si esa tabla tiene dueño, LA DEL
# MISMO sanador: una nota del sanador A sobre un paciente de B no es una fila
# que la app pueda crear, y sembrarla así mediría una situación imposible.
_FK = {}
for _l in psql("""select c.relname || '|' || a.attname || '|' || f.relname || '|' || af.attname
  from pg_constraint k
  join pg_class c on c.oid = k.conrelid
  join pg_class f on f.oid = k.confrelid
  join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
  join pg_attribute a on a.attrelid = c.oid and a.attnum = k.conkey[1]
  join pg_attribute af on af.attrelid = f.oid and af.attnum = k.confkey[1]
  where k.contype = 'f' and array_length(k.conkey, 1) = 1;""",
               tuplas=True).stdout.split('\n'):
    if _l.count('|') == 3:
        _tc, _cc, _tf, _cf = _l.strip().split('|')
        _FK[(_tc, _cc)] = (_tf, _cf)


def _fila_de(_tabla, _col, _sanador):
    """Un valor que exista en la tabla apuntada, del mismo sanador si tiene."""
    _tiene_dueno = any(_c == 'practitioner_id' for _c, _, _, _ in _cols.get(_tabla, []))
    _donde = (f"where practitioner_id = '{_sanador}'" if _tiene_dueno
              else (f"where id = '{_sanador}'" if _tabla == 'practitioners' else ''))
    _r = psql(f'select {_col} from public.{_tabla} {_donde} limit 1;',
              tuplas=True).stdout.strip().split('\n')[-1].strip()
    return f"'{_r}'" if _r else None


def _relleno(_tipo):
    if 'uuid' in _tipo: return "'33333333-3333-3333-3333-333333333333'"
    if 'char' in _tipo or 'text' in _tipo: return "'x'"
    if 'int' in _tipo or 'numeric' in _tipo or 'double' in _tipo: return '1'
    if 'bool' in _tipo: return 'false'
    if 'timestamp' in _tipo or 'date' in _tipo: return 'now()'
    if 'json' in _tipo: return "'{}'::jsonb"
    if 'ARRAY' in _tipo: return "'{}'"
    return 'null'


# El paciente del SEGUNDO sanador, sembrado antes del recorrido: las tablas
# se recorren en orden alfabético, así que `patient_notes` llega antes que
# `patients`, y sin una fila ajena a la que apuntar quedaba SIN MEDIR.
psql(f"""insert into public.patients(practitioner_id, full_name)
  values ('{OTRO}', 'Paciente del otro sanador');""")

_ejercitadas, _sin_medir = [], []
for _t in _tablas_rls:
    if _t in SOLO_SERVICE_ROLE:
        continue
    _campos = _cols.get(_t, [])
    _nombres = [_c for _c, _, _, _ in _campos]
    _dueno = next((_d for _d in DUENOS if _d in _nombres),
                  'id' if _t == 'practitioners' else None)
    if not _dueno:
        if _t not in SIN_DUENO:
            _sin_medir.append(f'{_t} (sin columna de dueño y sin declarar en '
                              f'SIN_DUENO: su aislamiento no lo mide nadie)')
        continue
    if _t == 'practitioners':
        # Las dos filas ya existen: las crea el disparador de la primera
        # migración al nacer el usuario.
        _visto = _como(SAN, f"select count(*) || '/' || coalesce(max(id::text), '-') "
                            f'from public.{_t};').stdout.strip().split('\n')[-1]
        ok(f'{_t}: el sanador ve solo su ficha, y es la suya',
           _visto == f'1/{SAN}', f'vio «{_visto}»')
        _ejercitadas.append(_t)
        continue
    _obligatorios = [(_c, _ty) for _c, _ty, _nul, _de in _campos
                     if not _nul and _de == '-' and _c != _dueno]
    _falla_siembra = None
    for _quien in (SAN, OTRO):
        _cs = [_dueno] + [_c for _c, _ in _obligatorios]
        _vs = [f"'{_quien}'"]
        for _c, _ty in _obligatorios:
            if (_t, _c) in _FK:
                _tf, _cf = _FK[(_t, _c)]
                _v = _fila_de(_tf, _cf, _quien)
                if not _v:
                    _falla_siembra = (f'{_c} apunta a {_tf}.{_cf} y no hay '
                                      f'fila de ese sanador para apuntar')
                    break
                _vs.append(_v)
            else:
                _vs.append(_relleno(_ty))
        if _falla_siembra:
            break
        # `on conflict do nothing`: varias tablas ya tienen la fila de este
        # sanador sembrada más arriba —`agent_config` la tiene por clave
        # primaria—, y un choque de clave no es un fallo de la RLS.
        _r = psql(f"insert into public.{_t}({', '.join(_cs)}) "
                  f"values ({', '.join(_vs)}) on conflict do nothing;")
        if _r.returncode != 0:
            _falla_siembra = (_r.stderr or '').strip().split('\n')[0][-110:]
            break
    if _falla_siembra:
        _sin_medir.append(f'{_t} (no se pudo sembrar: {_falla_siembra})')
        continue
    # Se cuentan DUEÑOS distintos, no filas: varias de estas tablas ya
    # tenían filas del primer sanador sembradas más arriba, y contar filas
    # daba «2 de 2» con la política funcionando perfecto. El invariante es
    # que el sanador vea un solo dueño, y que ese dueño sea él.
    # `max(uuid)` NO EXISTE en PostgreSQL —el primer intento de esta lente
    # dejó ocho afirmaciones leyendo «SET», que es lo que imprime psql cuando
    # la consulta de abajo revienta y lo único que quedó son los dos `set`—.
    # Por eso el casteo a texto va ADENTRO del agregado.
    _vistos = _como(SAN, f'select count(distinct {_dueno}) || \'/\' || '
                         f'coalesce(max({_dueno}::text), \'-\') '
                         f'from public.{_t};').stdout.strip().split('\n')[-1]
    ok(f'{_t}: el sanador ve la suya y NO la del otro', _vistos == f'1/{SAN}',
       f'vio dueños «{_vistos}», esperaba «1/{SAN}» — su política no acota '
       f'por {_dueno}')
    _cs = [_dueno] + [_c for _c, _ in _obligatorios]
    _vs = [f"'{OTRO}'"] + [_relleno(_ty) for _, _ty in _obligatorios]
    _escribio = _como(SAN, f"insert into public.{_t}({', '.join(_cs)}) "
                           f"values ({', '.join(_vs)});")
    ok(f'{_t}: el sanador NO puede escribir una fila a nombre del otro',
       _escribio.returncode != 0,
       'el insert ajeno pasó: su política no tiene `with check` que lo frene')
    _tocadas = _como(SAN, f"with t as (update public.{_t} set {_dueno} = {_dueno} "
                          f"where {_dueno} = '{OTRO}' returning 1) "
                          f'select count(*) from t;').stdout.strip().split('\n')[-1]
    ok(f'{_t}: el sanador NO puede tocar la fila del otro', _tocadas == '0',
       f'tocó {_tocadas} filas ajenas')
    _ejercitadas.append(_t)

# `patient_protocols` no tiene columna de dueño: su política llega por un
# `exists` sobre `patients`. Se ejercita a mano, que es la única manera.
_pac_otro = psql(f"""insert into public.patients(practitioner_id, full_name)
  values ('{OTRO}', 'Paciente del otro') returning id;""", tuplas=True).stdout.strip().split('\n')
_pac_otro = [l for l in _pac_otro if '-' in l]
_prot = psql("select id from public.protocols limit 1;", tuplas=True).stdout.strip()
if _pac_otro and _prot:
    psql(f"""insert into public.patient_protocols(patient_id, protocol_id)
      values ('{pac}', '{_prot}'), ('{_pac_otro[0]}', '{_prot}');""")
    _visto = _como(SAN, 'select count(*) from public.patient_protocols;'
                   ).stdout.strip().split('\n')[-1]
    ok('patient_protocols: el sanador ve el del suyo y NO el del paciente ajeno',
       _visto == '1', f'vio {_visto} de 2 — su `exists` sobre patients no acota')
    _ejercitadas.append('patient_protocols')
else:
    _sin_medir.append('patient_protocols (no se pudo sembrar el par de pacientes)')

_sobran_dueno = sorted(
    _t2 for _t2 in SIN_DUENO
    if _t2 not in _tablas_rls
    or any(_c2 in DUENOS for _c2, _, _, _ in _cols.get(_t2, [])))
ok('ninguna tabla declarada «sin dueño» ya tiene dueño o perdió la RLS',
   not _sobran_dueno,
   ', '.join(_sobran_dueno) + ' — la línea de SIN_DUENO sobra: sacarla para '
   'que el recorrido genérico la mida')
ok('toda tabla con política quedó ejercitada, y lo que no se pudo está dicho',
   not _sin_medir, '; '.join(_sin_medir))
print(f'  {len(_ejercitadas)} de las {len(_tablas_rls)} tablas con RLS, '
      f'ejercitadas con dos sesiones distintas')

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LA PUERTA QUE RODEA LA RLS ENTERA: QUIÉN PUEDE EJECUTAR LAS FUNCIONES    ║
# ╚══════════════════════════════════════════════════════════════════════════╝
#
# Medido en TCD el 17 de noviembre de 2026 a las 23:25, y preguntado acá el
# mismo día porque es la única pregunta que la RLS deja abierta:
#
#     UNA FUNCIÓN `SECURITY DEFINER` CORRE CON LOS PERMISOS DE SU DUEÑO, ASÍ
#     QUE NO LE APLICA LA RLS. Y EL PERMISO DE FÁBRICA DE PostgreSQL ES
#     `EXECUTE` PARA `PUBLIC`: nadie tiene que concederlo, viene puesto.
#     PostgREST publica toda función de `public` como
#     `/rest/v1/rpc/<nombre>`, así que con la clave anónima que viaja en el
#     bundle cualquiera la llama.
#
# En TCD eso eran 25 funciones que no preguntaban quién llamaba: una entregaba
# la semana de otro cliente que la RLS acababa de negar, y otra sumaba crédito
# comprado sin ninguna sesión.
#
# ACÁ LA PREMISA ES LA BUENA, y por eso esta lente es preventiva: las dos
# únicas `SECURITY DEFINER` de MCD son DE DISPARADOR, y a esas no las llama
# PostgREST sino la tabla. No hay puerta. Lo que esta lente cuida es el día
# que alguien escriba la primera función de `public` y la deje abierta, que es
# lo que pasó en TCD sin que nadie lo viera en nueve meses.
print()
print('── quién puede ejecutar lo que pasa por encima de la RLS ──')

_PERDON_FN: dict[str, str] = {}

_defs = psql(
    "select p.proname || '|' || "
    "  (case when p.prosrc ~* "
    "        '(auth\\.uid|auth\\.role|NOT_AUTHORIZED|practitioner_id\\s*=)' "
    "   then 'pregunta' else 'NO' end) "
    "from pg_proc p join pg_namespace n on n.oid = p.pronamespace "
    "where n.nspname = 'public' and p.prosecdef "
    "  and p.prorettype <> 'trigger'::regtype "
    "  and (has_function_privilege('anon', p.oid, 'EXECUTE') "
    "       or has_function_privilege('authenticated', p.oid, 'EXECUTE'));",
    tuplas=True).stdout.strip()
_vivas = [l.strip() for l in _defs.split('\n') if '|' in l]
_abiertas = sorted(l.split('|')[0] for l in _vivas if l.split('|')[1] == 'NO'
                   and l.split('|')[0] not in _PERDON_FN)
ok('ninguna SECURITY DEFINER alcanzable por anon o authenticated se saltea la '
   'RLS sin preguntar quién llama', not _abiertas,
   ', '.join(_abiertas) + ' — una SECURITY DEFINER corre como su dueño: la '
   'RLS no le aplica, y EXECUTE para PUBLIC viene de fábrica')

# Y EL DEFECTO, PUESTO A PROPÓSITO. Sin esto la afirmación de arriba es verde
# por no haber nada que mirar, que es exactamente el verde que este repo viene
# cazando desde el 13 de noviembre. Se crea una función abierta, se comprueba
# que la medición la ve, y se borra.
psql("create or replace function public.__canario_sin_guarda(p uuid) "
     "returns bigint language sql security definer as $x$ "
     "  select count(*) from public.patients where practitioner_id = p; $x$;")
_c = psql(
    "select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace "
    "where n.nspname = 'public' and p.prosecdef "
    "  and p.prorettype <> 'trigger'::regtype "
    "  and p.proname = '__canario_sin_guarda' "
    "  and not p.prosrc ~* '(auth\\.uid|auth\\.role|NOT_AUTHORIZED)' "
    "  and (has_function_privilege('anon', p.oid, 'EXECUTE') "
    "       or has_function_privilege('authenticated', p.oid, 'EXECUTE'));",
    tuplas=True).stdout.strip().split('\n')[-1]
ok('la medición de arriba VE una función abierta: el canario salió marcado',
   _c == '1', f'contó {_c} — la medición no puede ver el defecto, así que su '
   'verde no dice nada')
psql('drop function if exists public.__canario_sin_guarda(uuid);')

_quedo = psql("select count(*) from pg_proc p join pg_namespace n "
              "on n.oid = p.pronamespace where n.nspname = 'public' "
              "and p.proname = '__canario_sin_guarda';",
              tuplas=True).stdout.strip().split('\n')[-1]
ok('y el canario no se quedó en la base', _quedo == '0', f'quedaron {_quedo}')

_sobran_fn = sorted(f for f in _PERDON_FN
                    if f not in [l.split('|')[0] for l in _vivas])
ok('ninguna línea del perdón de funciones sobra', not _sobran_fn,
   ', '.join(_sobran_fn))
print(f'  {len(_vivas)} funciones SECURITY DEFINER alcanzables en public '
      f'(las de disparador no cuentan: no las llama PostgREST)')

print()

# ── 8 · LOS COMPROBANTES: DE QUIÉN ES CADA ARCHIVO ──────────────────────────
#
# Medido el 18 de noviembre de 2026. Las lentes de arriba miden las TABLAS.
# `storage.objects` —donde vive el comprobante de cada cobro, que es una
# captura de la transferencia de un paciente— no lo ejercitaba ninguna de las
# 99 miradas de MCD: la cubeta se medía solo por existir.
#
# Y storage tiene una trampa que las tablas no tienen:
#
#   · `storage.objects` nace con la RLS ENCENDIDA en Supabase, y en este
#     andamiaje nace apagada. Sin encenderla, las dos políticas del
#     comprobante no filtran nada y cualquier afirmación sale verde sin haber
#     probado ninguna.
#   · Una política sin `to <rol>` vale para TODOS los roles, `anon` incluido
#     —la llave publicable que viaja en el navegador—. PostgreSQL la guarda
#     como `{public}` y no avisa. Las dos de MCD están así; lo que las cierra
#     hoy es que su condición compara con `auth.uid()`, que sin sesión es
#     null. O sea: cerradas por la condición, no por la puerta.
#
# LA PREMISA SE CAYÓ DEL LADO BUENO: en TCD, el mismo día, dos políticas con
# la misma forma SÍ dejaban leer sin sesión, porque su condición no preguntaba
# de quién era la carpeta. Acá sí pregunta. Así que esto no arregla: vigila.
psql('alter table storage.objects enable row level security;')
psql('grant select, insert, update, delete on storage.objects '
     'to anon, authenticated;')

_priv = psql("select public from storage.buckets where id = 'comprobantes';",
             tuplas=True).stdout.strip().split('\n')[-1].strip()
ok('la cubeta de los comprobantes es privada', _priv == 'f',
   f'devolvió «{_priv}» — un comprobante es la transferencia de un paciente')

# El comprobante de cada uno, en su carpeta, como lo escribe
# `src/app/api/cobros/route.ts`: `${user.id}/${Date.now()}.png`.
psql(f"""insert into storage.objects (bucket_id, name, owner) values
  ('comprobantes', '{SAN}/1700000000.png', '{SAN}'),
  ('comprobantes', '{OTRO}/1700000001.png', '{OTRO}');""")


def _ve_archivos(_quien):
    """Cuántos comprobantes ve esa silla. `-` es sin sesión."""
    _sql = "select count(*) from storage.objects where bucket_id = 'comprobantes';"
    if _quien == '-':
        _r = psql(f"set role anon;\n{_sql}", tuplas=True)
    else:
        _r = _como(_quien, _sql)
    return _r.stdout.strip().split('\n')[-1].strip()


_n = _ve_archivos('-')
ok('sin ninguna sesión no se lista ni un comprobante', _n == '0',
   f'vio «{_n}» — con la llave publicable del navegador')
_n = _ve_archivos(SAN)
ok('cada sanador ve su comprobante y no el del otro', _n == '1', f'vio «{_n}»')

# Y escribir: en su carpeta sí, en la de al lado no.
psql(f"""set role authenticated;
set request.jwt.claim.sub = '{OTRO}';
insert into storage.objects (bucket_id, name)
  values ('comprobantes', '{SAN}/pisado.png');""")
_n = psql(f"select count(*) from storage.objects where name = '{SAN}/pisado.png';",
          tuplas=True).stdout.strip().split('\n')[-1].strip()
ok('un sanador no sube un comprobante a la carpeta de otro', _n == '0',
   f'entraron «{_n}»')
psql(f"""set role authenticated;
set request.jwt.claim.sub = '{OTRO}';
insert into storage.objects (bucket_id, name)
  values ('comprobantes', '{OTRO}/1700000002.png');""")
_n = psql(f"select count(*) from storage.objects where name = '{OTRO}/1700000002.png';",
          tuplas=True).stdout.strip().split('\n')[-1].strip()
ok('y sube el suyo, que es lo que hace /api/cobros', _n == '1',
   f'entraron «{_n}» — la lente no puede dar verde rompiendo la app')

# ── EL CANARIO: ¿esta medición VE una política abierta? ─────────────────────
#
# Lo mismo que el canario de las funciones de más abajo: se mete a propósito
# una política que deja leer a cualquiera, se comprueba que la medición la ve,
# y se saca. Sin esto, los cuatro verdes de arriba no dicen nada.
_todos = psql("select count(*) from storage.objects "
              "where bucket_id = 'comprobantes';",
              tuplas=True).stdout.strip().split('\n')[-1].strip()
psql("""create policy "__canario_abierto" on storage.objects
  for select using (bucket_id = 'comprobantes');""")
_n = _ve_archivos('-')
ok('la medición VE una política abierta: el canario dejó leer sin sesión',
   _n == _todos and _todos != '0',
   f'vio «{_n}» de «{_todos}» — tendría que ver TODOS los comprobantes, así '
   'que su verde de arriba no dice nada')
psql('drop policy if exists "__canario_abierto" on storage.objects;')
_n = _ve_archivos('-')
ok('y el canario no se quedó en la base', _n == '0', f'vio «{_n}»')

print()
print(f'  {len(pedidas)} pares tabla.columna medidos contra la base real; '
      f'{len(faltantes)} sin respaldo en el esquema')
sys.exit(1 if fallas else 0)
