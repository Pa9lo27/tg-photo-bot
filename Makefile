up:
	docker compose up --build

up_d:
	docker compose up --build -d

down:
	docker compose down -v

logs:
	docker compose logs -f

tree:
	tree -I 'venv'
