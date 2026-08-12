import datetime
import csv
import logging
import os
import mediacloud.api
from pathlib import Path
from tqdm import tqdm

import _bootstrap  # noqa: F401

from tornado_dataset import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("fetch.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

US_STATE_LOCAL = 38379429
US_NATIONAL = 34412234

# Read from the environment rather than the source, so the key never reaches git.
api_key = os.environ.get("MEDIACLOUD_API_KEY")
if not api_key:
    raise SystemExit(
        "MEDIACLOUD_API_KEY is not set — get a key from https://search.mediacloud.org/ "
        "and export it first:\n    export MEDIACLOUD_API_KEY=your-key-here"
    )
mc_search = mediacloud.api.SearchApi(api_key)

fieldnames = ['id', 'publish_date', 'title', 'url', 'language', 'media_name', 'media_url', 'indexed_date']
# Through config, so TORNADO_DATA_DIR is honoured like everywhere else.
output_dir = config.RAW_DIR / "media_cloud"
outfile = output_dir / "national_state_local_2010-2025.csv"

pagination_token = None
more_stories = True
total = 0
page_num = 0

output_dir.mkdir(parents=True, exist_ok=True)

with open(outfile, 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()

    with tqdm(desc="Fetching stories", unit="story") as pbar:
        while more_stories:
            page, pagination_token = mc_search.story_list(
                'tornado* AND (wind? OR storm? OR rain? OR damage? OR emergency)',
                start_date=datetime.date(2010, 1, 1),
                end_date=datetime.date(2025, 12, 31),
                collection_ids=[US_NATIONAL, US_STATE_LOCAL],
                pagination_token=pagination_token,
            )
            for s in page:
                writer.writerow(s)

            total += len(page)
            page_num += 1
            pbar.update(len(page))

            if page_num % 20 == 0:
                csvfile.flush()
                logger.info(f"page {page_num}: {total} stories so far")

            more_stories = pagination_token is not None

logger.info(f"Wrote {total} stories to {outfile}")