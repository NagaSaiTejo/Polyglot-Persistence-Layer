import os
import psycopg2
from pymongo import MongoClient
from neo4j import GraphDatabase

# PostgreSQL
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "logistics")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")

# MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password@localhost:27017/")

# Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

def get_postgres_connection():
    return psycopg2.connect(
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST
    )

def get_mongo_client():
    return MongoClient(MONGO_URI)

def get_neo4j_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def init_postgres_db():
    conn = get_postgres_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id VARCHAR(255) PRIMARY KEY,
            package_id VARCHAR(255) NOT NULL,
            customer_id VARCHAR(255) NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            event_timestamp VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
