import json
import os
import logging
from psycopg2.errors import UniqueViolation
from .database import get_postgres_connection, get_mongo_client, get_neo4j_driver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RETRY_QUEUE_FILE = 'retry_queue.json'

def append_to_retry_queue(event):
    logger.info(f"Appending to retry queue: {event}")
    with open(RETRY_QUEUE_FILE, 'a') as f:
        f.write(json.dumps(event) + '\n')

def handle_driver_location_update(payload, timestamp, driver):
    query = """
    MERGE (d:Driver {driverId: $driver_id})
    SET d.latitude = $lat, d.longitude = $lon, d.last_updated = $timestamp
    MERGE (z:Zone {zoneId: $zone_id})
    MERGE (d)-[:LOCATED_IN]->(z)
    """
    with driver.session() as session:
        session.run(query, 
                    driver_id=payload['driver_id'], 
                    lat=payload['location']['lat'], 
                    lon=payload['location']['lon'], 
                    zone_id=payload['zone_id'],
                    timestamp=timestamp)
    logger.info(f"Graph DB updated for driver {payload['driver_id']}")

def handle_package_status_change(payload, timestamp, mongo_client):
    db = mongo_client.logistics
    packages = db.packages
    status_entry = {
        "status": payload['status'],
        "timestamp": timestamp,
        "location": payload.get('location'),
        "driver_id": payload.get('driver_id')
    }
    
    packages.update_one(
        {"package_id": payload['package_id']},
        {"$push": {"status_history": status_entry}},
        upsert=True
    )
    logger.info(f"Document DB updated for package {payload['package_id']}")

def handle_billing_event(payload, timestamp, pg_conn, mongo_client):
    # Check if package is delivered
    db = mongo_client.logistics
    packages = db.packages
    package = packages.find_one({"package_id": payload['package_id']})
    
    is_delivered = False
    if package and 'status_history' in package:
        for status in package['status_history']:
            if status['status'] == 'DELIVERED':
                is_delivered = True
                break

    if is_delivered:
        try:
            with pg_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO invoices (invoice_id, package_id, customer_id, amount, event_timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                """, (payload['invoice_id'], payload['package_id'], payload['customer_id'], payload['amount'], timestamp))
            pg_conn.commit()
            logger.info(f"Relational DB inserted billing for invoice {payload['invoice_id']}")
        except UniqueViolation:
            pg_conn.rollback()
            logger.error(f"Duplicate billing record ignored for invoice {payload['invoice_id']}")
    else:
        logger.warning(f"Package {payload['package_id']} not DELIVERED. Queuing billing event.")
        # Reconstruct the full event for the queue
        event = {
            "timestamp": timestamp,
            "type": "BILLING_EVENT",
            "payload": payload
        }
        append_to_retry_queue(event)

def process_event_file(filepath="events.log"):
    if not os.path.exists(filepath):
        logger.error(f"Event file {filepath} not found.")
        return

    pg_conn = get_postgres_connection()
    mongo_client = get_mongo_client()
    neo4j_driver = get_neo4j_driver()

    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    event_type = event.get('type')
                    payload = event.get('payload')
                    timestamp = event.get('timestamp')

                    if event_type == 'DRIVER_LOCATION_UPDATE':
                        handle_driver_location_update(payload, timestamp, neo4j_driver)
                    elif event_type == 'PACKAGE_STATUS_CHANGE':
                        handle_package_status_change(payload, timestamp, mongo_client)
                    elif event_type == 'BILLING_EVENT':
                        handle_billing_event(payload, timestamp, pg_conn, mongo_client)
                    else:
                        logger.warning(f"Unknown event type: {event_type}")

                except json.JSONDecodeError:
                    logger.error(f"Malformed JSON line: {line}")
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
    finally:
        pg_conn.close()
        mongo_client.close()
        neo4j_driver.close()
