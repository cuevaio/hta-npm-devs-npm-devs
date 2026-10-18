# La landing y el dashboard se despliegan en Vercel; el MCP sigue en Cloudflare

Las dos piezas web (la landing en `web/` y el dashboard en `dashboard/`) se despliegan en Vercel, en proyectos separados, por decisión del equipo (es la plataforma que ya usó en proyectos anteriores). El servidor MCP sigue en Cloudflare Workers (ADR 0004) porque es un Worker, no un sitio. Esto reemplaza la decisión inicial de Cloudflare Pages para la web (D22).

## Consequences

- La Domain API en Cloud Run debe permitir por CORS los orígenes de Vercel (producción y previews) en las rutas que lee el dashboard.
- Las URLs de Vercel alimentan las variables `E2E_DASHBOARD_URL` y `E2E_LANDING_URL` del workflow de e2e.
