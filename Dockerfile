FROM python:3.12-slim

RUN pip install uv

WORKDIR /app

COPY pyproject.toml .python-version .env ./

RUN uv sync && uv pip install --system -e .

COPY main.py auth.py ./main.py ./auth.py

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
