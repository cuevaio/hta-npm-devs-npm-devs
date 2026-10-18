import { describe, expect, it } from "vitest"
import { agentConfig } from "../agent"

describe("configuración del agente de WhatsApp", () => {
  const env = { SENDER_ID: "snd_1", GEMINI_API_KEY: "clave-gemini" }

  it("usa Gemini con la key propia de Google", () => {
    const cfg = agentConfig(env)
    expect(cfg.provider).toBe("google")
    expect(cfg.model).toBe("gemini-4-argon")
    expect(cfg.apiKey).toBe("clave-gemini")
  })

  it("falla con un mensaje claro si falta GEMINI_API_KEY", () => {
    expect(() => agentConfig({ SENDER_ID: "snd_1" })).toThrow(/GEMINI_API_KEY/)
    expect(() => agentConfig({ SENDER_ID: "snd_1", GEMINI_API_KEY: "" })).toThrow(
      /Falta la variable de entorno GEMINI_API_KEY/,
    )
  })
})
