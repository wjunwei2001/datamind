import pandas as pd
from typing import Dict, Any, List, Optional
import httpx
import os
from dotenv import load_dotenv
import asyncio, inspect, json, logging
from dataclasses import dataclass, field
from datetime import datetime
from ydata_profiling import ProfileReport

load_dotenv()

@dataclass
class Task:
    role: str
    data: dict[str, Any]
    respond_to: asyncio.Queue

@dataclass
class Result:
    role: str
    content: dict[str, Any]
    ts: datetime = field(default_factory=datetime.utcnow)

class Agent:
    def __init__(self, name: str, inbox: asyncio.Queue):
        self.name, self.inbox = name, inbox
        # Common HTTP client for agents that need it
        # Can be initialized here or per-call if preferred
        self._http_client: Optional[httpx.AsyncClient] = None

    async def get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url="https://api.perplexity.ai",
                headers={"Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}"},
                timeout=20 # Increased timeout for potentially long API calls
            )
        return self._http_client

    async def close_http_client(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def run(self):
        try:
            while True:
                task = await self.inbox.get()
                if task.role != self.name:
                    await self.inbox.put(task)
                    await asyncio.sleep(0.01) # Yield control, small delay
                    continue
                try:
                    result_content = await self.handle(task.data)
                except Exception as e:
                    logging.error(f"{self.name} failed: {e}", exc_info=True)
                    result_content = {"error": str(e), "details": "Agent execution failed."}
                await task.respond_to.put(Result(self.name, result_content))
                self.inbox.task_done()
        finally:
            await self.close_http_client() # Ensure client is closed when agent stops

    async def handle(self, data: dict):   # override in child
        raise NotImplementedError
    
class ResearchAgent(Agent):
    async def handle(self, data):
        prompt = data.get("prompt", "No prompt provided.")
        s3_key = data.get("s3_key")
        # Augment prompt with s3_key if available
        if s3_key:
            prompt += f"\nConsider data from S3 object: {s3_key}"

        payload = {
            "model": "sonar-medium-online", # Explicitly using a known model
            "response_format": { "type": "json_object"}, # Simpler JSON object request
            "messages":[{"role":"user","content": prompt}],
        }
        client = await self.get_http_client()
        r = await client.post("/chat/completions", json=payload)
        r.raise_for_status()
        # Assuming content is directly the JSON object from Perplexity
        return r.json()["choices"][0]["message"]["content"]
    
class EDAAgent(Agent):
    async def handle(self, data):
        df_sample = data.get("df_sample") # Expecting a DataFrame sample
        if df_sample is None:
            return {"error": "No DataFrame sample provided for EDA"}
        
        # Ensure df_sample is a DataFrame (it might be passed as dict)
        if isinstance(df_sample, dict):
            df = pd.DataFrame.from_dict(df_sample)
        elif isinstance(df_sample, pd.DataFrame):
            df = df_sample
        else:
            return {"error": "Invalid df_sample format for EDA"}

        profile = await asyncio.to_thread(
            ProfileReport, df, minimal=True, explorative=True)
        return {"summary_html": profile.to_html(), "rows_in_sample": len(df)}
    
class Verifier(Agent):
    async def handle(self, data):
        claim = data.get("summary_to_verify", "No claim provided.")
        if claim == "No claim provided.":
             return {"ok": False, "error": "Missing summary for verification"}

        chk_payload = {
            "model":"sonar-medium-online",
            "messages":[{"role":"user",
             "content":f'Is the following claim accurate based on general knowledge and web search? "{claim}" Answer yes or no, and provide a brief explanation.'}]}
        client = await self.get_http_client()
        r = await client.post("/chat/completions", json=chk_payload)
        r.raise_for_status()
        response_content = r.json()["choices"][0]["message"]["content"]
        return {"ok": "yes" in response_content.lower(), "explanation": response_content}

class ModelAgent(Agent): # Placeholder
    async def handle(self, data: dict):
        logging.info(f"ModelAgent received data: {data.get('s3_key')}")
        # In a real scenario, load data from s3_key, train/run model
        await asyncio.sleep(2) # Simulate work
        return {"model_status": "processed placeholder", "s3_key": data.get('s3_key')}

class EvalAgent(Agent): # Placeholder
    async def handle(self, data: dict):
        logging.info(f"EvalAgent received data for evaluation")
        await asyncio.sleep(1) # Simulate work
        return {"eval_status": "evaluated placeholder"}

class Planner:
    def __init__(self):
        self.q = asyncio.Queue()
        self.out_q = asyncio.Queue()
        self.agent_instances: Dict[str, Agent] = {}

    def boot_agents(self):
        # Called once at startup
        if not self.agent_instances: # Ensure agents are booted only once
            self.agent_instances = {
                "research":  ResearchAgent("research", self.q),
                "eda":       EDAAgent("eda", self.q),
                "model":     ModelAgent("model", self.q),      # Placeholder
                "eval":      EvalAgent("eval", self.q),        # Placeholder
                "verify":    Verifier("verify", self.q),
            }
            for agent_name, agent_instance in self.agent_instances.items():
                asyncio.create_task(agent_instance.run(), name=f"Agent-{agent_name}")
            logging.info("Agents booted.")

    async def plan_and_execute(self, user_query: str, df_metadata: Dict[str, Any]):
        # This version dynamically passes results to the next relevant agent
        # For simplicity, we still define a somewhat linear plan here
        # but results can be accumulated and passed.

        s3_key = df_metadata.get("s3_key")
        df_sample_for_eda = df_metadata.get("sample_df")

        # 1. Research Task
        research_prompt = f"Regarding the dataset '{df_metadata.get('filename', 'N/A')}' (stored at {s3_key}), please research the following query: {user_query}. Provide a summary and any relevant citations or sources."
        await self.q.put(Task("research", {"prompt": research_prompt, "s3_key": s3_key}, self.out_q))
        
        # Wait for research result to use its summary for Verifier
        research_result_content = None
        eda_result_content = None

        # For a more robust system, collect results from out_q and dispatch dynamically.
        # Here, we'll make a simplified assumption about task order for now.

        # 2. EDA Task (can run in parallel with research if independent)
        if df_sample_for_eda is not None:
            await self.q.put(Task("eda", {"df_sample": df_sample_for_eda}, self.out_q))
        
        # 3. Model Task (Placeholder)
        await self.q.put(Task("model", {"s3_key": s3_key, "user_query": user_query}, self.out_q))
        
        # 4. Eval Task (Placeholder)
        # This would typically take model output and other data
        await self.q.put(Task("eval", {"s3_key": s3_key}, self.out_q))

        # 5. Verify Task (Placeholder - needs actual summary from research)
        # This part needs more sophisticated orchestration: wait for research_result,
        # then dispatch verify. For now, it will run with default data.
        # A better Planner would collect results from out_q and make decisions.
        await self.q.put(Task("verify", {"summary_to_verify": "Initial research summary will go here"}, self.out_q))

    async def stream_results(self):
        # This just streams whatever comes into out_q
        # A more advanced version could manage task dependencies and final aggregation here.
        active_tasks = 5 # Number of tasks enqueued in plan_and_execute
        tasks_completed = 0
        while tasks_completed < active_tasks:
            if self.out_q.empty() and tasks_completed < active_tasks:
                await asyncio.sleep(0.1) # Wait if queue is empty but tasks remain
                continue
            try:
                res: Result = await asyncio.wait_for(self.out_q.get(), timeout=30.0) # Timeout to prevent indefinite blocking
                yield f"data: {json.dumps(res.__dict__, default=str)}\n\n"
                self.out_q.task_done()
                tasks_completed += 1
            except asyncio.TimeoutError:
                logging.warning("Timeout waiting for result from out_q. Some tasks might be stuck.")
                # Potentially break or signal an error if this happens too often.
                break # Exit if no results for a while
            if tasks_completed == active_tasks:
                logging.info("All planned tasks have produced results.")
                break
        yield f"event: done\ndata: {{}}

" # Signal end of all planned tasks

planner = Planner()
# Agents should be booted at application startup, e.g., in main.py or when Planner is first used.
# For now, let's ensure they are booted when planner is imported.
# planner.boot_agents() # This will be called from main.py or an app event handler
