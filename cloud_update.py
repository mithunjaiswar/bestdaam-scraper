import argparse
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable


def run(*parts):
    print("\n▶", " ".join(str(part) for part in parts))
    subprocess.run([str(part) for part in parts], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-dir", required=True)
    args = parser.parse_args()

    site_dir = Path(args.site_dir).resolve()
    products = site_dir / "data" / "products.json"

    if not products.exists():
        raise FileNotFoundError(products)

    os.environ["BESTDAAM_SITE_DIR"] = str(site_dir)
    os.environ["HEADLESS"] = "true"

    run(PYTHON, "hydrate_database_from_catalog.py")
    run(PYTHON, "main.py")
    run(PYTHON, "export_catalog_to_bestdaam.py")
    run(PYTHON, "apply_ekaro_api_links.py")

    if os.environ.get("SUPABASE_URL") and os.environ.get(
        "SUPABASE_SERVICE_ROLE_KEY"
    ):
        run(PYTHON, "sync_catalog_to_supabase.py")
    else:
        print("\nSupabase secrets missing: catalog GitHub par safely update hoga.")


if __name__ == "__main__":
    main()
