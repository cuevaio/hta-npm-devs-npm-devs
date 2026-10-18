import { PROMPT } from "./prompt"

// Configuración del agente de WhatsApp: Gemini con la key propia de Google.
// Vive aparte de index.ts para poder probarla sin registrar el agente.

export const AGENT_MODEL = "gemini-4-argon"

type Env = Record<string, string | undefined>

export function agentConfig(env: Env) {
  const apiKey = env.GEMINI_API_KEY
  if (!apiKey) {
    throw new Error(
      "Falta la variable de entorno GEMINI_API_KEY: el agente usa Gemini con la key propia de Google. " +
        "En producción: tools/zavu.sh fn secrets set GEMINI_API_KEY -",
    )
  }
  return {
    senderId: env.SENDER_ID!,
    name: "Fleet Intelligence",
    provider: "google" as const,
    model: AGENT_MODEL,
    apiKey,
    channels: ["whatsapp" as const],
    prompt: PROMPT,
  }
}
