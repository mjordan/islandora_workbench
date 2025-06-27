#!/usr/bin/env python

"""Sample Islandora Workbrench post-action hook script to populate a
Persist Queue queue with node IDs.
"""

import sys
import json
import persistqueue

http_response_code = sys.argv[2]
http_response_body = sys.argv[3]
entity = json.loads(http_response_body)

if http_response_code == "201":
    node_id = entity["nid"][0]["value"]
    q = persistqueue.SQLiteAckQueue("workbench_queue_sample", auto_commit=True)
    q.put(f"node/{node_id}")
