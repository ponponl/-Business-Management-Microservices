from fastapi import FastAPI

app = FastAPI(title="Pricing Service")

@app.get("/")
def read_root():
    return {"service": "Pricing Service", "status": "active"}