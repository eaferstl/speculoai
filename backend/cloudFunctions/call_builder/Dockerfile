# Use the official Python image as the base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the function code into the container
COPY . .

# Set environment variables
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json
ENV ENVIRONMENT=production
ENV PROJECT_ID=heyisaai
ENV CONFIG_BUCKET=heyisaai
ENV BLAND_AI_URL=https://isa.bland.ai/v1/calls

# Install the Functions Framework
RUN pip install functions-framework

# Expose the port the app runs on
EXPOSE 8080

# Run the application
CMD ["functions-framework", "--target=call_builder", "--port=8080"]