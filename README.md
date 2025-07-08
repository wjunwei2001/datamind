# DataMind 🧠

**Chat with your data like never before**
![image](https://github.com/user-attachments/assets/2588ab34-fce5-47d4-8be1-4fc50239c61c)

DataMind is a sophisticated AI-powered data analysis platform that combines the power of multi-agent systems with an intuitive chat interface. Upload your datasets and have intelligent conversations to uncover insights, generate visualizations, and get comprehensive data stories.


## ✨ Features

### 🤖 Multi-Agent Intelligence
- **Planner Agent**: Orchestrates the entire workflow using LangGraph
- **Research Agent**: Supplements analysis with real-time web intelligence via Perplexity API
- **EDA Agent**: Generates comprehensive data profiles and statistical insights
- **Analyst Agent**: Executes code-based analysis and creates visualizations
- **Data Story Agent**: Weaves all findings into a coherent narrative

### 📊 Data Processing
- **File Support**: CSV and Excel files up to 1GB
- **Smart Analysis**: Automatic data profiling and type detection
- **Visualizations**: Auto-generated charts and plots
- **Statistical Insights**: Descriptive statistics, correlations, and patterns

### 💬 Interactive Chat
- **Natural Language**: Ask questions in plain English
- **Streaming Responses**: Real-time response generation
- **Context Aware**: Maintains conversation history
- **Data Preview**: Interactive table views with expandable details

### 🔒 Security & Privacy
- **Secure Processing**: Data processed securely and never shared with third parties
- **Cloud Storage**: AWS S3 integration for scalable file storage
- **Database**: Supabase integration for metadata and session management

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   External      │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   Services      │
│                 │    │                 │    │                 │
│ • Chat UI       │    │ • Multi-Agent   │    │ • Perplexity    │
│ • File Upload   │    │   Framework     │    │ • AWS S3        │
│ • Data Preview  │    │ • LangGraph     │    │ • Supabase      │
│ • Visualizations│    │ • API Endpoints │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Tech Stack

**Frontend:**
- Next.js 15 with TypeScript
- TailwindCSS for styling
- React Hooks for state management
- Markdown rendering for responses

**Backend:**
- FastAPI for high-performance APIs
- LangGraph for agent orchestration
- Pandas for data manipulation
- YData Profiling for EDA
- Matplotlib/Seaborn for visualizations

**Infrastructure:**
- AWS S3 for file storage
- Supabase for database
- Perplexity API for research
- Docker for containerization

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/wjunwei2001/datamind.git
cd datamind
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.template .env
# Edit .env with your API keys and configuration
```

### 3. Frontend Setup
```bash
cd frontend/datamind

# Install dependencies
npm install

# Create environment file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

### 4. Run the Application
```bash
# Terminal 1: Start backend
cd backend
uvicorn main:app --reload

# Terminal 2: Start frontend
cd frontend/datamind
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# API Keys
PERPLEXITY_API_KEY=your_perplexity_api_key_here

# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=your-aws-region
AWS_BUCKET_NAME=your-s3-bucket-name

# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## 📖 Usage

### 1. Upload Your Dataset
- Drag and drop or browse for CSV, Excel, or Parquet files
- Files up to 1GB are supported
- Provide context about your dataset for better analysis

### 2. Start Chatting
- Ask questions in natural language
- Examples:
  - "What are the main trends in this data?"
  - "Show me the correlation between sales and marketing spend"
  - "Create a visualization of customer segments"
  - "What insights can you find about seasonal patterns?"

### 3. Explore Results
- View auto-generated visualizations
- Read comprehensive data stories
- Access statistical summaries
- Download generated figures


## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🙏 Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) for agent orchestration
- [Perplexity AI](https://www.perplexity.ai/) for research capabilities
- [YData Profiling](https://github.com/ydataai/ydata-profiling) for EDA
- [Next.js](https://nextjs.org/) for the frontend framework
- [FastAPI](https://fastapi.tiangolo.com/) for the backend API

## 📞 Support

- 📧 Email: wangjunwei38@gmail.com
- 🐛 Issues: [GitHub Issues](https://github.com/wjunwei2001/datamind/issues)

---


*Transform your data into insights with the power of AI*
