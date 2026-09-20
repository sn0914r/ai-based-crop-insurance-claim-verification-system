import logging
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

    yield

    # Shutdown sequence
    logger.info("Shutting down Crop Insurance AI API...")

app = FastAPI(
    title="Crop Insurance AI Assessment API",
    description="Multimodal AI-driven crop damage assessment and fraud detection system.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# Register routers
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

@app.get("/", tags=["System"])
def root():
    return {
        "message": "Crop Insurance AI Assessment API is running.",
        "docs": "/docs",
        "health": "/health"
    }
