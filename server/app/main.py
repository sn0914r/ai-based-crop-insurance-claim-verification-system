import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.configs.settings import settings, get_resolved_path, ensure_directories
from app.db.session import init_db
from app.errors.app_error import AppError
import app.errors.error_codes as error_codes
from app.modules.claims.claim_routes import router as claims_router
from app.modules.weather import weather_router
from app.modules.satellite import satellite_router
from app.modules.fraud import fraud_router
from app.core.vision_engine import VisionEngine
from app.core.fraud_engine import fraud_engine
from app.core.xai_engine import xai_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    logger.info("Starting Crop Insurance AI API...")
    ensure_directories()
    init_db()
    logger.info("Database tables verified.")

    # Preload vision model in background / startup
    try:
        VisionEngine.load_model()
        logger.info("MobileNetV2 vision model loaded successfully.")
    except Exception as e:
        logger.warning(f"Vision model preload notice: {str(e)}")

    # Preload XGBoost fraud model
    try:
        if fraud_engine.model is not None:
            logger.info("XGBoost multimodal fraud model initialized successfully.")
        else:
            logger.warning("XGBoost fraud model initialized with fallback heuristics.")
    except Exception as e:
        logger.warning(f"Fraud model preload notice: {str(e)}")

    # Preload Tree SHAP explainable AI engine
    try:
        if xai_engine.booster is not None or xai_engine.model is not None:
            logger.info("Explainable AI (Tree SHAP) engine initialized successfully.")
        else:
            logger.warning("Explainable AI engine initialized with heuristic approximations.")
    except Exception as e:
        logger.warning(f"XAI engine preload notice: {str(e)}")

    yield

    # Shutdown sequence
    logger.info("Shutting down Crop Insurance AI API...")

app = FastAPI(
    title="Crop Insurance AI Assessment API",
    description="Multimodal AI-driven crop damage assessment and fraud detection system.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend applications (including VS Code Live Server on port 5500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler for AppError
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "errorCode": exc.error_code,
            "details": exc.details
        }
    )

# Exception handler for unexpected exceptions
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An internal server error occurred.",
            "errorCode": error_codes.INTERNAL_SERVER_ERROR,
            "details": str(exc)
        }
    )

# Mount static files directory for uploaded crop photographs
uploads_path = get_resolved_path(settings.UPLOADS_DIR)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

# Register API routers
app.include_router(claims_router)
app.include_router(weather_router)
app.include_router(satellite_router)
app.include_router(fraud_router)

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "service": "crop-insurance-server",
        "environment": settings.ENVIRONMENT
    }

# Mount Web Dashboard Frontend at "/"
client_candidates = [
    Path("/app/client"),
    Path(__file__).resolve().parent.parent.parent / "client",
    Path("client"),
    Path("../client")
]

client_mounted = False
for c_path in client_candidates:
    if c_path.exists() and (c_path / "index.html").exists():
        app.mount("/client", StaticFiles(directory=str(c_path), html=True), name="client_subpath")
        app.mount("/", StaticFiles(directory=str(c_path), html=True), name="client_dashboard")
        logger.info(f"Mounted Web Dashboard static files from: {c_path}")
        client_mounted = True
        break

if not client_mounted:
    @app.get("/", tags=["System"])
    def root():
        return {
            "message": "Crop Insurance AI Assessment API is running.",
            "docs": "/docs",
            "health": "/health"
        }
