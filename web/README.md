# web · landing de Certera

Página única y estática, sin build. HTML, CSS y Canvas, más el simulador del viaje en un iframe. Solo español.
Secciones (por `id`): `hero`, `problema`, `simulador` (viaje real: pendiente y consumo), `como-funciona`, `diferenciador` (escenario T-04 en Ticlio, ilustrativo), `torre` (MCP), `procedencia` (viabilidad y aviso) y `cta`.

## Correr en local

```sh
cd web
python3 -m http.server 8787
# http://127.0.0.1:8787
```

Hace falta un servidor (no `file://`): la página carga `assets/tokens.css` por ruta relativa y ajusta la altura del iframe del simulador leyendo su contenido.

## Tests

```sh
npm ci
npx playwright install chromium   # una vez
npm test
```

Playwright verifica el contenido, que no quede la marca Cuadra, que el simulador cargue, el aviso, el enlace al dashboard, el favicon y los metadatos para redes.

## Archivos generados

No se editan a mano; se regeneran desde `web/`:

| Comando | Genera | Desde |
|---|---|---|
| `node scripts/simulador.mjs` | `assets/simulador.html` | `../simulator/fuel-drive.html`, con la paleta de Certera |
| `node scripts/imagenes.mjs` | `favicon.ico`, `assets/brand/*.png`, `assets/og-certera.png` | `assets/brand/certera-*.svg` |

## Desplegar en Vercel (ADR 0011)

1. Importar el repo en Vercel y poner **Root Directory** = `web/`.
2. `vercel.json` ya indica sitio estático sin build ni install.
3. Si el dashboard queda en otra URL, cambiar `DASHBOARD_URL` en el `<script>` de `index.html` (y los `href` de respaldo).
4. La vista previa en redes usa URLs absolutas a `https://fleet-intelligence-ashy.vercel.app`. Si el proyecto queda con otro dominio, cambiarlo en `canonical`, `og:url`, `og:image` y `twitter:image` del `<head>`.

## Qué hay acá

| Archivo | Qué es |
|---|---|
| `index.html` | La landing completa; la lógica está en el `<script>` final |
| `assets/tokens.css` | Color, tipografía, espacio y movimiento. **Única fuente de verdad** de la página |
| `assets/brand/certera-*.svg` | Símbolo y favicon de Certera |
| `assets/simulador.html` | Simulador embebido (generado) |
| `assets/og-certera.png` | Imagen 1200×630 para compartir (generada) |
| `site.webmanifest`, `favicon.ico` | Íconos para navegadores y móviles |
| `assets/brand/cuadra-*.svg`, `assets/media/` | Heredados; la landing no los usa |
