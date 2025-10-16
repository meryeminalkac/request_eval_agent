## Project Evaluation Agent (Minimal Scaffold)

A minimal, runnable FastAPI service that evaluates a project across three main metrics: impact, effort, and risk. Each main metric aggregates multiple sub-metrics scored via a stubbed prompt engine and a stub retriever.

### Requirements
- Python 3.11
- Deps: `pydantic>=2, fastapi, uvicorn, pyyaml, httpx, tenacity`

### Quickstart
1. Create and activate a virtual environment
```bash
python -m venv .venv
# Windows PowerShell
. .venv/Scripts/Activate.ps1
# macOS/Linux
# source .venv/bin/activate
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Run the API
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

4. Send a request
```bash
curl -s http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d @examples/demo_request.json | jq
```

### Optional: Use FAISS knowledge base
- Place `.txt` or `.md` files under a top-level `knowledge/` folder. If present, the service will use a FAISS-backed retriever (LangChain + `sentence-transformers`) to fetch exemplars; otherwise it falls back to a stub retriever.
- Extra dependencies are already in `requirements.txt`: `langchain-community`, `sentence-transformers`, `faiss-cpu`.

### Project Structure
- `project_eval/` core library with schemas, base classes, evaluators, and stubs
- `api/main.py` FastAPI app with `POST /score`
- Bands: `<=2.33` low, `<3.67` medium, else high. All submetrics are equally weighted.
- `examples/demo_request.json` sample request payload

### Notes
- Prompt scoring and exemplar retrieval are stubbed to deterministic behavior.
- Bands follow thresholds: `<=2.33` low, `<3.67` medium, else high.
- Future work: integrate real LLM (Azure/OpenAI) and a vector store.


