default:
  just --list

run *args:
  uv --project backend run uvicorn backend.app.main:app --reload {{args}}

mm *args:
  uv --project backend run --directory backend alembic revision --autogenerate -m "{{args}}"

migrate:
  uv --project backend run --directory backend alembic upgrade head

downgrade *args:
  uv --project backend run --directory backend alembic downgrade {{args}}

ruff *args:
  uv --project backend run --directory backend ruff check {{args}} app

lint:
  uv --project backend run --directory backend ruff format app
  just ruff --fix

arq:
  uv --project backend run arq backend.app.workers.crawler_worker.WorkerSettings

# docker
up:
  docker-compose up -d

kill *args:
  docker-compose kill {{args}}

build:
  docker-compose build

ps:
  docker-compose ps