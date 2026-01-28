FROM python:3.10

# Create a non-root user
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Copy requirements and install
COPY --chown=user ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the rest of the application
COPY --chown=user . /app

# Create uploads directory
RUN mkdir -p /app/uploads

# Expose port and run Gunicorn (Flask)
EXPOSE 7860

CMD ["gunicorn", "-b", "0.0.0.0:7860", "--workers", "4", "--timeout", "300", "app:app"]
