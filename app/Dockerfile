FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 HF_HOME=/tmp/hf
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY train.py serve.py ./
CMD ["uvicorn", "serve:app", "--host", "0.0.0.0", "--port", "8000"]
