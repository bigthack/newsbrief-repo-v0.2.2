from fastapi import FastAPI
from fastapi.responses import JSONResponse
from api.routers import health, users, briefs

app = FastAPI(title="NewsBrief API", version="0.1.1")

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(briefs.router, prefix="/briefs", tags=["briefs"])

@app.get("/", include_in_schema=False)
def root():
    return JSONResponse({"ok": True})
