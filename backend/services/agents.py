from crewai import Agent, Task, Crew
from langchain.tools import tool
import pandas as pd
from typing import Dict, Any

class DataAnalysisTools:
    @tool("Analyze CSV Data")
    def analyze_csv(self, csv_content: str, query: str) -> str:
        """Analyze CSV data and answer questions about it."""
        try:
            # Convert CSV content to DataFrame
            df = pd.read_csv(pd.StringIO(csv_content))
            
            # Basic analysis based on query
            if "summary" in query.lower():
                return f"Dataset Summary:\n{df.describe().to_string()}"
            elif "columns" in query.lower():
                return f"Columns in dataset:\n{', '.join(df.columns)}"
            elif "rows" in query.lower():
                return f"Number of rows: {len(df)}"
            else:
                return f"Dataset has {len(df)} rows and {len(df.columns)} columns. Please ask specific questions about the data."
        except Exception as e:
            return f"Error analyzing data: {str(e)}"

def create_data_analyst_agent() -> Agent:
    """Create a data analyst agent with analysis tools."""
    tools = DataAnalysisTools()
    
    return Agent(
        role='Data Analyst',
        goal='Analyze data and provide clear, accurate insights',
        backstory="""You are an expert data analyst with years of experience in 
        analyzing datasets and providing clear insights. You excel at understanding 
        data patterns and communicating findings effectively.""",
        tools=[tools.analyze_csv],
        verbose=True
    )

def analyze_data(csv_content: str, user_query: str) -> Dict[str, Any]:
    """Analyze data using CrewAI agents."""
    # Create the data analyst agent
    analyst = create_data_analyst_agent()
    
    # Create a task for the agent
    analysis_task = Task(
        description=f"""Analyze the following CSV data and answer this question: {user_query}
        CSV Data:
        {csv_content}""",
        agent=analyst
    )
    
    # Create and run the crew
    crew = Crew(
        agents=[analyst],
        tasks=[analysis_task],
        verbose=True
    )
    
    # Execute the analysis
    result = crew.kickoff()
    
    return {
        "analysis": result,
        "status": "success"
    } 