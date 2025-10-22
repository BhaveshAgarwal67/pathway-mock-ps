# Use the official Pathway image as the base, which is already optimized
# for the underlying Rust engine used by the library.
FROM pathwaycom/pathway:latest

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY app.py .

# Command to run the Pathway application
# This is the entry point that will execute the python script
CMD ["python", "./app.py"]