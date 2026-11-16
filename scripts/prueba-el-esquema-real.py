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
PORT = '5434'
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
pedidas = {}
for base, _, fs in os.walk(os.path.join(RAIZ, 'src')):
    if 'node_modules' in base: continue
    for f in sorted(fs):
        if not f.endswith(('.ts', '.tsx')): continue
        ruta = os.path.join(base, f)
        src = sin_comentarios(open(ruta, encoding='utf-8', errors='replace').read())
        for m in re.finditer(r"\.from\(\s*['\"]([a-z_0-9]+)['\"]\s*\)", src):
            tabla = m.group(1)
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

print()
print(f'  {len(pedidas)} pares tabla.columna medidos contra la base real; '
      f'{len(faltantes)} sin respaldo en el esquema')
sys.exit(1 if fallas else 0)
