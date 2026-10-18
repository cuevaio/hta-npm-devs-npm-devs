# web · landing de Fleet Intelligence

Página única y estática, sin build. HTML, CSS y un Canvas (perfil de altitud vs combustible). Solo español.
Secciones (por `id`): `hero`, `problema`, `como-funciona` (el agente y sus cuatro dimensiones), `ejemplo` (caso T04 en Ticlio, ilustrativo), `arquitectura`, `mcp`, `procedencia` y `cta`.

## Correr en local

```sh
cd web
python3 -m http.server 8787
# http://127.0.0.1:8787
```

Hace falta un servidor (no `file://`) porque la página carga `assets/tokens.css` por ruta relativa.

## Tests

```sh
npm ci
npx playwright install chromium   # una vez
npm test
```

Playwright verifica el contenido, que no quede rastro de la marca anterior, el aviso de procedencia, el enlace al dashboard y que no haya errores de página.

## Desplegar en Vercel (ADR 0011)

1. Importar el repo en Vercel y poner **Root Directory** = `web/`.
2. `vercel.json` ya indica sitio estático sin build ni install.
3. Si el dashboard queda en otra URL, cambiar `DASHBOARD_URL` en el `<script>` de `index.html` (y los `href` de respaldo).

## Qué hay acá

| Archivo | Qué es |
|---|---|
| `index.html` | La landing completa; la lógica está en el `<script>` final |
| `vercel.json` | Configuración de sitio estático para Vercel |
| `assets/tokens.css` | Color, tipografía, espacio y movimiento. **Única fuente de verdad.** No escribas un hex en `index.html` |
| `assets/brand/`, `assets/media/` | Heredados; la landing no los usa |

Reglas visuales: [`docs/brand/IDENTIDAD-VISUAL.md`](../docs/brand/IDENTIDAD-VISUAL.md). Sin `border-radius`, sin sombras, y todo estado lleva su palabra además del color.
