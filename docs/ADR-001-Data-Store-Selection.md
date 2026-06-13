# ADR-001: Data Store Selection for the Logistics Platform

## Status
Accepted

## Context
Our logistics platform ingests a variety of event types, each representing different domain models and querying needs:
1. **Driver Location Updates**: Require fast geospatial and relationship-based querying to find which zone a driver is located in.
2. **Package Status Changes**: Represent the life cycle of a package. These events append to a chronologically growing history and have semi-structured metadata.
3. **Billing Events**: Require transactional integrity (ACID) and schema enforcement to prevent duplicate billing and allow complex financial reporting.

A single data store is insufficient to handle all these patterns effectively without significant performance trade-offs or complex application-side logic.

## Decision
We have decided to adopt a Polyglot Persistence architecture, utilizing three distinct data stores:
1. **Neo4j (Graph Database)**: Chosen for managing drivers, zones, and their relationships (`LOCATED_IN`).
2. **MongoDB (Document Database)**: Chosen for storing package status histories.
3. **PostgreSQL (Relational Database)**: Chosen for storing billing and transactional records.

## Consequences

### Graph Database (Neo4j)
* **Pros**: Highly efficient at querying relationships (e.g., finding all drivers in a zone, or the current zone of a driver). Schema-less nature allows easy addition of new relationship types.
* **Cons**: Not optimized for large-scale data aggregations or simple key-value lookups. Slightly higher learning curve for the Cypher query language.

### Document Database (MongoDB)
* **Pros**: Flexible schema easily accommodates varying JSON event structures. The `upsert` and `$push` operations are perfect for appending to a package's history without fetching the entire document first. Highly scalable.
* **Cons**: Lack of rigid schema can lead to data inconsistencies if the application does not enforce its own validation. Joins across collections are less efficient than in relational databases.

### Relational Database (PostgreSQL)
* **Pros**: Strong ACID properties guarantee data integrity for financial transactions. Built-in constraints (e.g., `UNIQUE`) naturally prevent duplicate billing records. Excellent for complex analytical queries.
* **Cons**: Rigid schema requires migrations when data structures change. Less efficient at storing highly nested or variable structure data compared to a document store.

### Overall Architectural Consequences
Adopting polyglot persistence introduces significant operational complexity:
* **Eventual Consistency**: We lose distributed transactions. We must build application-level reconciliation (e.g., retry queues) to handle out-of-order events (like a billing event arriving before a delivery event).
* **Maintenance**: We now have to manage, monitor, and back up three separate database systems instead of one.
* **Development Overhead**: Developers need to understand multiple database paradigms and query languages.
