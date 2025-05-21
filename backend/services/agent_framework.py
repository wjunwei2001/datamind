import pandas as pd
import httpx
import os
from dotenv import load_dotenv
import operator
import asyncio
import json
import logging
from typing import Dict, List, Any, TypedDict, Optional, Callable, Awaitable, AsyncGenerator, Annotated
from dataclasses import dataclass, field
from datetime import datetime
from ydata_profiling import ProfileReport
from pydantic import BaseModel, Field

from langchain.agents import Tool
from langgraph.graph import StateGraph, END

load_dotenv()

# Define the state for our agents
class AgentState(TypedDict):
    query: str
    dataset: Dict[str, Any]  # Metadata about the dataset
    research_results: Optional[Dict[str, Any]]
    eda_results: Optional[Dict[str, Any]]
    analysis_results: Optional[Dict[str, Any]]
    final_story: Optional[str]
    error: Optional[str]
    history: Annotated[List[Dict[str, Any]], operator.add]  # Track all agent outputs
    
# Base Agent class for shared functionality
class Agent:
    def __init__(self, name: str):
        self.name = name
        self._http_client: Optional[httpx.AsyncClient] = None

    async def get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url="https://api.perplexity.ai",
                headers={"Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}"},
                timeout=60  # Increased timeout for potentially long API calls
            )
        return self._http_client

    async def close_http_client(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            
    async def process(self, state: AgentState) -> Dict[str, Any]:
        """Process the current state and return updates to the state"""
        raise NotImplementedError("Subclasses must implement process method")
    
    def create_state_update(self, 
                            key: str, 
                            value: Any, 
                            state: AgentState) -> AgentState:
        """Helper to create a proper state update with history tracking"""
        # Add to history
        history_entry = {
            "agent": self.name,
            "timestamp": datetime.utcnow().isoformat(),
            "output": {key: value}
        }
        
        # Create state update
        update = {
            key: value,
            "history": state.get("history", []) + [history_entry]
        }
        
        return update

# Define Pydantic models for expected response formats
class Section(BaseModel):
    heading: str
    content: str

class StoryFormat(BaseModel):
    title: str = Field(description="A descriptive title for the data story")
    summary: str = Field(description="Executive summary (2-3 sentences)")
    sections: List[Section] = Field(description="Array of content sections")
    insights: List[str] = Field(description="Key bullet points of the most important findings")
    next_steps: List[str] = Field(description="Recommendations for further investigation")

class ResearchFormat(BaseModel):
    summary: str = Field(description="Comprehensive summary of research findings")
    sources: List[str] = Field(description="List of sources or citations", default=[])
    relevance: str = Field(description="Explanation of relevance to the query", default="")

class AnalysisResult(BaseModel):
    insights: Dict[str, Any] = Field(description="Key insights from the analysis")
    visualizations: Optional[Dict[str, str]] = Field(description="Base64-encoded visualizations", default=None)
    methods: List[str] = Field(description="Analysis methods used", default=[])
    code: str = Field(description="The code used for analysis")

# Research Agent implementation
class ResearchAgent(Agent):
    async def process(self, state: AgentState) -> AgentState:
        try:
            query = state.get("query", "No query provided")
            dataset = state.get("dataset", {})
            s3_key = dataset.get("s3_key")
            filename = dataset.get("filename", "N/A")
            columns = dataset.get("columns", [])
            
            # Craft research prompt
            prompt = f"""Do background research for contextual information that will complement the analysis of the user query: "{query}" on dataset '{filename}' with these columns: {columns}
            Please output a JSON with the following fields:
            - summary: A comprehensive summary of the research findings
            - sources: A list of sources or citations
            - relevance: An explanation of relevance to the query
            """
            
            # Call Perplexity API
            payload = {
                "model": "sonar",
                "messages": [
                    {"role": "system", "content": "You are a research assistant helping with data analysis. Provide thorough research with sources."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"schema": ResearchFormat.model_json_schema()},
                },
            }
            
            client = await self.get_http_client()
            r = await client.post("/chat/completions", json=payload)
            r.raise_for_status()
            
            # Extract research results
            content = r.json()["choices"][0]["message"]["content"]
            
            # Could be a string or already parsed JSON
            if isinstance(content, str):
                try:
                    research_results = json.loads(content)
                except Exception as e:
                    logging.error(f"JSON parsing error: {str(e)}")
                    research_results = {"summary": content}
            else:
                research_results = content
                
            # Return state update
            return self.create_state_update("research_results", research_results, state)
            
        except Exception as e:
            logging.error(f"Research agent error: {str(e)}", exc_info=True)
            return self.create_state_update("error", f"Research failed: {str(e)}", state)
        finally:
            await self.close_http_client()

# EDA Agent implementation
class EDAAgent(Agent):
    async def process(self, state: AgentState) -> AgentState:
        try:
            dataset = state.get("dataset", {})
            df_sample = dataset.get("sample_df")
            
            if df_sample is None:
                return self.create_state_update("error", "No dataframe sample provided for EDA", state)
            
            # Convert dict to DataFrame if needed
            if isinstance(df_sample, dict):
                df = pd.DataFrame.from_dict(df_sample)
            elif isinstance(df_sample, pd.DataFrame):
                df = df_sample
            else:
                return self.create_state_update(
                    "error", 
                    f"Invalid df_sample format for EDA: {type(df_sample)}", 
                    state
                )
            
            # # Generate profile report but don't include the huge HTML in output
            # profile = ProfileReport(df, minimal=True, explorative=True)
            
            # Create a more concise summary
            eda_results = {
                # Basic dataset information
                "dataset_info": {
                    "rows": len(df),
                    "columns": len(df.columns),
                    "memory_usage": int(df.memory_usage(deep=True).sum()),
                    "missing_cells": int(df.isna().sum().sum()),
                    "duplicate_rows": int(df.duplicated().sum())
                },
                
                # Column types summary
                "column_types": {
                    "numeric": len(df.select_dtypes(include=['number']).columns),
                    "categorical": len(df.select_dtypes(include=['object', 'category']).columns),
                    "datetime": len(df.select_dtypes(include=['datetime']).columns),
                    "boolean": len(df.select_dtypes(include=['bool']).columns)
                },
                
                # Per-column information
                "columns": {
                    col: {
                        "type": str(df[col].dtype),
                        "unique_values": int(df[col].nunique()),
                        "missing": int(df[col].isna().sum()),
                        "missing_pct": float((df[col].isna().sum() / len(df)) * 100)
                    } for col in df.columns
                },
                
                # Statistical summary
                "numeric_stats": json.loads(df.describe().to_json()),
                
                # Store original column list for other agents
                "column_list": list(df.columns),
                "dtypes": df.dtypes.astype(str).to_dict()
            }
            
            # Add correlation matrix for numeric columns
            numeric_df = df.select_dtypes(include=['number'])
            if len(numeric_df.columns) > 1:
                correlations = []
                corr_matrix = numeric_df.corr().round(2)
                
                # Find top correlations
                for col1 in corr_matrix.columns:
                    for col2 in corr_matrix.columns:
                        if col1 != col2 and abs(corr_matrix.loc[col1, col2]) > 0.5:
                            correlations.append({
                                "columns": [col1, col2],
                                "correlation": float(corr_matrix.loc[col1, col2])
                            })
                
                eda_results["correlations"] = correlations
            
            # Add a summary text for better readability
            eda_summary = [
                f"Dataset has {eda_results['dataset_info']['rows']} rows and {eda_results['dataset_info']['columns']} columns",
                f"Column types: {eda_results['column_types']['numeric']} numeric, {eda_results['column_types']['categorical']} categorical",
            ]
            
            if df.isna().sum().sum() > 0:
                eda_summary.append(f"Contains {eda_results['dataset_info']['missing_cells']} missing values")
            
            eda_results["summary"] = ". ".join(eda_summary)
            
            return self.create_state_update("eda_results", eda_results, state)
            
        except Exception as e:
            logging.error(f"EDA agent error: {str(e)}", exc_info=True)
            return self.create_state_update("error", f"EDA failed: {str(e)}", state)

# Analyst Agent Implementation
class AnalystAgent(Agent):
    async def process(self, state: AgentState) -> AgentState:
        try:
            dataset = state.get("dataset", {})
            df_sample = dataset.get("sample_df")
            query = state.get("query", "")
            eda_results = state.get("eda_results", {})
            
            if df_sample is None:
                return self.create_state_update("error", "No dataframe sample provided for analysis", state)
            
            # Convert dict to DataFrame if needed
            if isinstance(df_sample, dict):
                df = pd.DataFrame.from_dict(df_sample)
            elif isinstance(df_sample, pd.DataFrame):
                df = df_sample
            else:
                return self.create_state_update(
                    "error", 
                    f"Invalid df_sample format for analysis: {type(df_sample)}", 
                    state
                )
            
            # Create prompt for code generation with improved column info
            column_info = []
            for col in df.columns:
                col_type = eda_results.get("dtypes", {}).get(col, str(df[col].dtype))
                
                # Add statistics for numeric columns
                if df[col].dtype.kind in 'if':  # integer or float
                    stats = eda_results.get("numeric_stats", {}).get(col, {})
                    col_info = f"- {col}: {col_type} (min: {stats.get('min', 'N/A')}, max: {stats.get('max', 'N/A')}, mean: {stats.get('mean', 'N/A')})"
                else:
                    # For categorical columns, show unique values count
                    unique_count = eda_results.get("columns", {}).get(col, {}).get("unique_values", df[col].nunique())
                    col_info = f"- {col}: {col_type} (unique values: {unique_count})"
                
                column_info.append(col_info)
            
            column_details = "\n".join(column_info)
            
            # Include correlation information if available
            correlation_info = ""
            if "correlations" in eda_results and eda_results["correlations"]:
                top_corrs = eda_results["correlations"][:3] if len(eda_results["correlations"]) > 3 else eda_results["correlations"]
                correlation_info = "Notable correlations:\n" + "\n".join([
                    f"- {c['columns'][0]} and {c['columns'][1]} have correlation of {c['correlation']:.2f}"
                    for c in top_corrs
                ])
            
            code_gen_prompt = f"""
            Write Python code to analyze this DataFrame that answers: {query}
            
            DataFrame summary: {eda_results.get('summary', 'No summary available')}
            
            DataFrame columns:
            {column_details}
            
            {correlation_info}
            
            Your solution must:
            - Use pandas and numpy to analyze the dataframe named 'df'
            - Be careful when dealing with dates and times.
            - Create a visualization using matplotlib or seaborn
            - Store visualization as base64 strings
            - Create a 'results' dictionary with insights
            
            IMPORTANT: Be very careful with curly braces in f-strings. Use double curly braces {{ }} to escape them in the generated code.
            
            Example output format:
            ```python
            import pandas as pd
            import matplotlib.pyplot as plt
            import seaborn as sns
            import base64
            from io import BytesIO
            
            # Analysis code here...
            
            # Create visualization
            plt.figure(figsize=(10, 6))
            # ... plotting code ...
            
            # Convert plot to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            plot_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Store results
            results = {{
                "key_insight": "Your main finding here",
                "metrics": {{"metric1": value1, "metric2": value2}},
                "plot": plot_data
            }}
            ```
            """
            
            # Call Perplexity API - for code generation we don't need the schema format
            # since we'll be executing the code directly
            payload = {
                "model": "sonar",
                "messages": [
                    {"role": "system", "content": "You are an expert data analyst who understands the data and who writes clean, efficient Python code. Generate only code, no explanations."},
                    {"role": "user", "content": code_gen_prompt}
                ]
            }
            
            client = await self.get_http_client()
            r = await client.post("/chat/completions", json=payload)
            r.raise_for_status()
            
            # Extract code from response
            response_content = r.json()["choices"][0]["message"]["content"]
            
            # Strip any markdown formatting if present
            analysis_code = response_content.strip()
            if analysis_code.startswith("```python"):
                analysis_code = analysis_code[len("```python"):].strip()
            if analysis_code.startswith("```"):
                analysis_code = analysis_code[3:].strip()
            if analysis_code.endswith("```"):
                analysis_code = analysis_code[:-3].strip()
            
            # Pre-validate the code - check for common string formatting issues
            if "%" in analysis_code and not "%%" in analysis_code:
                # Check for potentially problematic % string formatting
                logging.warning("Potentially unsafe string formatting with % detected in generated code")
                
                # Try to fix common string formatting issues
                analysis_code = analysis_code.replace("%s", "{}")
                analysis_code = analysis_code.replace("%d", "{}")
                analysis_code = analysis_code.replace("%f", "{}")
            
            # Execute the code in a safe environment
            # This needs proper sandboxing in production!
            try:
                # Setup local environment with common packages
                import matplotlib
                matplotlib.use('Agg')  # Set non-interactive backend
                import matplotlib.pyplot as plt
                import seaborn as sns
                import numpy as np
                import io as python_io
                import base64
                
                local_vars = {
                    "df": df.copy(), 
                    "pd": pd,
                    "plt": plt,
                    "sns": sns,
                    "np": np, 
                    "io": python_io,
                    "base64": base64
                }
                
                # Add safety code to handle date columns properly
                try:
                    # Check if "date" column exists
                    if "date" in df.columns:
                        # Convert date column to datetime properly
                        local_vars["df"]["date"] = pd.to_datetime(df["date"], errors="coerce")

                except Exception as prep_error:
                    logging.warning(f"Error during dataframe preparation: {prep_error}")
                
                # Execute the code with a timeout
                exec(analysis_code, {}, local_vars)
                
                # Extract results
                results = local_vars.get("results", "No results found")
                
                # Save the figures to disk if they exist
                image_paths = {}
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                figures_dir = "figures"
                
                # Create figures directory if it doesn't exist
                os.makedirs(figures_dir, exist_ok=True)
                
                # Check if there are base64 encoded images in the results
                if isinstance(results, dict):
                    for key, value in results.items():
                        if isinstance(value, str) and value.startswith('data:image') or key == 'plot':
                            # Extract the base64 data
                            base64_data = value
                            if ',' in base64_data:
                                base64_data = base64_data.split(',')[1]
                            
                            # Generate filename
                            img_filename = f"{figures_dir}/{timestamp}_{key}.png"
                            
                            # Decode and save the image
                            try:
                                with open(img_filename, "wb") as img_file:
                                    img_file.write(base64.b64decode(base64_data))
                                image_paths[key] = img_filename
                                print(f"Saved figure to {img_filename}")
                            except Exception as e:
                                logging.error(f"Error saving image {key}: {str(e)}")
                
                # Also save any open matplotlib figures
                try:
                    figures = [plt.figure(i) for i in plt.get_fignums()]
                    for i, fig in enumerate(figures):
                        fig_filename = f"{figures_dir}/{timestamp}_figure_{i}.png"
                        fig.savefig(fig_filename)
                        image_paths[f"figure_{i}"] = fig_filename
                        print(f"Saved open figure to {fig_filename}")
                except Exception as e:
                    logging.error(f"Error saving open matplotlib figures: {str(e)}")
                
                # Close all figures to prevent memory leaks
                plt.close('all')
                
                # Return analysis results
                analysis_results = {
                    "insights": results,
                    "code": analysis_code,
                    "status": "success",
                    "saved_figures": image_paths
                }
                
                return self.create_state_update("analysis_results", analysis_results, state)
                
            except SyntaxError as e:
                # Syntax error in the code
                logging.error(f"Syntax error in generated code: {str(e)}")
                return self.create_state_update(
                    "analysis_results", 
                    {"error": f"Syntax error: {str(e)}", "code": analysis_code, "status": "failed"}, 
                    state
                )
            except Exception as e:
                # Other execution error
                logging.error(f"Code execution error: {str(e)}", exc_info=True)
                
                # Try to provide more specific error messaging for common issues
                error_msg = str(e)
                if "format" in error_msg.lower():
                    error_msg = f"String formatting error: {str(e)}. This is likely due to an issue with f-strings or string formatting."
                
                return self.create_state_update(
                    "analysis_results", 
                    {"error": error_msg, "code": analysis_code, "status": "failed"}, 
                    state
                )
            
        except Exception as e:
            logging.error(f"Analyst agent error: {str(e)}", exc_info=True)
            return self.create_state_update("error", f"Analysis failed: {str(e)}", state)
        finally:
            await self.close_http_client()

# Data Story Agent Implementation
class DataStoryAgent(Agent):
    async def process(self, state: AgentState) -> AgentState:
        try:
            query = state.get("query", "")
            research_results = state.get("research_results", {})
            eda_results = state.get("eda_results", {})
            analysis_results = state.get("analysis_results", {})
            
            # Get the dataset information
            dataset = state.get("dataset", {})
            dataset_name = dataset.get("filename", "the dataset")
            
            # Extract EDA summary for prompt
            eda_summary = eda_results.get("summary", "No EDA summary available")
            
            # Prepare correlation insights if available
            correlation_insights = ""
            if "correlations" in eda_results and eda_results["correlations"]:
                top_correlations = sorted(
                    eda_results["correlations"], 
                    key=lambda x: abs(x["correlation"]), 
                    reverse=True
                )[:3]  # Get top 3
                
                correlation_insights = "Notable correlations: " + "; ".join([
                    f"{c['columns'][0]} and {c['columns'][1]} ({c['correlation']:.2f})"
                    for c in top_correlations
                ])
            
            # Create the prompt for generating the data story
            story_prompt = f"""
            Create a comprehensive data story that answers the query: "{query}"
            
            Use these inputs:
            
            1. BACKGROUND RESEARCH:
            {research_results.get('summary', 'No research available')}
            
            2. DATA PROFILE:
            {eda_summary}
            {correlation_insights}
            
            3. DATA ANALYSIS:
            {analysis_results.get('insights', 'No analysis available')}
            
            Your data story should:
            - Start with a clear executive summary
            - Include key findings from the analysis
            - Connect the research context to the data insights
            - Be structured and easy to follow
            - Suggest potential next steps or further analyses
            
            Output a JSON object exactly matching the requested schema format.
            """
            
            # Call Perplexity API with JSON schema response format
            payload = {
                "model": "sonar",
                "messages": [
                    {"role": "system", "content": "You are an expert data analyst creating insightful data stories for someone who is relying on you for insights and analysis. Generate business value for the user."},
                    {"role": "user", "content": story_prompt}
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"schema": StoryFormat.model_json_schema()},
                },
            }
            
            client = await self.get_http_client()
            r = await client.post("/chat/completions", json=payload)
            r.raise_for_status()
            
            # Extract story content
            content = r.json()["choices"][0]["message"]["content"]
            
            # Parse content if it's a string
            if isinstance(content, str):
                try:
                    story = json.loads(content)
                except Exception as e:
                    logging.error(f"JSON parsing error: {str(e)}")
                    story = {"error": "Failed to parse story JSON", "raw_content": content}
            else:
                story = content
            
            return self.create_state_update("final_story", story, state)
            
        except Exception as e:
            logging.error(f"Data Story agent error: {str(e)}", exc_info=True)
            return self.create_state_update("error", f"Story generation failed: {str(e)}", state)
        finally:
            await self.close_http_client()

