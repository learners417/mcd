#!/usr/bin/env python3
"""¿Ve la batería la TABLA que falta, y no solo la columna?

Por qué existe esta prueba. `prueba-el-esquema-real.py` dice medir que «toda
columna que el código nombra existe en el esquema», y su recorrido empezaba
con:

    if tabla in vistas or tabla not in objetos: continue

Una tabla que no existe no se medía: se salteaba. Medido el 17 de noviembre de
2026: de las 14 tablas que el código nombra, SEIS no estaban en el esquema y
la lente daba VERDE. Tres eran de MCD y las tres fallaban en silencio en
producción —el Guardar del Asistente, la nota del paciente y la campanita—.
Es la tercera vez en este repo que la ausencia es el defecto, así que la lente
nueva se prueba contra su propio fallo y queda probada por escrito.

Cómo se prueba: se copia el repo a un temporal, se le pone el defecto ahí y se
corre la prueba del esquema CONTRA ESA COPIA. Nada del disco de verdad se
toca. Cada defecto dice qué lente tiene que ponerse roja; si se pone verde, o
si se pone roja otra que no es, esta prueba falla.

Corre: python3 scripts/probar-que-la-lente-de-la-tabla-ve-el-defecto.py
"""
import os, re, shutil, subprocess, sys, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fallas = 0


def copiar():
    d = tempfile.mkdtemp(prefix='lente-tabla-')
    for sub in ('scripts', 'supabase', 'src'):
        shutil.copytree(os.path.join(RAIZ, sub), os.path.join(d, sub))
    # El temporal nace en 0700 y las migraciones las lee `psql` COMO POSTGRES,
    # no como root: sin este permiso todas las lentes se ponen rojas por no
    # poder abrir el archivo, y este arnés daba por «vista» cualquier lente
    # que le pidieras. Fue el primer fallo de este arnés, el 17 de noviembre.
    subprocess.run(['chmod', '-R', 'a+rX', d], capture_output=True)
    return d


def correr(copia):
    r = subprocess.run([sys.executable, os.path.join(copia, 'scripts/prueba-el-esquema-real.py')],
                       capture_output=True, text=True)
    sal = (r.stdout or '') + (r.stderr or '')
    if 'sin PostgreSQL local' in sal:
        return None, sal
    rojas = [l.strip().lstrip('✗ ').split(' — ')[0] for l in sal.splitlines() if '✗' in l]
    return rojas, sal


def caso(nombre, tocar, espera_roja, espera_verde=()):
    """`tocar(copia)` pone el defecto. `espera_roja` es el texto que tiene que
    aparecer en alguna lente roja; `espera_verde`, el que NO puede aparecer."""
    global fallas
    copia = copiar()
    try:
        tocar(copia)
        rojas, sal = correr(copia)
        if rojas is None:
            print(f'  ⚠ SIN MEDIR ({nombre}): no hay PostgreSQL local')
            return
        hay = [r for r in rojas if espera_roja in r]
        mal = [r for r in rojas for v in espera_verde if v in r]
        # La base que no levanta pone rojas TODAS las lentes, y con ellas
        # cualquiera que le pidas: este arnés daba ocho defectos por «vistos»
        # con la base muerta —el temporal nacía en 0700 y `psql` corre como
        # postgres—. Así que antes de creerle a una lente roja se mira el
        # canario: si la base no contestó, esta corrida no midió nada.
        # No se cuentan las rojas: borrar la migración de las tres tablas pone
        # nueve en rojo con razón, y contar las confundiría con esto.
        canario = [r for r in rojas
                   if 'la base contesta' in r or 'corre contra PostgreSQL' in r]
        if canario:
            fallas += 1
            print(f'  ✗ {nombre} → la base no levantó ({canario[0][:60]}): '
                  f'esta corrida no midió el defecto')
            return
        if hay and not mal:
            print(f'  ✓ {nombre} → roja: «{hay[0][:80]}»')
        else:
            fallas += 1
            if not hay:
                print(f'  ✗ {nombre} → la lente NO se puso roja. '
                      f'Rojas: {rojas if rojas else "ninguna"}')
            else:
                print(f'  ✗ {nombre} → se puso roja la que no era: {mal}')
    finally:
        shutil.rmtree(copia, ignore_errors=True)


