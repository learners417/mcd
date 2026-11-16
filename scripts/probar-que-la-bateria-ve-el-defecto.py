#!/usr/bin/env python3
"""
¿LA BATERÍA DE MCD VE EL DEFECTO? — el otro lado de «74 en verde».

Que una lente esté en verde no dice nada: dice que hoy no se cayó. La pregunta
de atrás es si, puesto el defecto, se pone roja alguna. Para la batería de MCD
nadie la había hecho nunca sobre el producto: el 13 y el 14 de noviembre se
auditó la batería CONTRA SÍ MISMA (el comentario, la puerta, la lista vacía),
que es otra cosa.

MEDIDO EL 16 DE NOVIEMBRE DE 2026: diez defectos puestos a propósito en los
archivos de verdad, uno por vez, con las 74 lentes corriendo contra cada uno.

  | el defecto puesto                                   | la batería  |
  |-----------------------------------------------------|-------------|
  | la etiqueta del GCM se lee un byte corta            | 74 en verde |
                                        (y el primer intento de prueba tampoco:
                                         AES-GCM acepta etiquetas truncadas, asi
                                         que el token iba y venia igual. Lo ve la
                                         vuelta byte por byte de la etiqueta.)
  | el IV del cifrado es siempre el mismo (doce ceros)  | 74 en verde |
  | el descifrado devuelve lo guardado, sin descifrar   | 74 en verde |
  | la paginación corta en la primera página            | 74 en verde |
  | la bandeja nunca marca que esperan respuesta        | 74 en verde |
  | toda venta abierta cuenta como paciente             | 74 en verde |
  | el que no vino cuenta como que vino                 | 74 en verde |
  | el hilo anidado de GHL deja de desanidarse          | 74 en verde |
  | el `429` fuera de la condición del reintento        | **roja**    |
  | un segundo `const MAX_ITEMS`                        | **roja**    |

Los dos que se veían eran de TEXTO. Los ocho que no se veían eran de CUENTA:
la batería leía el código y no lo ejecutaba. Las pruebas que faltaban se
escribieron ese día —`prueba-el-token-cifrado.ts`, `prueba-las-listas-completas.ts`
y `prueba-lo-que-ve-el-avatar.ts`, en el bloque 10— y esto es lo que las obliga
a seguir viendo: cada defecto de abajo NOMBRA la lente que tiene que ponerse
roja. Si alguien la ablanda, acá se entera.

Cómo: el repo se copia a una carpeta temporal —el `node_modules` va por
enlace—, el defecto se pone sobre la copia y se corre SOLO la lente declarada.
El repo de verdad no se toca nunca.

Correr con: python3 scripts/probar-que-la-bateria-ve-el-defecto.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (nombre, archivo, lo que dice, lo que va a decir, la lente que DEBE verlo, qué es)
DEFECTOS = [
    # ── los ocho que nadie veía, el 16 de noviembre de 2026 ────────────────
    ('etiqueta-corta', 'src/lib/crypto.ts',
     'buf.subarray(12, 28)', 'buf.subarray(12, 27)',
     'prueba-el-token-cifrado.ts',
     'la etiqueta se verifica truncada: el ultimo byte no lo mira nadie'),
    ('iv-fijo', 'src/lib/crypto.ts',
     'crypto.randomBytes(12)', 'Buffer.alloc(12)',
     'prueba-el-token-cifrado.ts',
     'nonce repetido en AES-GCM: el PIT se puede despejar y falsificar'),
    ('sin-descifrar', 'src/lib/crypto.ts',
     'if (!stored.startsWith(PREFIX)) return stored', 'if (true) return stored',
     'prueba-el-token-cifrado.ts',
     'GHL recibe el texto cifrado como token: 401 para todos los clientes'),
    ('corta-en-cien', 'src/lib/ghl/client.ts',
     'if (page.length < 100) break', 'if (page.length <= 100) break',
     'prueba-las-listas-completas.ts',
     'el cliente con 300 contactos ve 100, en silencio: faltan personas'),
    ('bandeja-muda', 'src/lib/ghl/normalize.ts',
     'sinLeer: Number(c.unreadCount ?? 0),', 'sinLeer: 0,',
     'prueba-lo-que-ve-el-avatar.ts',
     'la doctora no ve que la esperan y deja de contestar'),
    ('todos-pacientes', 'src/lib/ghl/normalize.ts',
     "if (status === 'won' ||", "if (status !== 'lost' ||",
     'prueba-lo-que-ve-el-avatar.ts',
     'toda venta abierta cuenta como paciente: el tablero miente'),
    ('no-vino-vino', 'src/lib/ghl/normalize.ts',
     "noshow: 'no_vino'", "noshow: 'realizada'",
     'prueba-lo-que-ve-el-avatar.ts',
     'el que no vino cuenta como que vino: la tasa de asistencia infla'),
    ('hilo-anidado', 'src/lib/ghl/client.ts',
     'return data.messages?.messages ?? data.messages ?? []', 'return data.messages ?? []',
     'prueba-las-listas-completas.ts',
     'la conversacion se dibuja vacia cuando GHL anida el hilo'),
    # ── y los dos que SÍ se veían, para que sigan viéndose ─────────────────
    ('sin-reintento-429', 'src/lib/ghl/client.ts',
     'if ((res.status === 429 || res.status >= 500) && attempt < 2)',
     'if (res.status >= 500 && attempt < 2)',
     'auditoria.py',
     'el sync se cae por rate-limit en una cuenta grande'),
    ('dos-techos', 'src/lib/ghl/client.ts',
     'const MAX_ITEMS = 1_000', 'const MAX_ITEMS = 1_000\nconst MAX_ITEMS_2 = 1_000',
     'auditoria.py',
     'el techo de la paginacion declarado en dos lugares'),
]

fallas: list = []


def correr(lente, cwd):
    """Corre una sola lente sobre la copia. Roja = codigo != 0 o un ✗ impreso."""
    if lente == 'auditoria.py':
        cmd = [sys.executable, 'auditoria.py', '--rapido']
    else:
        cmd = ['node', '--experimental-transform-types', f'scripts/{lente}']
    entorno = dict(os.environ, MCD_SIN_ARNES='1')  # la copia no vuelve a llamar a este arnes
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=entorno)
    salida = r.stdout + r.stderr
    roja = r.returncode != 0 or any('✗' in l for l in salida.splitlines())
    return roja, salida


def main():
    copia = tempfile.mkdtemp(prefix='mcd-ve-el-defecto-')
    try:
        subprocess.run(
            f'tar -cf - --exclude=node_modules --exclude=.git --exclude=.next '
            f'-C {RAIZ} . | tar -xf - -C {copia}',
            shell=True, check=True)
        os.symlink(os.path.join(RAIZ, 'node_modules'), os.path.join(copia, 'node_modules'))

        # 1 · Sin defecto, las lentes declaradas tienen que estar VERDES.
        for lente in sorted({d[4] for d in DEFECTOS}):
            roja, salida = correr(lente, copia)
            if roja:
                ultima = (salida.strip().splitlines() or [''])[-1][:120]
                fallas.append(f'{lente} ya esta ROJA sin defecto: {ultima}')
                print(f'  ✗ {lente} ya esta roja sin ningun defecto puesto')
            else:
                print(f'  ✓ {lente} esta verde sin defecto')

        # 2 · Con el defecto puesto, la lente declarada tiene que ponerse ROJA.
        for nombre, rel, viejo, nuevo, lente, que in DEFECTOS:
            p = os.path.join(copia, rel)
            original = open(p, encoding='utf-8').read()
            if original.count(viejo) != 1:
                fallas.append(
                    f'{nombre}: el texto del defecto aparece {original.count(viejo)} veces '
                    f'en {rel}, no una. El defecto no se pudo poner, asi que no se midio nada.')
                print(f'  ✗ {nombre}: no se pudo poner el defecto en {rel}')
                continue
            open(p, 'w', encoding='utf-8').write(original.replace(viejo, nuevo))
            try:
                roja, _ = correr(lente, copia)
            finally:
                open(p, 'w', encoding='utf-8').write(original)
            if roja:
                print(f'  ✓ {nombre} — {que}: {lente} se pone roja')
            else:
                fallas.append(f'{nombre} ({que}): {lente} sigue VERDE con el defecto puesto')
                print(f'  ✗ {nombre} — {que}: {lente} NO lo ve')
    finally:
        shutil.rmtree(copia, ignore_errors=True)

    if fallas:
        print(f'\n✗ {len(fallas)} defectos que la bateria no ve:')
        for f in fallas:
            print(f'   · {f}')
        return 1
    print(f'\n✓ los {len(DEFECTOS)} defectos ponen roja a su lente')
    return 0


if __name__ == '__main__':
    sys.exit(main())
