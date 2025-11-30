# Deployment Guide

## Option 1: Local Deployment

### Prerequisites
- Python 3.11+
- pip

### Steps
```bash
# 1. Clone repository
git clone <your-repo-url>
cd personal-productivity-agent

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# 5. Run the system
python src/main.py
```

## Option 2: Docker Deployment
```bash
# 1. Build Docker image
docker build -t productivity-agent -f deployment/Dockerfile .

# 2. Run container
docker run -e GOOGLE_API_KEY=your_key_here productivity-agent
```

## Option 3: Google Cloud Run (Optional)
```bash
# 1. Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/productivity-agent

# 2. Deploy to Cloud Run
gcloud run deploy productivity-agent \
  --image gcr.io/PROJECT_ID/productivity-agent \
  --platform managed \
  --region us-central1 \
  --set-env-vars GOOGLE_API_KEY=your_key_here
```

## Option 4: Vertex AI Agent Engine (Advanced)

See Google Cloud documentation for deploying to Vertex AI Agent Engine.