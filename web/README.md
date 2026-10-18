# web · landing de Cuadra

Página única, sin build ni dependencias. HTML, CSS y Canvas.

## Correr en local

```sh
cd web
python -m http.server 8787
# http://127.0.0.1:8787
```

Hace falta un servidor (no `file://`) porque la página carga `assets/tokens.css` por ruta relativa.

## Tests

```sh
npm ci
npx playwright install chromium   # una vez
npm test
```

Playwright levanta el servidor estático y verifica que la landing carga sin errores. Las dependencias de `package.json` son solo para los tests: la landing sigue sin build.

## Qué hay acá

| Archivo | Qué es |
|---|---|
| `index.html` | La landing completa. Toda la lógica está en el `<script>` del final |
| `assets/tokens.css` | Color, tipografía, espacio y movimiento. **Única fuente de verdad.** No escribas un hex en `index.html` |
| `assets/brand/` | Sistema de símbolo en SVG. Regenerable con `sh tools/gen-logos.sh web/assets/brand` |
| `assets/media/` | Vacío: acá van el video y la imagen del hero |

Las reglas de uso de todo esto están en [`docs/brand/IDENTIDAD-VISUAL.md`](../docs/brand/IDENTIDAD-VISUAL.md).

## Los dos huecos de contenido

Buscá `<!-- HUECO -->` en `index.html`. Hay dos, y los dos ya tienen un placeholder
dibujado en Canvas que funciona como fallback definitivo si el material no llega.

1. **Imagen del hero** · 4:5 · `assets/media/hero.webp` → descomentar el `<img>` dentro de `#hero-imagen`.
2. **Video** · 16:9 · `assets/media/demo.mp4` + `demo-poster.webp` + `demo-es.vtt` → descomentar el `<video>` dentro de `#video`.

Detalle de qué debe mostrar cada uno, peso máximo y tratamiento: §14 del manual de identidad.

## Publicar como Artifact de Claude

El Artifact envuelve el archivo en su propio esqueleto de documento y bloquea las
hojas de estilo externas que no sean Google Fonts, así que hay que generar una
variante: sin `<!doctype>`/`<html>`/`<head>`/`<body>` y con `tokens.css` incrustado.

```sh
sh tools/build-artifact.sh      # -> build/cuadra-landing.html
```

Correrlo cada vez que cambie `index.html` o `tokens.css`, o el link publicado queda viejo.

**Nota:** dentro de un Artifact no se puede embeber YouTube ni Vimeo (los iframes
externos están bloqueados). Ahí el video tiene que ser un `<video>` con archivo propio.
En el despliegue del repositorio no hay esa restricción.

## Antes de tocar nada

El checklist de §15 del manual de identidad. Los tres que más se rompen por costumbre:
sin `border-radius`, sin sombras, y todo chip de estado lleva su palabra además del color.
