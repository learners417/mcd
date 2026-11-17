#!/usr/bin/env python3
"""
¿EL TRABAJO SALIÓ DEL REPO? — la lente que ninguna de las dos baterías tenía.

Las diez baterías de este repo miden el código. Ninguna medía LO ÚNICO que
hace que el código importe: que haya salido del contenedor. Y el contenedor
de estas despertadas es de usar y tirar: lo que queda commiteado y sin subir
se pierde cuando se recicla, y el mapa queda con una fila «cerrado · hash»
apuntando a un commit que nadie tiene.

MEDIDO EL 17 DE NOVIEMBRE DE 2026, y en carne propia, que es por qué existe:
esta despertada leyó `origin/main` de MCD, lo vio nueve commits atrás y dio
por perdido el trabajo de tres despertadas. Era falso. El `git fetch` había
quedado rechazado, así que `refs/remotes/origin/main` era un ref VIEJO: una
foto del remoto de ayer, guardada en disco, que `git rev-parse` y
`git status` leen sin avisar que es vieja. El remoto de verdad —`git
ls-remote`, que pregunta por la red— estaba al día.

O sea que el ref local de origin miente en las dos direcciones, y las dos
cuestan:

  · atrás, como acá: da por perdido trabajo que está subido, y la despertada
    gasta el turno «recuperándolo»;
  · adelante: si un `git push` falla y el ref ya quedó movido, da por subido
    trabajo que no salió, y eso sí se pierde de verdad.

Por eso esta lente NO le cree al ref local. Pregunta por la red con
`git ls-remote`, que es la única fuente que no envejece, y mide tres cosas:

  1 · todo commit alcanzable desde HEAD está en alguna rama del remoto;
  2 · el ref local de origin coincide con el remoto de verdad (si está
      viejo, cualquier lente que lo lea mide una foto de ayer);
  3 · y si el remoto no contestó, esta corrida NO MIDIÓ NADA, y lo dice.
      El canario es el mismo que la base de datos del bloque 10: una lente
      que se pone verde porque no pudo preguntar es peor que no tenerla.

Se corre antes de commitear, que es cuando HEAD tiene que estar en el
remoto. Después de commitear y antes de subir se pone roja a propósito: eso
es lo que mide.

Correr con: python3 scripts/prueba-el-trabajo-subido.py [carpeta]
Código de salida: 0 en verde (o sin medir), 1 con una falla.
"""
import os
import subprocess
import sys

RAIZ = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))

# Lo que tarda en contestar el remoto antes de darlo por no contestado. Sin
# esto, una red lenta cuelga la batería entera.
ESPERA = 45

fallas = 0


def check(nombre, ok, detalle=''):
    global fallas
    print(('  ✓ ' if ok else '  ✗ ') + nombre + (f' — {detalle}' if detalle and not ok else ''))
    if not ok:
        fallas += 1


def git(*args, cwd=RAIZ, espera=None):
    """git, con su salida y su código. Nunca revienta: devuelve el código."""
    try:
        r = subprocess.run(('git',) + args, cwd=cwd, capture_output=True,
                           text=True, timeout=espera)
        return r.returncode, (r.stdout or '').strip(), (r.stderr or '').strip()
    except subprocess.TimeoutExpired:
        return 124, '', f'el remoto no contestó en {espera}s'
    except OSError as e:
        return 127, '', str(e)


