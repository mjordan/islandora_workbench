"""Sample script to process items in the Persist Queue populated by the
workbench_queue_sample_enqueue_node_id.py script.
"""

import sys
import logging
import json
import requests
import persistqueue

islandora_host = "https://islandora.dev/"
# Number of items in queue to process.
batch_size = 5

logging.basicConfig(
    filename="queue_sample.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

q = persistqueue.SQLiteAckQueue("../workbench_queue_sample", auto_commit=True)

i = 0
while i < batch_size:
    if q.empty() is True:
        sys.exit("Queue is empty.")
    item = q.get()
    if item.startswith("node/"):
        # Actions using the node ID (for example, create a Bag from the node) would happen
        # here. For this demo, we simply fetch the title of the node from Drupal and log it.
        # If successful, acknowledge the node ID to remove it from the queue. If
        # unsuccessful, leave the node ID in the queue so we can try again later.
        url = f"{islandora_host}{item}?_format=json"
        try:
            result = requests.get(url, verify=False)
            node = json.loads(result.text)
            title = node["title"][0]["value"]
            q.ack(item)
            logging.info(f'Dequeued {item} ("{title}") successfully, acknowledged it.')
        except Exception as e:
            logging.error(
                f"Could not retrieve data from {url}, HTTP response code was {result.status_code}."
            )
    else:
        logging.warning(f"Did not dequeue {item}, did not acknowledged it.")
    i += 1
