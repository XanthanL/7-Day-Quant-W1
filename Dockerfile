# Use a slim Python base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install dependencies
# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Copy the application code
# Exclude quant.db, venv, .git etc. using .dockerignore
COPY src/ ./src/
COPY main.py .
COPY app.py .
COPY README.md .
# If there are other essential files like scripts/migrate_csv_to_db.py, include them
# Assuming scripts/ is also needed, as migrate_csv_to_db.py could be run manually in container
COPY scripts/ ./scripts/
COPY LICENSE .

# Expose the port Streamlit runs on
EXPOSE 8501

# Command to run the Streamlit application
CMD ["streamlit", "run", "app.py"]