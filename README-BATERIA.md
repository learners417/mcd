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

Esta es la primera batería. Nueve bloques, 46 lentes el 9 de noviembre; **diez
bloques y 87 lentes hoy**, y el bloque 10 es el que dejó de leer para empezar a
ejecutar.

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
| 10 | el código se ejecuta, no solo se lee | la cuenta se rompe sin que cambie una sola letra del código, y los nueve bloques de arriba miran letras |

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

## La tercera vez que se midió la batería y no el código: ¿VE el defecto?

**El 16 de noviembre.** Las dos veces anteriores preguntaron si una lente se
podía *engañar* (con un comentario, con una lista vacía). Esta preguntó otra
cosa: **puesto el defecto de verdad, ¿se pone roja alguna?** Diez defectos en
los archivos de verdad, uno por vez, con las 74 lentes corriendo contra cada
uno. **Ocho no los vio nadie:**

| el defecto puesto | lo que le pasa al cliente | la batería |
|---|---|---|
| la etiqueta del GCM leída un byte corta | el último byte de la etiqueta no lo verifica nadie | 74 en verde |
| el IV fijo en doce ceros | nonce repetido en AES-GCM: el PIT se puede despejar y falsificar | 74 en verde |
| el descifrado devuelve lo guardado, sin descifrar | GHL recibe el texto cifrado como token: 401 para todos | 74 en verde |
| `page.length < 100` → `<= 100` | el cliente con 300 contactos ve 100, **en silencio** | 74 en verde |
| la bandeja marca cero sin leer siempre | la doctora no ve que la esperan y deja de contestar | 74 en verde |
| toda venta abierta cuenta como paciente | el tablero miente | 74 en verde |
| el que no vino cuenta como que vino | la tasa de asistencia infla | 74 en verde |
| el hilo anidado de GHL sin desanidar | la conversación se dibuja vacía | 74 en verde |

Los dos que **sí** se vieron eran de texto: el `429` borrado de la condición
del reintento, y un segundo `const MAX_ITEMS`. O sea: la batería veía las
letras y no la cuenta. El cuarto de la tabla es literalmente lo que el bloque 6
dice que existe para evitar.

**Lo que se construyó.** Las tres primeras pruebas de MCD que ejecutan código,
con 71 escenarios, y el bloque 10 que las corre:

| la prueba | qué ejecuta |
|---|---|
| `scripts/prueba-el-token-cifrado.ts` | cifra y descifra de verdad: la vuelta completa, el IV que no se repite, los 16 bytes de la etiqueta uno por uno, la clave equivocada, el passthrough de datos viejos |
| `scripts/prueba-las-listas-completas.ts` | la paginación contra un GHL de juguete: 300 contactos llegan 300, el borde de 101, el techo de 1.000, las 250 oportunidades, el hilo anidado |
| `scripts/prueba-lo-que-ve-el-avatar.ts` | los normalizadores: quién espera respuesta, quién no vino, en qué etapa está cada venta |

Corren con el TypeScript que Node 22 entiende solo
(`node --experimental-transform-types`), **a propósito: MCD no gana ninguna
dependencia nueva por tener pruebas.** A mano: `npm run pruebas`.

**Y lo que las obliga a seguir viendo:**
`scripts/probar-que-la-bateria-ve-el-defecto.py`, dentro del bloque 10. Los
diez defectos de la tabla, y **cada uno NOMBRA la lente que tiene que ponerse
roja**. Si alguien ablanda esa prueba, el renglón se pone rojo. Probado contra
su propio fallo: con las afirmaciones de la etapa ablandadas, el arnés salió en
rojo y nombró el defecto que había vuelto a ser invisible.

El arnés también cazó un agujero en la primera versión de la prueba del token:
la etiqueta leída un byte corta **igual descifra**, porque AES-GCM acepta
etiquetas truncadas, así que la vuelta completa daba verde. Lo ve la vuelta
byte por byte que quedó escrita.

## Una decisión de producto que quedó medida y NO se tocó

`toVenta` evalúa el nombre de la etapa con un `||`, así que **gana sobre el
status de GHL**: una venta `lost` o `abandoned` parada en la etapa «Paciente»
se muestra como paciente. El comentario del propio archivo dice lo contrario
(«Señal DURA primero: el status de GHL»). Hoy es así, y quedó clavado en
`prueba-lo-que-ve-el-avatar.ts` para que el cambio sea un clic de Javo y no un
descuido.

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
