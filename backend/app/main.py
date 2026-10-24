from fastapi import FastAPI

app = FastAPI(title="CampusOpt API")

@app.get("/")
async def root():
    return {"message": "CampusOpt API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
