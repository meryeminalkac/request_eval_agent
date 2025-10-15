from __future__ import annotations

from typing import Dict

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(title="Form Processing API", version="0.1.0")


class FormAnswer(BaseModel):
    question: str
    answer: str


class FormAnswersRequest(BaseModel):
    answers: list[FormAnswer]


class FormAnswersResponse(BaseModel):
    question_answer_dict: Dict[str, str]


@app.post("/form-answers", response_model=FormAnswersResponse)
async def process_form_answers(request: FormAnswersRequest) -> FormAnswersResponse:
    """
    Process form answers and return a dictionary with questions as keys and answers as values.
    Handles Turkish translations by removing everything after '-' in question keys.
    
    Expected input format:
    {
        "answers": [
            {"question": "Project - Proje", "answer": "OptiMix"},
            {"question": "Company - Şirket", "answer": "EYAP"}
        ]
    }
    
    Returns:
    {
        "question_answer_dict": {
            "Project": "OptiMix",
            "Company": "EYAP"
        }
    }
    """
    try:
        # Convert list of FormAnswer objects to dictionary
        # Remove Turkish translations (everything after '-') from question keys
        question_answer_dict = {}
        for answer in request.answers:
            # Split by '-' and take only the first part (English)
            english_question = answer.question.split(' - ')[0].strip()
            question_answer_dict[english_question] = answer.answer
        
        return FormAnswersResponse(question_answer_dict=question_answer_dict)
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing form answers: {str(e)}")


if __name__ == "__main__":
	uvicorn.run(app, host="0.0.0.0", port=8080, reload=False)



