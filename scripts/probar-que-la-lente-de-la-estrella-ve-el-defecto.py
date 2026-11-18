#!/usr/bin/env python3
"""¿Ve la lente el CAMPO que el código lee por nombre y la base no tiene?

Por qué existe este arnés. `prueba-lo-que-trae-la-estrella.py` nació el 18 de
noviembre de 2026 por un defecto vivo: el Tablero leía ocho campos de la vista
`mis_numeros` y la vista tenía siete. El octavo, `roi_mes`, era la condición
del cartel «Tu inversión en MiClínica se pagó N×», así que esa rama no se
dibujó nunca desde el 8 de julio —y ninguna de las 74 lentes de MCD lo veía,
porque la otra lente del esquema saltea las vistas y saltea el `select('*')`.

Una lente nueva que nunca se vio roja no es una lente: es un verde más. Así
que acá se le ponen los defectos de a uno y se exige que se ponga roja LA
NOMBRADA. Dos de los nueve son al revés —el canario—: un cambio que NO es un
defecto tiene que dejarla verde, porque una lente que se pone roja con todo
tampoco mide nada.

Cómo se prueba: se copia el repo a un temporal, el defecto se pone ahí y la
lente corre CONTRA ESA COPIA. Nada del disco de verdad se toca.

Corre: python3 scripts/probar-que-la-lente-de-la-estrella-ve-el-defecto.py
"""
import os, shutil, subprocess, sys, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LENTE = 'scripts/prueba-lo-que-trae-la-estrella.py'
fallas = 0


def copiar():
    d = tempfile.mkdtemp(prefix='lente-estrella-')
    for sub in ('scripts', 'supabase', 'src'):
        shutil.copytree(os.path.join(RAIZ, sub), os.path.join(d, sub))
    # El temporal nace en 0700 y las migraciones las lee `psql` COMO POSTGRES.
    # Sin este permiso TODAS las lentes se ponen rojas por no poder abrir el
    # archivo, y el arnés daría por «visto» cualquier defecto que le pidieras.
    # Es el fallo que ya se comió el arnés de la tabla el 17 de noviembre.
    subprocess.run(['chmod', '-R', 'a+rX', d], capture_output=True)
    return d


def correr(copia):
    r = subprocess.run([sys.executable, os.path.join(copia, LENTE)],
                       capture_output=True, text=True)
    sal = (r.stdout or '') + (r.stderr or '')
    if 'sin PostgreSQL local' in sal:
        return None, sal
    return [l.strip().lstrip('✗ ').split(' — ')[0] for l in sal.splitlines() if '✗' in l], sal


def caso(nombre, tocar, espera_roja, espera_verde=()):
    global fallas
    copia = copiar()
    try:
        tocar(copia)
        rojas, sal = correr(copia)
        if rojas is None:
            print(f'  ⚠ SIN MEDIR ({nombre}): no hay PostgreSQL local')
            return
        # El canario primero: con la base muerta se ponen rojas todas, y con
        # ellas cualquiera que le pidas. Una corrida así no midió nada.
        canario = [r for r in rojas
                   if 'la base contesta' in r or 'corre contra PostgreSQL' in r]
        if canario and 'corre contra PostgreSQL' not in espera_roja:
            fallas += 1
            print(f'  ✗ {nombre} → la base no levantó ({canario[0][:60]}): '
                  f'esta corrida no midió el defecto')
            return
        hay = [r for r in rojas if espera_roja in r]
        mal = [r for r in rojas for v in espera_verde if v in r]
        if hay and not mal:
            print(f'  ✓ {nombre} → roja: «{hay[0][:86]}»')
        else:
            fallas += 1
            if not hay:
                print(f'  ✗ {nombre} → la lente NO se puso roja. '
                      f'Rojas: {rojas if rojas else "ninguna"}')
            else:
                print(f'  ✗ {nombre} → se puso roja la que no era: {mal}')
    finally:
        shutil.rmtree(copia, ignore_errors=True)


def canario(nombre, tocar):
    """Al revés: esto NO es un defecto y la lente tiene que quedar en verde."""
    global fallas
    copia = copiar()
    try:
        tocar(copia)
        rojas, sal = correr(copia)
        if rojas is None:
            print(f'  ⚠ SIN MEDIR ({nombre}): no hay PostgreSQL local')
            return
        if not rojas:
            print(f'  ✓ {nombre} → sigue verde, como tiene que ser')
        else:
            fallas += 1
            print(f'  ✗ {nombre} → se puso roja sin defecto: {rojas[:3]}')
    finally:
        shutil.rmtree(copia, ignore_errors=True)


def editar(copia, rel, viejo, nuevo, veces=1):
    p = os.path.join(copia, rel)
    t = open(p, encoding='utf-8').read()
    assert viejo in t, f'no encontré «{viejo[:50]}» en {rel}'
    open(p, 'w', encoding='utf-8').write(t.replace(viejo, nuevo, veces))


VISTA = 'supabase/migrations/20261118_la_estrella_traia_un_numero_que_no_existia.sql'
TABLERO = 'src/app/(app)/dashboard/page.tsx'

print('LA LENTE DE LA ESTRELLA, CONTRA SU PROPIO FALLO')
print()

