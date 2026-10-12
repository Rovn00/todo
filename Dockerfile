FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py index.html ./
RUN mkdir /data && chown -R 10001:10001 /data /app
USER 10001:10001
ENV PORT=8000 DB_PATH=/data/tasks.db PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "app.py"]
