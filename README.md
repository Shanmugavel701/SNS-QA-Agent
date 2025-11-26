# SNS Square - QA Agent

AI-powered content quality assurance tool for Instagram, YouTube, and Blog posts.

## Features

- ✅ AI Content Review
- 📊 Hashtag Optimization
- 📈 Engagement Prediction
- 🔍 SEO Analysis

## Tech Stack

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: FastAPI (Python)
- **AI**: Google Gemini 2.5 Flash

## Local Development

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

### Frontend
```bash
cd frontend
python3 -m http.server 8080
```

## Environment Variables

Create a `.env` file in the `backend` directory:

```
GEMINI_API_KEY=your_api_key_here
```

## Deployment

This project is configured for deployment on Vercel.

## License

© 2025 SNS Square. All rights reserved.
