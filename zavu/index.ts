import { defineAgent, defineTool } from "@zavudev/functions"
import { agentConfig } from "./agent"
import { TOOL_DEFS, callDomainApi } from "./tools"

// Certera: agente de WhatsApp para el gestor de flota.
// Las tools de lectura solo hacen fetch a la Domain API (ADR 0004).
// Solo se despliega lo que se importa por ruta relativa desde este archivo.

defineAgent(agentConfig(process.env))

for (const def of TOOL_DEFS) {
  defineTool({
    name: def.name,
    description: def.description,
    parameters: def.parameters,
    handler: async (args) => callDomainApi(def.name, args as Record<string, unknown>),
  })
}
