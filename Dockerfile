FROM python:3.8-slim

ENV APP_HOME /app
WORKDIR $APP_HOME

# Install dependencies.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Service must listen to $PORT environment variable.
# This default value facilitates local development.
ENV PORT 8080

# Setting this ensures print statements and log messages
# promptly appear in Cloud Logging.
ENV PYTHONUNBUFFERED TRUE
ENV PYTHONDONTWRITEBYTECODE 1

# Copy local code to the container image.
COPY ./manage.py ./manage.py
COPY ./config ./config
COPY ./bug_tracker_v2 ./bug_tracker_v2

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
CMD exec gunicorn --bind=0.0.0.0:$PORT --workers=1 --threads=8 --timeout=0 --log-level=debug config.wsgi:application