# 1 · EL DEFECTO DE VERDAD, el del 18 de noviembre: la migración que agrega
#     `roi_mes`, borrada. Es el estado exacto en que estaba el repo esta
#     mañana, y ninguna lente lo veía.
caso('la migración de roi_mes, borrada (el defecto vivo de hoy)',
     lambda c: os.remove(os.path.join(c, VISTA)),
     'mis_numeros.roi_mes')

# 2 · El mismo campo, pero sacado de adentro del `create view`: la vista
#     existe, trae siete columnas y el Tablero pide ocho.
caso('roi_mes sacado del create view',
     lambda c: editar(c, VISTA, 'as roi_mes', 'as roi_del_mes'),
     'mis_numeros.roi_mes')

# 3 · Un campo nuevo leído en la pantalla y que nadie creó: el caso de mañana,
#     cuando alguien agregue una tarjeta antes que su columna.
caso('el Tablero lee un campo que no existe',
     lambda c: editar(c, TABLERO, 'n?.pacientes_activos', 'n?.pacientes_del_mes'),
     'mis_numeros.pacientes_del_mes')

# 4 · El mismo caso en una TABLA y no en una vista: la lente no mira solo
#     `mis_numeros`.
caso('la pantalla de la marca lee una columna que no existe',
     lambda c: editar(c, 'src/app/(app)/marca/page.tsx', 'me?.specialty', 'me?.especialidad'),
     'practitioners.especialidad')

# 5 · La tabla entera inventada.
caso('un select(*) sobre una tabla que no existe',
     lambda c: editar(c, 'src/app/api/notificaciones/route.ts',
                      ".from('notifications')", ".from('avisos')"),
     'la tabla o vista «avisos»')

# 6 · LA PUERTA: la vista sin `security_invoker` corre con los permisos de su
#     dueño y se saltea el RLS de sus cuatro tablas base. Tienen que ponerse
#     rojas la del catálogo Y el ejercicio: sin sesión se ven las dos filas.
caso('la vista sin security_invoker (se saltea el RLS de sus tablas base)',
     lambda c: editar(c, VISTA, 'with (security_invoker = true) as', 'as', 2),
     'declara security_invoker')
caso('la vista sin security_invoker, visto desde la silla vacía',
     lambda c: editar(c, VISTA, 'with (security_invoker = true) as', 'as', 2),
     'sin sesion no se ve ninguna fila')

# 7 · La cuenta cambiada: la vista trae un roi_mes que no es el que el Tablero
#     ya calculaba a mano en la tarjeta «Retorno». Las dos copias de una
#     cuenta tienen que decir lo mismo, que es el motivo de esta migración.
caso('roi_mes con otra cuenta que la de la tarjeta Retorno',
     lambda c: editar(c, VISTA, '/ nullif(p.inversion_mensual, 0)',
                      '* nullif(p.inversion_mensual, 0)'),
     'la misma cuenta que la tarjeta')

# 8 · El aislamiento roto por abajo: la política de `practitioners` deja de
#     preguntar de quién es la fila. La vista no cambia una letra; lo que
#     cambia es cuántas filas base deja pasar, y A pasa a ver los números del
#     otro. Es el agujero que `security_invoker` existe para evitar, puesto
#     desde el otro lado.
#
#     Lo que se midió al escribirlo, y vale anotarlo: el primer intento rompió
#     la política de `patients` y la lente quedó VERDE con razón. La subconsulta
#     de la vista filtra `pa.practitioner_id = p.id`, y `p` ya viene acotada a
#     la fila del que consulta, así que abrir `patients` no cambia su cuenta.
#     La fila base que manda es la de `practitioners`.
caso('la política de practitioners sin dueño: A ve también los números de B',
     lambda c: editar(c, 'supabase/migrations/20260706_mcd_mvp.sql',
                      'create policy "own practitioner" on public.practitioners\n'
                      '  for all using (auth.uid() = id) with check (auth.uid() = id);',
                      'create policy "own practitioner" on public.practitioners\n'
                      '  for all using (true) with check (true);'),
     'el sanador A ve UNA fila en mis_numeros')

# 9 · EL CANARIO, y es el falso positivo que esta lente ya se comió una vez:
#     un archivo que ata DOS veces la misma variable a tablas distintas. Si el
#     tramo no se cortara en la segunda atadura, la lente pediría las columnas
#     de una tabla en la otra y se pondría roja sin defecto. Medido el 18 de
#     noviembre en el repo de TCD, donde `session_logs` y `hoja_de_ruta` atan
#     las dos a `data` en la misma pantalla.
def _dos_ataduras(c):
    editar(c, 'src/app/api/notificaciones/route.ts',
           ".select('*').order('created_at', { ascending: false }).limit(30)",
           ".select('*').order('created_at', { ascending: false }).limit(30)\n"
           "  const { data } = await supabase.from('practitioners').select('*')"
           ".eq('id', 'x').maybeSingle()\n"
           "  void data?.brand_name")


canario('dos ataduras de la misma variable a tablas distintas', _dos_ataduras)

# 10 · El otro canario: un método de JavaScript sobre el resultado no es una
#      columna. `n?.toFixed` o un `.map` no se piden a la base.
canario('un método de JavaScript sobre el resultado no es una columna',
        lambda c: editar(c, TABLERO, 'const sinPacientes =',
                         'const _m = String(n?.ingresos_mes ?? 0).toString()\n  '
                         'const sinPacientes ='))

print()
print(f'{"TODO EN VERDE" if fallas == 0 else str(fallas) + " EN ROJO"}')
sys.exit(0 if fallas == 0 else 1)
