import { defineAgent, defineTool } from "@zavudev/functions"
import { PROMPT } from "./prompt"
import { TOOL_DEFS, callDomainApi } from "./tools"

// Fleet Intelligence: agente de WhatsApp para el gestor de flota.
// Las tools de lectura solo hacen fetch a la Domain API (ADR 0004).
// Solo se despliega lo que se importa por ruta relativa desde este archivo.

defineAgent({
  senderId: process.env.SENDER_ID!,
  name: "Fleet Intelligence",
  provider: "zavu",
  model: "deepseek/deepseek-v4-flash-0731",
  channels: ["whatsapp"],
  prompt: PROMPT,
})

for (const def of TOOL_DEFS) {
  defineTool({
    name: def.name,
    description: def.description,
    parameters: def.parameters,
    handler: async (args) => callDomainApi(def.name, args as Record<string, unknown>),
  })
}
