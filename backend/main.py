from pathlib import Path
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import api_router
from benchmarking.metrics import registry
from config import get_settings
from database import init_db


settings = get_settings()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger("workers.pipeline").setLevel(logging.INFO)
    logging.getLogger("services.gemini_service").setLevel(logging.INFO)


app = FastAPI(
    title="Veriti API",
    description="Privacy-first crisis signal verification",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def measure_http_request(request, call_next):
    if not (settings.performance_metrics_enabled or settings.benchmark_mode):
        return await call_next(request)

    started = registry.begin()
    response = None
    outcome = "success"
    try:
        response = await call_next(request)
        if response.status_code >= 500:
            outcome = "error"
        elif response.status_code >= 400:
            outcome = "client_error"
        return response
    except Exception:
        outcome = "error"
        raise
    finally:
        route = request.scope.get("route")
        status_code = response.status_code if response is not None else 500
        registry.finish(
            "http.request",
            started,
            outcome,
            {
                "method": request.method,
                "route": getattr(route, "path", "unmatched"),
                "status_class": f"{status_code // 100}xx",
            },
        )


@app.on_event("startup")
def startup() -> None:
    configure_logging()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    init_db()


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "veriti", "docs": "/docs"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
