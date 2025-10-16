#!/usr/bin/env python3
"""
Method 3: Real API Integration
Calls your form API and uses the response with evaluators.
"""

import json
import requests
from project_eval.llm import Generator, StubLLMClient
from project_eval.evaluators import ImpactEvaluator, EffortEvaluator, RiskEvaluator


def call_form_api(api_url: str, form_data: dict) -> dict:
    """Call your form API and get the response dictionary."""
    try:
        print(f"Calling API: {api_url}")
        response = requests.post(api_url, json=form_data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        print(f"API Response received")
        
        # Extract the question_answer_dict from the response
        if "question_answer_dict" in result:
            return result["question_answer_dict"]
        else:
            print("Warning: No 'question_answer_dict' in API response")
            return {}
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API server")
        print("Make sure to start the server with: python api/main.py")
        return {}
    except Exception as e:
        print(f"Error calling API: {e}")
        return {}


def build_project_text_from_api(api_dict: dict, project_name: str) -> str:
    """Build project description text from API response dictionary."""
    text_parts = [f"Project: {project_name}"]
    
    key_mappings = {
        "Project": "Project Name",
        "Company": "Company", 
        "Project Scope & Objectives": "Scope and Objectives",
        "Business Value Contribution": "Business Value",
        "Project Stakeholders & Sponsorship": "Stakeholders",
        "Data Scope": "Data Sources"
    }
    
    for api_key, value in api_dict.items():
        if api_key in key_mappings:
            text_parts.append(f"{key_mappings[api_key]}: {value}")
        else:
            text_parts.append(f"{api_key}: {value}")
    
    return "\n".join(text_parts)


async def run_ai_evaluation(api_response_dict: dict, use_azure: bool = True):
    """Run AI evaluation on the processed form data."""
    # Choose LLM client
    if use_azure:
        try:
            llm = Generator()
            print("Using Azure OpenAI")
        except Exception as e:
            print(f"Azure OpenAI failed: {e}, using StubLLMClient")
            llm = StubLLMClient()
    else:
        llm = StubLLMClient()
        print("Using StubLLMClient")
    
    # Extract project name and build project text
    project_name = api_response_dict.get("Project", "Unknown Project")
    project_text = build_project_text_from_api(api_response_dict, project_name)
    
    print(f"Project: {project_name}")
    
    # Create evaluators
    impact_evaluator = ImpactEvaluator(llm)
    effort_evaluator = EffortEvaluator(llm)
    risk_evaluator = RiskEvaluator(llm)
    
    print("Running evaluations...")
    
    # Run evaluations
    impact_result = await impact_evaluator.evaluate_with_sources(
        project_name=project_name,
        project_text=project_text,
        evaulations=json.load(open("evaulations.json")),
        prf_answers=json.load(open("prf_answers.json")),
        staff_info=json.load(open("staff_info.json"))
    )
    
    effort_result = await effort_evaluator.evaluate_with_sources(
        project_name=project_name,
        project_text=project_text,
        evaulations=json.load(open("evaulations.json")),
        prf_answers=json.load(open("prf_answers.json")),
        staff_info=json.load(open("staff_info.json"))
    )
    
    risk_result = await risk_evaluator.evaluate_with_sources(
        project_name=project_name,
        project_text=project_text,
        evaulations=json.load(open("evaulations.json")),
        prf_answers=json.load(open("prf_answers.json")),
        staff_info=json.load(open("staff_info.json"))
    )
    
    # Display results
    print("\nEVALUATION RESULTS:")
    print("=" * 60)
    
    for result in [impact_result, effort_result, risk_result]:
        print(f"\n{result['metric'].upper()}")
        print(f"   Overall Score: {result['overall_score']}/5")
        print(f"   Band: {result['band']}")
        print(f"   Reason: {result['overall_reason']}")
        
        print("   Submetrics:")
        for sub in result['submetrics']:
            print(f"     - {sub['name']}: {sub['score']}/5 - {sub['reason']}")
    
    return {
        "impact": impact_result,
        "effort": effort_result,
        "risk": risk_result
    }


async def evaluate_form_submission(form_data: dict, api_url: str = "http://localhost:8000/form-answers", use_azure: bool = True):
    """
    Production function to evaluate a form submission.
    
    Args:
        form_data: Form data from Power Automate
        api_url: URL of your form API
        use_azure: Whether to use Azure OpenAI or StubLLMClient
    
    Returns:
        Evaluation results dictionary
    """
    print("Production AI Evaluator")
    print("=" * 50)
    
    # Step 1: Call the API to get processed form data
    print("Step 1: Processing form data...")
    api_response = call_form_api(api_url, form_data)
    
    if not api_response:
        print("Failed to get API response. Exiting.")
        return None
    
    print(f"Successfully processed form data with {len(api_response)} fields")
    
    # Step 2: Run AI evaluation
    print("\nStep 2: Running AI evaluation...")
    results = await run_ai_evaluation(api_response, use_azure=use_azure)
    
    if results:
        print("\nEvaluation completed successfully!")
        
        # Save results to file with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_results_{timestamp}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {filename}")
        
        return results
    else:
        print("Evaluation failed")
        return None


# Production-ready function - no example usage
# Use this function in your Power Automate workflow or production code

async def main():
    """Main function to run the AI evaluator with real API data."""
    import asyncio
    
    print("Production AI Evaluator")
    print("=" * 50)
    print("Getting form data from API...")
    print("Make sure your API server is running: python api/main.py")
    print()
    
    # Get real form data from your API
    api_url = "http://localhost:8000/form-answers"
    
    form_data = {
        "answers": {
        }
    }
    
    # Run evaluation with API data
    results = await evaluate_form_submission(form_data, api_url=api_url, use_azure=False)
    
    if results:
        print("\nEvaluation completed successfully!")
        return results
    else:
        print("\nEvaluation failed!")
        return None


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
