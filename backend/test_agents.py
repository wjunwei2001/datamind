import asyncio
import pandas as pd
import json
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
from services.agent_framework import execute_workflow

def create_health_tech_financial_data():
    """
    Create a sample financial dataset for a digital health company
    spanning 8 quarters (2 years) with multiple product lines.
    """
    # Generate consistent dates for 8 quarters
    start_date = datetime(2022, 1, 1)
    quarters = []
    for i in range(8):
        quarter_date = start_date + timedelta(days=i*90)
        quarter = f"Q{(i%4)+1} {quarter_date.year}"
        quarters.append(quarter)
    
    # Product lines
    products = ['Telemedicine', 'Remote Monitoring', 'Health Analytics', 'Mobile App']
    
    # Create data rows
    data = []
    
    # Generate financial metrics with realistic patterns
    for quarter in quarters:
        quarter_num = quarters.index(quarter)
        
        # Global company metrics with seasonal patterns and growth
        base_growth = 1.0 + (quarter_num * 0.06)  # 6% growth per quarter
        seasonal_factor = 1.0 if quarter.startswith('Q1') or quarter.startswith('Q4') else 0.9
        
        for product in products:
            # Product-specific factors
            if product == 'Telemedicine':
                product_factor = 1.2  # Strongest performer
                margin = 0.65 - (0.01 * quarter_num)  # Declining margins due to competition
                customer_acquisition = 120 - (5 * quarter_num)  # Improving CAC
                
            elif product == 'Remote Monitoring':
                product_factor = 1.0 + (quarter_num * 0.04)  # Growing product
                margin = 0.55
                customer_acquisition = 200 - (10 * quarter_num)
                
            elif product == 'Health Analytics':
                product_factor = 0.8 + (quarter_num * 0.08)  # Fastest growing from small base
                margin = 0.72
                customer_acquisition = 250 - (12 * quarter_num)
                
            else:  # Mobile App
                product_factor = 0.9
                margin = 0.82 - (0.02 * quarter_num)  # High but declining margins
                customer_acquisition = 80 - (2 * quarter_num)
            
            # Calculate metrics
            revenue = round(500000 * base_growth * seasonal_factor * product_factor * (1 + np.random.normal(0, 0.05)), 2)
            expenses = round(revenue * (1 - margin) * (1 + np.random.normal(0, 0.03)), 2)
            profit = round(revenue - expenses, 2)
            profit_margin = round(profit / revenue * 100, 2)
            new_customers = round(revenue / customer_acquisition)
            retention_rate = min(98, 85 + (quarter_num * 1.5) + np.random.normal(0, 1))
            
            # Add row
            data.append({
                'quarter': quarter,
                'product': product,
                'revenue': revenue,
                'expenses': expenses,
                'profit': profit,
                'profit_margin': profit_margin,
                'new_customers': new_customers,
                'retention_rate': retention_rate,
                'customer_acquisition_cost': customer_acquisition
            })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    return df

async def test_agent_workflow():
    """
    Test the agent workflow with financial data from a digital health company
    """
    # Load environment variables (for API keys)
    load_dotenv()
    
    # Create sample health tech financial data
    df = create_health_tech_financial_data()
    
    # Create metadata
    dataset_metadata = {
        "filename": "healthtech_financials_2022_2023.csv",
        "s3_key": "test/healthtech_financials.csv",  # This doesn't need to exist
        "sample_df": df,
        "columns": list(df.columns)
    }
    
    # Query to analyze
    query = """
    Analyze the financial performance trends across different product lines, identify which areas 
    are showing the strongest growth and profitability.
    """
    
    print(f"Testing agent workflow with query about digital health company financials")
    print("Sample data:")
    print(df.head())
    print("=" * 80)
    
    # Execute workflow and collect results
    results = []
    async for chunk in execute_workflow(query, dataset_metadata):
        print(f"Received event: {chunk}")
        if chunk.startswith("data: "):
            data_json = chunk[6:]  # Remove "data: " prefix
            try:
                data = json.loads(data_json)
                results.append(data)
            except json.JSONDecodeError:
                print(f"Error decoding JSON: {data_json}")
    
    print("=" * 80)
    print(f"Workflow complete with {len(results)} events")
    
    # Save results to test.json
    output_data = {
        "query": query,
        "metadata": {k: v for k, v in dataset_metadata.items() if k != "sample_df"},
        "events": results,
        "timestamp": datetime.now().isoformat()
    }
    
    # Handle the DataFrame separately (convert to dict)
    sample_data = df.head(10).to_dict(orient="records")
    output_data["sample_data"] = sample_data
    
    # Write to file
    with open("test.json", "w") as f:
        json.dump(output_data, f, indent=2, default=str)
    
    print(f"Results saved to test.json")
    
    # # Look for analysis results
    # for event in results:
    #     if "data" in event and "analysis_results" in event["data"]:
    #         print("\nAnalysis Results:")
    #         analysis = event["data"]["analysis_results"]
    #         print(json.dumps(analysis, indent=2))
    #         break
    
    # # Look for final story
    # for event in results:
    #     if "data" in event and "final_story" in event["data"]:
    #         print("\nFinal Story:")
    #         story = event["data"]["final_story"]
    #         print(f"Title: {story.get('title', 'N/A')}")
    #         print(f"Summary: {story.get('summary', 'N/A')}")
            
    #         if "insights" in story:
    #             print("\nKey Insights:")
    #             for insight in story["insights"]:
    #                 print(f"- {insight}")
                    
    #         if "next_steps" in story:
    #             print("\nRecommended Next Steps:")
    #             for step in story["next_steps"]:
    #                 print(f"- {step}")
            
    #         break

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_agent_workflow()) 