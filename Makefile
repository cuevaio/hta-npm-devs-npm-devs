# Un objetivo por carpeta; `make test` corre todos los que no necesitan URLs públicas.
.PHONY: test test-backend test-mcp test-dashboard test-web test-e2e

test: test-backend test-mcp test-dashboard test-web

test-backend:
	cd backend && uv run pytest

test-mcp:
	cd mcp && npm run typecheck && npm test

test-dashboard:
	cd dashboard && npm test

test-web:
	cd web && npm test

# Requiere E2E_API_URL, E2E_DASHBOARD_URL y/o E2E_LANDING_URL.
test-e2e:
	cd e2e && npm test
