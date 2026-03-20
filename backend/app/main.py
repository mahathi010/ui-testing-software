"""ui_testing_software service entry point."""

from fastapi import FastAPI

app = FastAPI(title="ui_testing_software")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ui_testing_software"}
