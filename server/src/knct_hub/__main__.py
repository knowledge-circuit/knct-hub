import uvicorn

from knct_hub.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "knct_hub.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
