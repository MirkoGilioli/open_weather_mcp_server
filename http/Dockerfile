# Use the official Python lightweight image
FROM python:3.13-slim

# Install the project into /app
COPY . /app
WORKDIR /app

# Install dependencies
RUN pip install -r requirements.txt

EXPOSE 8080

# Run the FastMCP server
CMD ["python", "mcp_server.py"]
