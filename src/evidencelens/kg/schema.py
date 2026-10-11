"""`src/evidencelens/kg/schema.py`: constraints/indexes for graph identifiers.

The constraints make entity, trial, chunk, and document merges deterministic;
the full-text index supports entity-name lookup. These DDL statements define the
schema foundation only: loading nodes/relationships and graph retrieval remain
future pipeline work.
"""

from neo4j import AsyncDriver

# Run as idempotent DDL before any graph import job writes entities or evidence.
SETUP_CONSTRAINTS_CYPHER = [
    "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE",
    "CREATE CONSTRAINT trial_id IF NOT EXISTS FOR (t:Trial) REQUIRE t.nct_id IS UNIQUE",
    "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE",
    "CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE",
    "CREATE FULLTEXT INDEX entity_names IF NOT EXISTS FOR (e:Entity) ON EACH [e.name, e.aliases]",
]

async def init_neo4j_schema(driver: AsyncDriver):
    """Apply the graph's uniqueness constraints and entity-name full-text index."""
    async with driver.session() as session:
        for query in SETUP_CONSTRAINTS_CYPHER:
            await session.run(query)