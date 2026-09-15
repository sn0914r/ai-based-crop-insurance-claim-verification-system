import os
import uvicorn
from app.configs.settings import settings

if __name__ == "__main__":
    port = int(os.getenv("PORT", settings.PORT))
    reload_flag = (settings.ENVIRONMENT == "development")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=reload_flag
    )
