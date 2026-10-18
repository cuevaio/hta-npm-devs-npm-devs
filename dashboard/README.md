# dashboard

Vite + TypeScript. El framework se decide en el grilling del dashboard (#8). Dueña: Lian.

## Correr

```sh
npm ci
npm run dev
```

## Tests

```sh
npx playwright install chromium   # una vez
npm test
```

Playwright compila, sirve el build con `vite preview` y corre los tests contra él.