# Planner implementation for LangGraph
def planner(state: AgentState) -> str:
    """Determines which agent to call next based on current state"""
    
    # If there's an error, stop the workflow
    if state.get("error"):
        logging.error(f"Workflow stopped due to error: {state.get('error')}")
        return END
    
    # Determine which stage to run next
    if "research_results" not in state:
        return "research"
    
    if "eda_results" not in state:
        return "eda"
    
    if "analysis_results" not in state:
        return "analysis"
    
    if "final_story" not in state:
        return "story"
    
    # All tasks completed
    return END

# Build the workflow graph
def build_agent_graph() -> StateGraph:
    """Constructs the agent workflow graph"""
    
    # Create the graph with our state type
    workflow = StateGraph(AgentState)
    
    # Add all agent nodes
    workflow.add_node("research", ResearchAgent("research").process)
    workflow.add_node("eda", EDAAgent("eda").process)
    workflow.add_node("analysis", AnalystAgent("analysis").process)
    workflow.add_node("story", DataStoryAgent("story").process)

    workflow.add_node("start", lambda state: state)
    
    workflow.add_edge("start", "research")
    workflow.add_edge("start", "eda")

    workflow.add_edge(["research", "eda"], "analysis")
    workflow.add_edge("analysis", "story")

    # # Add conditional edges from start and between nodes
    # workflow.add_conditional_edges("start", planner)
    # workflow.add_conditional_edges("research", planner)
    # workflow.add_conditional_edges("eda", planner)
    # workflow.add_conditional_edges("analysis", planner)
    # workflow.add_conditional_edges("story", planner)
    
    # Set the entry point to the first node directly
    workflow.set_entry_point("start")
    
    return workflow

# Graph instance
agent_graph = build_agent_graph().compile()

# Async function to execute the workflow
async def execute_workflow(query: str, dataset_metadata: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """
    Executes the agent workflow and yields results as a stream
    """
    # Initialize state
    initial_state: AgentState = {
        "query": query,
        "dataset": dataset_metadata,
        "research_results": None,
        "eda_results": None, 
        "analysis_results": None,
        "final_story": None,
        "error": None,
        "history": []
    }
    
    # Stream updates
    try:
        async for event in agent_graph.astream(initial_state):
            # Convert to JSON string and yield for streaming
            event_json = json.dumps({
                "data": event,
                "timestamp": datetime.utcnow().isoformat()
            }, default=str)
            
            yield f"data: {event_json}\n\n"
            
        # Signal completion
        yield "event: done\ndata: {}\n\n"
        
    except Exception as e:
        logging.error(f"Error in agent workflow: {str(e)}", exc_info=True)
        error_json = json.dumps({
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
        yield f"data: {error_json}\n\n"
        yield "event: done\ndata: {}\n\n" 