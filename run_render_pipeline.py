"""Run the ETL and dbt models on Render using its DATABASE_URL setting."""

import os
import shutil
import subprocess
import sys
from urllib.parse import urlparse


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    parsed = urlparse(database_url)
    os.environ["PGHOST"] = parsed.hostname or ""
    os.environ["PGPORT"] = str(parsed.port or 5432)
    os.environ["PGUSER"] = parsed.username or ""
    os.environ["PGPASSWORD"] = parsed.password or ""
    os.environ["POSTGRES_PASSWORD"] = parsed.password or ""
    os.environ["PGDATABASE"] = parsed.path.lstrip("/")

    subprocess.run([sys.executable, "-m", "src.pipeline"], check=True)
    dbt = shutil.which("dbt")
    if not dbt:
        raise RuntimeError("dbt executable was not installed from requirements-render.txt")
    subprocess.run(
        [dbt, "build", "--project-dir", "dbt", "--profiles-dir", "dbt"],
        check=True,
    )


if __name__ == "__main__":
    main()
