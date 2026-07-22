from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI(
    title="Invoice Validation System",
    description="Document Verification System API",
    version="0.1.0",
)

from routes.processing import router as processing_router
from services.validation_engine import validate_completeness

# Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi.staticfiles import StaticFiles

app.include_router(processing_router)

class CompletenessRequest(BaseModel):
    uploaded_doc_types: List[str]

@app.post("/validation/completeness", tags=["Validation"])
async def check_completeness(request: CompletenessRequest):
    return validate_completeness(request.uploaded_doc_types)

import os
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Invoice Validation System API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "invoice-validation-system",
        "version": "0.1.0",
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, loop="asyncio")

