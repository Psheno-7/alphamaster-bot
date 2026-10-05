FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY alphamaster ./alphamaster
ENV DB_PATH=/data/alphamaster.db
VOLUME /data
CMD ["python", "-m", "alphamaster"]
