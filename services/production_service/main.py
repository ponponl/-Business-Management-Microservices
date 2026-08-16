from fastapi import FastAPI

app = FastAPI(title="Production Service")

@app.get("/")
def read_root():
    return {"service": "Production Service", "status": "active"}