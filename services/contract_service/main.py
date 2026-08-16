from fastapi import FastAPI

app = FastAPI(title="Contract Service")

@app.get("/")
def read_root():
    return {"service": "Contract Service", "status": "active"}