import sys

import uvicorn

from src.cli.runner import run_cli
from src.startup import prepare_database


def main() -> None:
    """Подготовить БД и запустить веб-приложение или консольный режим."""
    if "--cli" in sys.argv:
        run_cli()
        return
    prepare_database()
    uvicorn.run("src.web.app:create_app", factory=True, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
