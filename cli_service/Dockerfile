FROM python:3.11-slim

WORKDIR /app
COPY cli.py .
RUN pip install requests

CMD ["python", "cli.py"]
