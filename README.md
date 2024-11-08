# Patent Analyzer Backend

This backend is a Flask application designed to analyze patent infringement risks based on provided patent IDs and company names. The application includes an OpenAI API integration for natural language processing and rate limiting for request management.

## Table of Contents
- [Patent Analyzer Backend](#patent-analyzer-backend)
  - [Table of Contents](#table-of-contents)
  - [Requirements](#requirements)
  - [Environment Variables](#environment-variables)
  - [Setup](#setup)
  - [Running The Application](#running-the-application)
    - [Create A virtualenv](#create-a-virtualenv)
    - [Enter The virtualenv](#enter-the-virtualenv)
    - [Use Pip To Install Dependencies](#use-pip-to-install-dependencies)
    - [Run Flask Locally](#run-flask-locally)
  - [Running In Docker](#running-in-docker)
    - [Build And Run Docker Image](#build-and-run-docker-image)
    - [API Endpoint](#api-endpoint)
  - [Endpoints](#endpoints)
  - [Rate Limiting](#rate-limiting)
  - [Production Deployment](#production-deployment)
    - [Example Dockerfile](#example-dockerfile)
    - [Build Production Docker Image](#build-production-docker-image)
  - [License](#license)

## Requirements

- **Python 3.7+**
- **pip** (Python package manager)

## Environment Variables

Create a `.env` file in the backend root directory to configure the necessary environment variables.

| Variable           | Description                                 | Example                  |
|--------------------|---------------------------------------------|--------------------------|
| `OPENAI_API_KEY`   | Your OpenAI API key                         | `your_openai_api_key`    |

Example `.env` file:

```
OPENAI_API_KEY=your_openai_api_key
PORT=5000
HOST=0.0.0.0
DEVELOPMENT=1 
```

## Setup
```
git clone https://github.com/IMingGarson/PIC-Backend.git
cd PIC-Backend
```

## Running The Application

### Create A virtualenv
```
python3 -m venv venv
```
### Enter The virtualenv
```
source venv/bin/activate (MacOS/Linux)
venv\Scripts\activate.bat (Windows)
```
### Use Pip To Install Dependencies
```
pip install --upgrade pip
pip install -r requirements.txt
```
### Run Flask Locally
```
python app.py
```
## Running In Docker
### Build And Run Docker Image
```
docker build -t pic-backend .
docker run --env-file .env -p 5000:5000 pic-backend
```

### API Endpoint
Request
```json
POST "http://localhost:5000/analyze"
{
  "patent_id": "US-RE49889-E1",
  "company_name": "Walmart Inc."
}
```
Response
```json
{
  "analysis_id": "1",
  "patent_id": "US-RE49889-E1",
  "company_name": "Walmart Inc.",
  "analysis_date": "2024-10-31",
  "top_infringing_products": [
    {
      "product_name": "Walmart Shopping App",
      "infringement_likelihood": "High",
      "relevant_claims": ["1", "2", "3"],
      "explanation": "Detailed infringement explanation.",
      "specific_features": "Mobile application with integrated shopping list and advertisement features"
    },
    {
      "product_name": "Walmart Grocery",
      "infringement_likelihood": "High",
      "relevant_claims": ["1", "2", "3"],
      "explanation": "Grocery app with automated list building from ads.",
      "specific_features": "Grocery app with automated list building from ads"
    }
  ],
  "overall_risk_assessment": "Both the \"Walmart Shopping App\" and \"Walmart Grocery\" have a high likelihood of patent infringement due to features involving integrated shopping lists and advertisements. Numerous claims are relevant, suggesting substantial risk, particularly concerning methods for generating shopping lists and ad integration. Both products could significantly infringe on patented functionalities related to user interaction and data management."
}
```

## Endpoints
| Method | Endpoint | Description |
| :------| :------- | :---------- |
| POST   | /analyze | Analyzes the patent for potential infringement.|

## Rate Limiting
The backend API includes rate limiting to prevent excessive requests and protect the server from potential abuse. Since the project allows unauthenticated requests, rate limiting is essential to prevent misuse by anonymous users.

* Default limit: 10 requests per hour per IP address on the `/analyze` endpoint.
* Response when limit is exceeded: HTTP 429 status code with the message `Too Many Requests.`

## Production Deployment
For production deployment, it is recommended to use a WSGI server like Gunicorn with Docker or a similar setup.
### Example Dockerfile
```
FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p files

COPY app.py .
COPY ./files/patents.json ./files
COPY ./files/company_products.json ./files
COPY ./utils ./utils

EXPOSE 5000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "300"]
```

### Build Production Docker Image
```
docker build -t pic-backend .
docker run --env-file .env -p 5000:5000 pic-backend
```

## License
MIT