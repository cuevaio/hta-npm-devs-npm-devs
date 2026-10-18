# Los reportes del conductor entran por webhook, no por el agente

El webhook de Zavu recibe todos los mensajes entrantes, firmados y con reintentos, aunque el agente esté activo ([`zavu-whatsapp-capacidades.md`](../research/zavu-whatsapp-capacidades.md)). Los reportes del conductor se registran desde ese webhook en nuestro backend, deduplicados por id de mensaje, y el agente nunca escribe reportes. Si los registrara el agente, cada mensaje podría guardarse dos veces y su captura dependería de que el LLM decida llamar a una tool.

## Consequences

- El agente de Zavu solo tiene tools de lectura.
- Conductores y gestor comparten número (un agente por número); el rol se resuelve en la Domain API a partir del teléfono del contacto.
