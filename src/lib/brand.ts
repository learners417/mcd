// Marca MCD (verde). Prohibido cambiar sin confirmar (regla de vocabulario).
export const BRAND = {
  black: '#080808',
  panel: '#0F0F0F',
  line:  '#1e1e1e',
  green:   '#3D6B4F',
  greenL:  '#5A9170',
  gold:    '#E8962E',
  goldL:   '#F4B65C',
  text:  '#EDEDED',
  muted: '#8a8a8a',
} as const

// Idioma MVP: castellano NEUTRO (tú/tienes). Sin voseo hardcodeado.
export const COPY = {
  greet: (name: string) => `Hola, ${name}`,
  greetSub: 'Este es el estado de tu práctica hoy.',
} as const
