from ninja import NinjaAPI

from .routers.health import router as health_router

api = NinjaAPI(
    title="DSA40 Application Helper", version="1.0.0", urls_namespace="api-v1"
)


api.add_router("/health", health_router)
