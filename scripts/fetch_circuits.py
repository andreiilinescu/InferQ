import os
import json
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from tqdm import tqdm
from utils.azure_connection import AzureConnection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("fetch_circuits.log")],
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = "fetched_data"
CHECKPOINT_FILE = os.path.join(OUTPUT_DIR, "checkpoint.json")
PAGE_SIZE = 1000  # Azure Table Storage limit is 1000


def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        logger.info(f"Created output directory: {OUTPUT_DIR}")


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Checkpoint file corrupted. Starting over.")
            return None
    return None


def save_checkpoint(continuation_token, file_counter, total_rows):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(
            {
                "continuation_token": continuation_token,
                "file_counter": file_counter,
                "total_rows": total_rows,
                "last_updated": datetime.now().isoformat(),
            },
            f,
        )


def fetch_data():
    ensure_output_dir()

    checkpoint = load_checkpoint()
    continuation_token = None
    file_counter = 0
    total_rows = 0

    if checkpoint:
        continuation_token = checkpoint.get("continuation_token")
        file_counter = checkpoint.get("file_counter", 0)
        total_rows = checkpoint.get("total_rows", 0)
        logger.info(
            f"Resuming from checkpoint. File counter: {file_counter}, Rows fetched so far: {total_rows}"
        )
    else:
        logger.info("Starting new fetch job.")

    try:
        azure_conn = AzureConnection()
        table_client = azure_conn.get_circuits_table_client()

        logger.info(f"Querying Azure Table 'circuits' with page size {PAGE_SIZE}...")

        # query_entities returns an ItemPaged object
        query = table_client.query_entities(
            query_filter="PartitionKey eq 'circuits'", results_per_page=PAGE_SIZE
        )

        # Get iterator with continuation token if available
        pages = query.by_page(continuation_token=continuation_token)

        # Iterate over pages
        for page in tqdm(pages, desc="Fetching pages", unit="page"):
            # Convert page to list of dicts
            rows = [dict(item) for item in page]

            if not rows:
                logger.info("Empty page received. Stopping.")
                break

            # Convert to DataFrame
            df = pd.DataFrame(rows)

            # Clean up data to avoid PyArrow errors
            # Replace string "None" with np.nan which PyArrow can handle in numeric columns
            df = df.replace("None", np.nan)

            # Save to Parquet
            output_file = os.path.join(
                OUTPUT_DIR, f"circuits_part_{file_counter:05d}.parquet"
            )

            # Ensure we handle potential data type issues for Parquet
            # Convert object columns that might contain mixed types to string if needed,
            # but pandas usually handles it.
            # Azure Table entities can have different schemas per row, so we might have sparse columns.
            # Parquet handles sparse data well.

            df.to_parquet(output_file, index=False)
            logger.info(f"Saved {len(rows)} rows to {output_file}")

            total_rows += len(rows)
            file_counter += 1

            # Get the continuation token for the NEXT page
            next_token = pages.continuation_token

            if next_token:
                save_checkpoint(next_token, file_counter, total_rows)
            else:
                # No more pages
                logger.info("Fetching complete. No more continuation token.")
                if os.path.exists(CHECKPOINT_FILE):
                    os.remove(CHECKPOINT_FILE)
                break

        logger.info(f"Total rows fetched: {total_rows}")

    except Exception as e:
        logger.error(f"Error occurred during fetch: {e}")
        logger.info(
            "Progress has been saved to checkpoint. Run the script again to resume."
        )
        raise


if __name__ == "__main__":
    fetch_data()
