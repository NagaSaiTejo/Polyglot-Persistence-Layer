import json
import os
import logging
from psycopg2.errors import UniqueViolation
from .ingest import RETRY_QUEUE_FILE
from .database import get_postgres_connection, get_mongo_client

logger = logging.getLogger(__name__)

def run_reconciliation():
    if not os.path.exists(RETRY_QUEUE_FILE):
        return

    logger.info("Running reconciliation process...")
    
    remaining_events = []
    pg_conn = get_postgres_connection()
    mongo_client = get_mongo_client()
    
    try:
        with open(RETRY_QUEUE_FILE, 'r') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            payload = event['payload']
            timestamp = event['timestamp']
            
            # Check package status
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
                logger.info(f"Reconciling deferred billing event for invoice {payload['invoice_id']}")
                try:
                    with pg_conn.cursor() as cur:
                        try:
                            cur.execute("""
                                INSERT INTO invoices (invoice_id, package_id, customer_id, amount, event_timestamp)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (payload['invoice_id'], payload['package_id'], payload['customer_id'], payload['amount'], timestamp))
                            pg_conn.commit()
                        except UniqueViolation:
                            pg_conn.rollback()
                            logger.error(f"Duplicate billing record ignored during reconciliation for invoice {payload['invoice_id']}")
                except Exception as e:
                    logger.error(f"Error during reconciliation insert: {e}")
                    remaining_events.append(event)
            else:
                remaining_events.append(event)
                
    finally:
        pg_conn.close()
        mongo_client.close()
        
    # Rewrite the queue with remaining events
    with open(RETRY_QUEUE_FILE, 'w') as f:
        for ev in remaining_events:
            f.write(json.dumps(ev) + '\n')
    logger.info("Reconciliation complete.")
