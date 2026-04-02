.PHONY: web-install web-dev web-typecheck

web-install:
	cd apps/web && npm install

web-dev:
	cd apps/web && npm run dev

web-typecheck:
	cd apps/web && npm run typecheck
