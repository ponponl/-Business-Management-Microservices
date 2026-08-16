from fastapi import FastAPI

app = FastAPI(title="Payment Service")

@app.get("/")
def read_root():
    return {"service": "Payment Service", "status": "active"}