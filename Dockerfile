FROM python:3.14-alpine AS build

# Match the uv version that writes uv.lock
COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /bin/uv

# setuptools-scm needs git to derive the version from .git
RUN apk add --no-cache git

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /code/
COPY . /code/
# Install the locked versions so the image matches what CI tested
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.14-alpine

RUN adduser -S app app

COPY --from=build /code/.venv /code/.venv
ENV PATH="/code/.venv/bin:$PATH"

USER app
WORKDIR /workspace/
ENTRYPOINT ["ecs-deplojo"]
