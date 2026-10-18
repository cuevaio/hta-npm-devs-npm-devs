# Zavu · agente de soporte "Ada"

Zavu Function con un agente (`defineAgent`) y dos herramientas (`lookup_order`, `escalate`).
Corre en Zavu Cloud; esta carpeta es autocontenida y se despliega desde aquí.

## Requisitos

- Node 18+ (probado con 22)
- Acceso al proyecto de Zavu (`.zavu/config.json`) y sesión iniciada: `npx zavudev login`
- [Bun](https://bun.sh), solo para `npx zavudev fn invoke`

## Puesta en marcha

```sh
npm ci
npx tsc -p .          # chequeo de tipos, no genera archivos
cp .env.example .env  # completar SENDER_ID para pruebas locales
```

## Probar y desplegar

```sh
npx zavudev fn invoke --tool lookup_order --args '{"order_id":"ORD-001"}'
npx zavudev fn secrets set SENDER_ID <senderId>   # una vez por función
npx zavudev deploy
```

## Qué hay aquí

| Archivo | Qué es |
|---|---|
| `index.ts` | Prompt del agente, canales, voz y herramientas |
| `.zavu/config.json` | Vincula la carpeta con la función en Zavu. **No borrar ni editar**: sin el `functionId` no se puede desplegar |
| `.env.example` | Variables para pruebas locales. `.env` está en `.gitignore` |

Solo se despliega lo que `index.ts` importa por ruta relativa, y nunca archivos fuera de esta carpeta (`../`).

## Pendiente

- `lookup_order` devuelve datos fijos (`"shipped"`): conectar al backend real antes de exponerlo a clientes.
- `escalate` solo hace `console.log`: falta notificar a una persona.
- El prompt es de soporte genérico en inglés; adaptarlo al caso del transportista.
