import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import MOCK_MODE
from app.database import init_db
from app.routers import upload, jobs, review, download

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    mode = "MOCK" if MOCK_MODE else "LIVE"
    logger.info(f"Rokt Creative Audit started in {mode} mode")
    yield


app = FastAPI(title="Rokt Creative Audit", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(upload.router)
app.include_router(jobs.router)
app.include_router(review.router)
app.include_router(download.router)


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "mock_mode": MOCK_MODE,
    })


@app.get("/jobs/{job_id}")
async def job_detail_page(request: Request, job_id: int):
    return templates.TemplateResponse("job_detail.html", {
        "request": request,
        "job_id": job_id,
        "mock_mode": MOCK_MODE,
    })


@app.get("/review/{job_id}")
async def review_page(request: Request, job_id: int):
    return templates.TemplateResponse("review.html", {
        "request": request,
        "job_id": job_id,
        "mock_mode": MOCK_MODE,
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
