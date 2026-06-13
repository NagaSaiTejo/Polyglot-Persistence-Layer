from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from .database import get_postgres_connection, get_mongo_client, get_neo4j_driver

router = APIRouter()

@router.get("/query/package/{package_id}")
def query_package(package_id: str):
    mongo_client = get_mongo_client()
    pg_conn = get_postgres_connection()
    neo4j_driver = get_neo4j_driver()
    
    combined_history = []
    
    try:
        # 1. Document Store Query
        db = mongo_client.logistics
        package = db.packages.find_one({"package_id": package_id})
        
        driver_id_for_graph = None
        if package and 'status_history' in package:
            for status in package['status_history']:
                combined_history.append({
                    "source_system": "document_store",
                    "timestamp": status['timestamp'],
                    "event_details": {
                        "status": status['status'],
                        "location": status.get('location'),
                        "driver_id": status.get('driver_id')
                    }
                })
                # Capture the driver_id from the latest DELIVERED status (or any for this example)
                if status['status'] == 'DELIVERED' and status.get('driver_id'):
                    driver_id_for_graph = status['driver_id']

        # 2. Relational Store Query
        with pg_conn.cursor() as cur:
            cur.execute("""
                SELECT invoice_id, customer_id, amount, event_timestamp 
                FROM invoices 
                WHERE package_id = %s
            """, (package_id,))
            rows = cur.fetchall()
            for row in rows:
                combined_history.append({
                    "source_system": "relational_store",
                    "timestamp": row[3],
                    "event_details": {
                        "invoice_id": row[0],
                        "customer_id": row[1],
                        "amount": float(row[2])
                    }
                })

        # 3. Graph Store Query
        if driver_id_for_graph:
            query = """
            MATCH (d:Driver {driverId: $driver_id})-[:LOCATED_IN]->(z:Zone)
            RETURN d.latitude AS lat, d.longitude AS lon, z.zoneId AS zone_id, d.last_updated AS last_updated
            """
            with neo4j_driver.session() as session:
                result = session.run(query, driver_id=driver_id_for_graph)
                record = result.single()
                if record:
                    combined_history.append({
                        "source_system": "graph_store",
                        "timestamp": record["last_updated"] if record["last_updated"] else "9999-12-31T23:59:59Z",
                        "event_details": {
                            "driver_id": driver_id_for_graph,
                            "zone_id": record["zone_id"],
                            "location": {"lat": record["lat"], "lon": record["lon"]}
                        }
                    })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        mongo_client.close()
        pg_conn.close()
        neo4j_driver.close()
        
    # Sort by timestamp ascending
    combined_history.sort(key=lambda x: x['timestamp'])
    
    return combined_history
