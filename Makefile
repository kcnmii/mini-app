up:
	docker compose up -d postgres redis minio gotenberg

down:
	docker compose down

start-dev:
	bash scripts/start-dev.sh

stop-dev:
	bash scripts/stop-dev.sh

api:
	cd apps/api && uv run uvicorn app.main:app --reload

miniapp:
	cd apps/miniapp && pnpm dev

docgen:
	cd apps/docgen && pnpm dev
