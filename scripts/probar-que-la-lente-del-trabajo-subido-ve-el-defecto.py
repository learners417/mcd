#!/usr/bin/env python3
"""
¿Y LA LENTE DEL TRABAJO SUBIDO, VE EL DEFECTO?

`scripts/prueba-el-trabajo-subido.py` dice medir que lo commiteado salió del
repo. Que esté en verde hoy no dice nada: dice que hoy el repo está al día.
La pregunta de atrás —la que este repo se hizo ya en seis cuerpos distintos—
es si, puesto el defecto, se pone ROJA.

Su defecto no es texto en un archivo, así que el arnés de la batería no le
sirve: lo que hay que ensuciar es el ESTADO DE GIT. Así que acá se arman
repos de verdad en una carpeta temporal —un `--bare` de origin y dos clones—
y se corre la lente contra cada uno. El repo de verdad no se toca nunca.

Los cinco ejercicios, y el que importa es el último:

  1 · todo subido                      → verde
  2 · un commit commiteado y sin subir  → ROJA (se pierde con el contenedor)
  3 · el ref local de origin viejo      → ROJA (es la que se cobró la
                                           despertada del 17 a las 15:30)
  4 · HEAD suelto en un commit sin subir → ROJA (así nace el contenedor)
  5 · el remoto que no contesta         → SIN MEDIR, y NO verde: una lente
                                          que se pone verde porque no pudo
                                          preguntar es peor que no tenerla

Correr con: python3 scripts/probar-que-la-lente-del-trabajo-subido-ve-el-defecto.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LENTE = os.path.join(RAIZ, 'scripts', 'prueba-el-trabajo-subido.py')

GIT = ('git', '-c', 'user.email=arnes@local', '-c', 'user.name=Arnes',
       '-c', 'commit.gpgsign=false', '-c', 'init.defaultBranch=main',
       '-c', 'protocol.file.allow=always')

fallas = []


def g(*args, cwd):
    r = subprocess.run(GIT + args, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'git {" ".join(args)} en {cwd}: {(r.stderr or r.stdout).strip()[:300]}')
    return (r.stdout or '').strip()


def commit(repo, archivo, texto):
    with open(os.path.join(repo, archivo), 'w', encoding='utf-8') as f:
        f.write(texto)
    g('add', archivo, cwd=repo)
    g('commit', '-m', f'{archivo}: {texto[:30]}', cwd=repo)


def correr(repo):
    """La lente sobre ese repo: (código, salida)."""
    r = subprocess.run([sys.executable, LENTE, repo], capture_output=True, text=True)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def afirmar(nombre, cond, detalle=''):
    if cond:
        print(f'  ✓ {nombre}')
    else:
        print(f'  ✗ {nombre} — {detalle}')
        fallas.append(f'{nombre}: {detalle}')


def main():
    if not os.path.exists(LENTE):
        print(f'  ✗ no está {LENTE}')
        return 1

    tmp = tempfile.mkdtemp(prefix='arnes-subido-')
    try:
        origen = os.path.join(tmp, 'origen.git')
        g('init', '--bare', origen, cwd=tmp)

        a = os.path.join(tmp, 'a')
        g('clone', origen, a, cwd=tmp)
        commit(a, 'uno.txt', 'el primero')
        g('push', '-u', 'origin', 'main', cwd=a)
        g('fetch', 'origin', cwd=a)

        # ── 1 · todo subido → verde ───────────────────────────────────────
        cod, sal = correr(a)
        afirmar('1 · con todo subido, la lente está verde', cod == 0,
                f'salió {cod}: {sal.strip()[-200:]}')
        afirmar('   y dice que el trabajo salió', 'todo lo commiteado salió del repo' in sal
                and '✓ todo lo commiteado' in sal, sal.strip()[-200:])

        # ── 2 · un commit sin subir → roja ────────────────────────────────
        commit(a, 'dos.txt', 'commiteado y sin subir')
        cod, sal = correr(a)
        afirmar('2 · con un commit sin subir, la lente se pone ROJA', cod == 1,
                f'salió {cod} con el commit sin subir: {sal.strip()[-250:]}')
        afirmar('   y nombra que se pierde con el contenedor',
                'SIN SUBIR' in sal and 'git push' in sal, sal.strip()[-200:])

        # ── 3 · el ref local viejo → roja ─────────────────────────────────
        # Otro clone sube; `a` no hace fetch. Su `origin/main` en disco queda
        # siendo la foto de antes, que es lo que `git status` lee.
        b = os.path.join(tmp, 'b')
        g('clone', origen, b, cwd=tmp)
        commit(b, 'tres.txt', 'subido desde otro clon')
        g('push', 'origin', 'main', cwd=b)

        c = os.path.join(tmp, 'c')
        g('clone', origen, c, cwd=tmp)          # al día, para aislar el defecto
        commit(c, 'cuatro.txt', 'y uno mas')
        g('push', 'origin', 'main', cwd=c)
        # `b` ahora tiene el ref viejo (le falta `cuatro.txt`) y su HEAD SÍ
        # está en el remoto: la única falla posible es el ref viejo.
        cod, sal = correr(b)
        afirmar('3 · con el ref local de origin viejo, la lente se pone ROJA', cod == 1,
                f'salió {cod} con el ref viejo: {sal.strip()[-250:]}')
        afirmar('   y la falla que nombra es la del ref viejo',
                'foto vieja' in sal and '✗ el ref local de origin' in sal,
                sal.strip()[-300:])
        # Y lo que el arnés encontró el 17 a las 15:30, que es por qué este
        # renglón existe: con el ref viejo, el commit del remoto NO ESTÁ en
        # este disco, así que la lente de arriba no tiene con qué comparar.
        # No se le puede creer al ref local —es la foto vieja—, así que se
        # exige que lo diga en vez de dar verde.
        afirmar('   y no da por bueno lo commiteado sin tener con qué comparar',
                '✓ todo lo commiteado salió del repo' not in sal
                and 'git fetch origin' in sal,
                sal.strip()[-300:])

        # ── 4 · HEAD suelto en un commit sin subir → roja ─────────────────
        # Así nace el contenedor de estas despertadas: clonado y en detached.
        d = os.path.join(tmp, 'd')
        g('clone', origen, d, cwd=tmp)
        g('checkout', '--detach', 'HEAD', cwd=d)
        commit(d, 'cinco.txt', 'commiteado en HEAD suelto')
        cod, sal = correr(d)
        afirmar('4 · con HEAD suelto en un commit sin subir, la lente se pone ROJA',
                cod == 1, f'salió {cod} con HEAD suelto: {sal.strip()[-250:]}')

        # ── 5 · el remoto que no contesta → SIN MEDIR, no verde ───────────
        e = os.path.join(tmp, 'e')
        g('clone', origen, e, cwd=tmp)
        commit(e, 'seis.txt', 'sin subir, y sin remoto a quien preguntar')
        g('remote', 'set-url', 'origin', os.path.join(tmp, 'no-existe.git'), cwd=e)
        cod, sal = correr(e)
        afirmar('5 · sin remoto que contestar, la lente dice SIN MEDIR',
                'SIN MEDIR' in sal, sal.strip()[-250:])
        afirmar('   y NO se pone verde por no haber podido preguntar',
                '✓ todo lo commiteado salió del repo' not in sal,
                'dio por bueno un commit sin subir porque el remoto no contestó: '
                + sal.strip()[-200:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if fallas:
        print(f'\n✗ {len(fallas)} defecto(s) que la lente del trabajo subido no ve:')
        for f in fallas:
            print(f'   · {f}')
        return 1
    print('\n✓ los cinco defectos del estado de git ponen roja (o sin medir) a la lente')
    return 0


if __name__ == '__main__':
    sys.exit(main())
