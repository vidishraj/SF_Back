# Backend - Customer Support Ticket Analyzer

Flask API server for ticket analysis with dual strategy support.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Add your Claude API key to .env
   ```

3. Run the server:
   ```bash
   python app.py
   ```

Server runs on http://localhost:5500

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/analysis-methods` - Available analysis methods  
- `POST /api/process-tickets` - Process tickets and return analysis

## Environment Variables

- `CLAUDE_API_KEY` - Required for LLM analysis strategy
- `FLASK_ENV` - Set to `development` for dev mode
- `PORT` - Server port (default: 5500)

## Architecture

The backend uses the Strategy Pattern with two analysis approaches:

- **Keyword Strategy**: Fast analysis using predefined categories
- **LLM Strategy**: AI-powered analysis using Claude SDK

See the main project documentation for detailed architectural decisions.