def main():
    cod, _, err = git('rev-parse', '--git-dir')
    if cod != 0:
        print(f'  ⚠ SIN MEDIR: {RAIZ} no es un repo de git — {err[:120]}')
        return 0

    cod, cabeza, err = git('rev-parse', 'HEAD')
    if cod != 0:
        print(f'  ⚠ SIN MEDIR: el repo no tiene ningún commit todavía — {err[:120]}')
        return 0

    # ── EL CANARIO ────────────────────────────────────────────────────────
    # El remoto de VERDAD, por la red. No `origin/main`, que es una foto en
    # disco y puede ser de ayer: eso es exactamente el defecto que esta
    # lente nació midiendo.
    cod, salida, err = git('ls-remote', '--heads', 'origin', espera=ESPERA)
    if cod != 0:
        print(f'  ⚠ SIN MEDIR: el remoto no contestó, así que esta corrida no '
              f'midió si el trabajo salió — {err.splitlines()[-1][:160] if err else cod}')
        return 0

    remoto = {}
    for linea in salida.splitlines():
        partes = linea.split('\t')
        if len(partes) == 2 and partes[1].startswith('refs/heads/'):
            remoto[partes[1][len('refs/heads/'):]] = partes[0]

    if not remoto:
        check('el remoto tiene al menos una rama', False,
              'origin contestó sin ninguna rama: no hay dónde haber subido nada')
        return 1 if fallas else 0

    # ── 1 · TODO LO COMMITEADO ESTÁ EN EL REMOTO ──────────────────────────
    #
    # Y acá hubo que medir dos veces, porque el primer intento de esta lente
    # no podía correr en el caso que más importa: `git rev-list HEAD --not
    # <sha>` revienta con «bad object» si ese commit del remoto no está en
    # este disco, que es justo lo que pasa cuando el ref local quedó viejo.
    # Lo encontró el arnés, en el ejercicio 3.
    #
    # Así que se miden solo los commits del remoto que este disco TIENE, y
    # no tener ninguno no se perdona en silencio: sin un commit del remoto
    # acá, no hay con qué comparar, y eso es un rojo con su remedio escrito.
    # Creerle al ref local en ese caso sería creerle a la foto vieja, que es
    # el defecto que esta lente nació midiendo.
    conocidos = [sha for sha in remoto.values()
                 if git('cat-file', '-e', sha + '^{commit}')[0] == 0]
    if not conocidos:
        check('este disco tiene al menos un commit del remoto con el que comparar', False,
              f'origin tiene {len(remoto)} rama(s) y ninguno de sus commits está acá: '
              'no se puede medir si el trabajo salió — se arregla con `git fetch origin`')
    else:
        cod, sueltos, err = git('rev-list', '--format=%h %ad %s',
                                '--date=format:%d/%m %H:%M',
                                '--no-commit-header', 'HEAD', '--not', *conocidos)
        if cod != 0:
            check('se pueden listar los commits que no están en el remoto', False,
                  err.replace('\n', ' ')[:160])
        else:
            lineas = [l for l in sueltos.splitlines() if l.strip()]
            check(f'todo lo commiteado salió del repo ({len(remoto)} rama(s) en origin)',
                  not lineas,
                  f'{len(lineas)} commit(s) commiteados y SIN SUBIR, que se pierden con el '
                  f'contenedor: ' + ' · '.join(lineas[:5]) +
                  ('…' if len(lineas) > 5 else '') + ' — se arregla con `git push`')

    # ── 2 · EL REF LOCAL DE ORIGIN NO ES UNA FOTO DE AYER ─────────────────
    # Esta es la que se cobró la despertada del 17 a las 15:30. `git status`,
    # `git rev-parse origin/main` y `git log origin/main..` leen este ref sin
    # avisar de qué fecha es.
    viejos = []
    for rama, sha in sorted(remoto.items()):
        cod, local, _ = git('rev-parse', '--verify', '--quiet', f'refs/remotes/origin/{rama}')
        if cod == 0 and local and local != sha:
            viejos.append(f'origin/{rama}: en disco {local[:7]}, en el remoto {sha[:7]}')
    check('el ref local de origin coincide con el remoto de verdad', not viejos,
          '; '.join(viejos) + ' — el ref es una foto vieja y cualquier lente que lo '
          'lea mide el remoto de ayer; se arregla con `git fetch origin`')

    # ── 3 · Y EL ÁRBOL, PARA QUE EL ROJO DE ARRIBA SE PUEDA LEER ──────────
    # No es una falla tener cambios sin commitear —la batería se corre justo
    # ahí—, pero si están, se nombran: un `git push` no los lleva.
    cod, sucio, _ = git('status', '--porcelain')
    if cod == 0 and sucio.strip():
        print(f'  · {len(sucio.splitlines())} archivo(s) con cambios sin commitear '
              '(normal al correr la batería; `git push` no los lleva)')

    return 1 if fallas else 0


if __name__ == '__main__':
    sys.exit(main())
