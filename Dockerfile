# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Define environment variable to pass secrets (example)
# ENV SCRAPINGBEE_API_KEY=your_api_key_here 
# Note: It's better to pass secrets at runtime, not build time.

# Run scrape_ui.py when the container launches
CMD ["streamlit", "run", "scrape_ui.py"]
