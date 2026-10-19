FROM python:3.14-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi==0.135.1 \
    uvicorn==0.41.0

COPY --from=app_context src /app/src

USER 65532:65532
EXPOSE 8080

CMD ["uvicorn", "src.apis.examples.python.get_widgets:app", "--host", "0.0.0.0", "--port", "8080"]
