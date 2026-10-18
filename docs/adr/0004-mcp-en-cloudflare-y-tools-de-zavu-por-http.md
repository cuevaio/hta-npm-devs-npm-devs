# El servidor MCP vive en Cloudflare y las tools de Zavu llaman a la Domain API por HTTP

Zavu no puede consumir servidores MCP ("MCP connections are not supported", [`zavu-whatsapp-capacidades.md`](../research/zavu-whatsapp-capacidades.md)), así que el agente de WhatsApp no puede usar nuestro MCP. Hay dos superficies de tools: las de Zavu, que hacen `fetch` a la Domain API, y un servidor MCP en Cloudflare para agentes externos, con las mismas 7 tools. Ambas son adaptadores delgados: toda la lógica vive en la Domain API (FastAPI en Cloud Run), que es la única que toca la base de datos.

## Consequences

- Las tools parecen duplicadas, pero no se deben fusionar ni mover lógica a ninguna de las dos.
- El MCP también es el plan B si falla el agente de Zavu: se pausa y se orquesta desde nuestro lado.
