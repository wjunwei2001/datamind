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

2. Create a `.env` file with your API keys:

```
PERPLEXITY_API_KEY=your_perplexity_api_key
S3_BUCKET=your_s3_bucket  # If using S3
```

## Running the System

### Development Server

```bash
uvicorn main:app --reload
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
- **API /api/datasets/...** - Dataset management endpoints

## How It Works

1. A user submits a query about a dataset
2. The LangGraph workflow routes the query through all agents in sequence
3. Each agent contributes its specialty to the analysis
4. The final story agent creates a comprehensive narrative from all the results
5. Results are streamed back to the user in real-time

## Technologies Used

- **FastAPI** - API framework
- **LangGraph** - Agent orchestration
- **Perplexity AI** - LLM for research and analysis
- **pandas** - Data manipulation
- **ydata-profiling** - Exploratory data analysis

## Architecture Diagram

```
┌──────────────┐     ┌─────────────────┐     ┌────────────────┐
│  API Layer   │────▶│ LangGraph State │────▶│ Agent Executor │
└──────────────┘     └─────────────────┘     └────────────────┘
                             │                       │
                             ▼                       ▼
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  ┌────────────┐  ┌─────────────┐  ┌───────────┐  ┌─────────┐ │
│  │  Research  │  │     EDA     │  │  Analyst  │  │  Story  │ │
│  │   Agent    │  │    Agent    │  │   Agent   │  │  Agent  │ │
│  └────────────┘  └─────────────┘  └───────────┘  └─────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
``` 