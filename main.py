from fastapi import FastAPI

from routers.api import router

app = FastAPI(title="Hirify Vacancy Parser")
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
