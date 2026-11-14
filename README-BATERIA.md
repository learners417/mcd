# MCD · LA BATERÍA

Una sola orden, desde la raíz del repo y con `node_modules` instalado:

```
npm run bateria          # todo, incluido el build (~2 min)
npm run bateria:rapida   # todo menos el build (~20 s)
```

Verde quiere decir que puede salir. Rojo dice exactamente qué se rompió.

## Por qué existe, y por qué recién ahora

MCD es el negocio recurrente: TCD vende una vez, MCD cobra todos los meses.
Su propio `README-AUDITORIA.md` lo abre así — «un bug acá no es un bug, es
churn» — y aun así el repo no tenía **ninguna** prueba. El `package.json`
tenía tres scripts (dev, build, start) y ninguno miraba si el código es
correcto: ni siquiera `tsc --noEmit`.

Esta es la primera batería. Nueve bloques, 46 lentes.

## Qué cuida cada bloque

| # | bloque | qué pasaría sin él |
|---|---|---|
| 1 | el código compila | un error de tipos llega a producción sin que nadie lo vea |
| 2 | ninguna pantalla sin llave | una pantalla nueva queda abierta sin sesión, con los pacientes de un cliente detrás |
| 3 | la plata tiene una sola fuente | vuelven `payments`/`sessions`, o un cobro sin comprobante dispara el cinturón Rojo en TCD |
| 4 | cada puerta pide su llave | una ruta de API contesta sin preguntar nada, o la clave se puede adivinar cronometrando |
| 5 | el token del cliente no viaja en claro | el PIT de GHL —acceso total a sus pacientes y su WhatsApp— queda legible |
| 6 | las listas llegan completas | los contactos se truncan en 100 **en silencio**: «faltan personas» |
| 7 | ningún secreto escrito en el repo | un secreto entra al historial de git y ya no se borra: hay que rotarlo; o entra `node_modules` entero |
| 8 | las dos apps se nombran igual | el puente cambia un campo y el contador X/10 de TCD deja de moverse |
| 9 | la batería se puede correr | una batería que no está en el `package.json` se corre una vez y se olvida |

## La regla de las lentes

Cada lente defiende algo que **ya está bien hoy**, y se escribió después de
medirlo, no antes. Y cada una se probó contra su propio fallo: se reintrodujo
el defecto a propósito y se confirmó que se pone roja.

Las siete que se reintrodujeron el 9 de noviembre, y todas dieron rojo:

1. una pantalla nueva bajo `(app)/` que no entra en la lista de protegidas
2. una pantalla que vuelve a leer `payments`
3. una migración que vuelve nullable el comprobante del cobro
4. el puente comparando su clave con `!==` pelado
5. los contactos truncándose en las primeras cien
6. un JWT pegado en el código
7. el puente dejando de devolver `primer_cobro`
8. el `.gitignore` borrado

## Las dos veces que se midió la batería, y no el código

**El 13 de noviembre**, dos lentes daban verde con el defecto puesto: la
guarda de las rutas y el service role en el navegador. Las dos leían el
archivo **crudo**, así que un comentario que nombrara la guarda alcanzaba.

**El 14 de noviembre**, lo que quedaba abierto después de ese arreglo:

1. **El comentario del FINAL de la línea.** `solo_codigo` sacaba el de bloque
   y el de línea entera, no el del final. Medido: con la comparación del
   puente cambiada por un `!==` pelado y `timingSafeEqual` y `.length !==`
   dejados al final de esa misma línea, **las 53 lentes daban verde**. Ahora
   se saca también ese, sin tocar las barras de una URL, de un texto ni de una
   expresión regular —las tres probadas en una lente propia—.
2. **«Todo el que guarda un token lo cifra» medía para nadie.** Buscaba la
   columna `ghl_token`, y esa columna **no existe en este repo**: el token del
   cliente vive en `private_token` de `ghl_connections`. `ghl_token` aparecía
   en un solo lugar de todo MCD: en esa línea de la batería. La lista salía
   vacía y el verde no significaba nada. Con la columna de verdad **seguía**
   dando verde con el token guardado en claro, porque miraba el archivo y el
   `import { encryptToken }` de arriba ya alcanzaba. Ahora se mide **el valor
   que se escribe**, y una lente nueva exige que la lista tenga a alguien:
   una lista vacía es la forma en que una lente se apaga sola sin avisar.

Las tres se probaron contra su propio fallo, y las tres dieron rojo.

## Lo que esta batería todavía NO prueba

El puente de punta a punta. Acá se mira **solo el lado de MCD**: que el
contrato que TCD consume no cambie de nombre. La ida y vuelta de verdad —con
el lado de TCD, `api/mcd-bridge.ts`— es el turno 7 de la cola.

## Una decisión que no se tomó sola

Al instalar las dependencias para correr la batería apareció un
`package-lock.json`, que MCD no tenía. **No se subió, a propósito.** Un
lockfile es buena práctica, pero subir ESTE fija las versiones que se
resolvieron el 9 de noviembre, y eso cambia lo que Vercel instala en el
próximo deploy respecto de lo que corre hoy. Es una decisión de Javo, no de la
batería. Si la quiere: `npm install` y subir el `package-lock.json` que queda.
