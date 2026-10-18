# e2e · flujo de la demo

Playwright contra los despliegues públicos. Compartido; lo integra Joseph (#26).

## Tests

```sh
npx playwright install chromium   # una vez
E2E_API_URL=https://... E2E_DASHBOARD_URL=https://... E2E_LANDING_URL=https://... npm test
```

Los tests de una superficie sin URL se saltan. En CI, las URLs salen de las variables del repositorio `E2E_API_URL`, `E2E_DASHBOARD_URL` y `E2E_LANDING_URL`, o de los inputs al lanzar el workflow a mano.
