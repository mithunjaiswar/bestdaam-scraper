import json
from pathlib import Path

from process_product_requests import update_request


RESULTS_FILE = Path("output/product_request_results.json")


def main():
    if not RESULTS_FILE.exists():
        print("No product request results to publish.")
        return

    results = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))

    for item in results:
        update_request(
            request_id=item["id"],
            status=item["status"],
            result_url=item.get("result_url", ""),
        )

    print(f"Product request statuses updated: {len(results)}")


if __name__ == "__main__":
    main()