def editar(copia, rel, viejo, nuevo):
    p = os.path.join(copia, rel)
    t = open(p, encoding='utf-8').read()
    assert viejo in t, f'no encontré «{viejo[:40]}» en {rel}'
    open(p, 'w', encoding='utf-8').write(t.replace(viejo, nuevo, 1))


print('LA LENTE DE LA TABLA, CONTRA SU PROPIO FALLO')
print()

# 1 · El defecto de verdad: la migración de las tres tablas, borrada.
caso('la migración de las tres tablas, borrada',
     lambda c: os.remove(os.path.join(c, 'supabase/migrations/20261117_las_tres_tablas_que_el_codigo_pedia.sql')),
     'toda tabla que el código nombra existe')

# 2 · Una tabla inventada en una consulta: el caso que antes se salteaba.
caso('una consulta nombra una tabla que no existe',
     lambda c: editar(c, 'src/app/api/notificaciones/route.ts',
                      ".from('notifications')", ".from('notificaciones_viejas')"),
     'toda tabla que el código nombra existe')

# 3 · La cubeta de storage, inventada.
caso('el upload nombra una cubeta que no existe',
     lambda c: editar(c, 'src/app/api/cobros/route.ts',
                      ".from('comprobantes')", ".from('recibos')"),
     'toda cubeta de storage que el código nombra existe')

# 4 · La RLS de la campanita, apagada: el sanador vería las de todos.
caso('`notifications` sin RLS',
     lambda c: editar(c, 'supabase/migrations/20261117_las_tres_tablas_que_el_codigo_pedia.sql',
                      'alter table public.notifications  enable row level security;',
                      '-- alter table public.notifications enable row level security;'),
     'el sanador ve SOLO sus notificaciones')

# 5 · La política de la campanita, sin dueño: ve lo suyo pero marca las de todos.
caso('la política de `notifications` sin filtro de dueño',
     lambda c: editar(c, 'supabase/migrations/20261117_las_tres_tablas_que_el_codigo_pedia.sql',
                      '''create policy "own notifications" on public.notifications
  for all using (auth.uid() = practitioner_id) with check (auth.uid() = practitioner_id);''',
                      '''create policy "own notifications" on public.notifications
  for all using (true) with check (true);'''),
     'no toca las del otro sanador')

# 6 · `agent_config` sin `practitioner_id` de clave primaria: el segundo
#     Guardar inserta otra fila y el `maybeSingle()` de la pantalla revienta.
caso('`agent_config` con `practitioner_id` que no es clave primaria',
     lambda c: editar(c, 'supabase/migrations/20261117_las_tres_tablas_que_el_codigo_pedia.sql',
                      'practitioner_id uuid primary key references public.practitioners(id) on delete cascade,',
                      'id uuid primary key default gen_random_uuid(),\n'
                      '  practitioner_id uuid references public.practitioners(id) on delete cascade,'),
     'el Guardar corre')

# 7 · La lista de perdón, con una entrada que nadie nombra.
caso('AJENAS perdona una tabla que ninguna consulta nombra',
     lambda c: editar(c, 'scripts/prueba-el-esquema-real.py',
                      "AJENAS = {", "AJENAS = {\n    'tabla_que_nadie_nombra': 'quedó de un borrado',"),
     'ninguna excepción de AJENAS es inalcanzable')

# 8 · La lista de perdón, con una entrada que YA existe en el esquema.
caso('AJENAS perdona una tabla que sí existe',
     lambda c: editar(c, 'scripts/prueba-el-esquema-real.py',
                      "AJENAS = {", "AJENAS = {\n    'patients': 'esto ya no es cierto',"),
     'ninguna excepción de AJENAS es inalcanzable')

print()
if fallas:
    print(f'{fallas} de 8 defectos no los vio nadie')
    sys.exit(1)
print('los 8 defectos puestos se vieron: la lente de la tabla no está ciega')
