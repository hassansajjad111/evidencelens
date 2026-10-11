# src/evidencelens/kg/schema.py
from neo4j import AsyncDriver

SETUP_CONSTRAINTS_CYPHER = [
    "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE",
    "CREATE CONSTRAINT trial_id IF NOT EXISTS FOR (t:Trial) REQUIRE t.nct_id IS UNIQUE",
    "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE",
    "CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE",
    "CREATE FULLTEXT INDEX entity_names IF NOT EXISTS FOR (e:Entity) ON EACH [e.name, e.aliases]",
]

async def init_neo4j_schema(driver: AsyncDriver):
    """Initializes Neo4j unique constraints and full-text indexes for the knowledge graph."""
    async with driver.session() as session:
        for query in SETUP_CONSTRAINTS_CYPHER:
            await session.run(query)