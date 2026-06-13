# Polyglot Persistence Layer

This project demonstrates a Polyglot Persistence architecture for a logistics platform. It ingests an event stream and routes data to three distinct databases based on the event type:
- **Graph Database (Neo4j)** for driver and zone relationships.
- **Document Database (MongoDB)** for package status histories.
- **Relational Database (PostgreSQL)** for billing transactions.

It also implements an eventual consistency model using a retry queue to handle out-of-order billing events.

## Prerequisites
- Docker and Docker Compose installed.

## Setup and Run

1. Clone the repository and navigate to the root directory.
2. The project contains a `.env.example` file. The `docker-compose.yml` is configured to use defaults or these values.
3. Build and start the services:

   ```bash
   docker-compose up --build
   ```

4. The application will automatically:
   - Wait for all databases to become healthy.
   - Initialize the PostgreSQL schema.
   - Read the `events.log` file.
   - Route events to Neo4j, MongoDB, and PostgreSQL.
   - Handle out-of-order billing events using a retry queue (`retry_queue.json`).
   - Start the FastAPI web server on port `8000`.

## Querying the API

The application exposes a unified query API that aggregates data from all three databases.

You can query the unified history of a package using `curl`:

```bash
curl http://localhost:8000/query/package/pkg-abc-123
```

This will return a JSON array containing the chronological history of the package, including its status changes, its final driver location, and any associated billing events.
