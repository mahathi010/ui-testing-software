"""ui_testing_software service entry point."""

from fastapi import FastAPI

from app.ui_testing_software.login_page.api import router as login_page_router

app = FastAPI(title="ui_testing_software")

app.include_router(login_page_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ui_testing_software"}
