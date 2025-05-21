# DataMind: Multi-Agent Data Analysis System

DataMind is a sophisticated data analysis platform that uses a hybrid agent framework built with LangGraph to analyze data intelligently.

## System Architecture

The system uses a hybrid agent framework with the following components:

1. **Planner** - Orchestrates the workflow between agents using LangGraph
2. **Research Agent** - Supplements data analysis with real-time web intelligence
3. **EDA Agent** - Generates data profiles and statistical insights
4. **Analyst Agent** - Runs analysis with code to extract key insights
5. **Data Story Agent** - Creates a comprehensive narrative from all analysis

## Setup

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Create a `.env` file with your API keys (use .env.template as a template):

```
# API Keys
PERPLEXITY_API_KEY=your_perplexity_api_key_here

# AWS/S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key_here
AWS_REGION=ap-southeast-1
AWS_BUCKET_NAME=your_bucket_name_here

# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
```

## Running the System

### Development Server

```bash
uvicorn main:app --reload
```

### Docker

Build and run using Docker:

```bash
docker build -t datamind-backend .
docker run -p 8000:8000 --env-file .env datamind-backend
```

### Test Script

To test the agent workflow without running the API server:

```bash
python test_agents.py
```

## API Endpoints

- **GET /** - API information
- **POST /analyze** - Direct file upload and analysis
- **POST /api/chat/stream/{dataset_id}** - Chat with an existing dataset
- **GET /figure/{figure_name}** - Retrieve a saved figure by name
- **API /api/datasets/...** - Dataset management endpoints

## How It Works

1. A user submits a query about a dataset
2. The Research and EDA agents run in parallel
3. The Analyst agent then processes the combined results
4. The Data Story agent creates a comprehensive narrative from all the results above
5. Results are streamed back to the user in real-time
6. Visualizations are saved and accessible via URLs

## Technologies Used

- **FastAPI** - API framework
- **LangGraph** - Agent orchestration
- **Perplexity AI** - LLM for research and analysis
- **pandas** - Data manipulation
- **Supabase** - Database storage
- **AWS S3** - File storage
- **matplotlib/seaborn** - Data visualization

## Architecture Diagram

```
┌──────────────┐     ┌─────────────────┐     ┌────────────────┐
│  API Layer   │────▶│ LangGraph State │────▶│ Agent Executor │
└──────────────┘     └─────────────────┘     └────────────────┘
       │                     │                       │
       ▼                     ▼                       ▼
┌──────────────┐  ┌──────────────────────────────────────────────┐
│  Supabase DB │  │                                              │
└──────────────┘  │  ┌────────────┐  ┌─────────────┐            │
       ▲          │  │  Research  │  │     EDA     │            │
       │          │  │   Agent    │  │    Agent    │            │
┌──────────────┐  │  └────────────┘  └─────────────┘            │
│   AWS S3     │  │         │              │                    │
└──────────────┘  │         └──────┬───────┘                    │
       ▲          │                ▼                            │
       │          │         ┌───────────┐        ┌─────────┐    │
       │          │         │  Analyst  │───────▶│  Story  │    │
       └──────────┼─────────│   Agent   │        │  Agent  │    │
                  │         └───────────┘        └─────────┘    │
                  │                                             │
                  └─────────────────────────────────────────────┘
``` 