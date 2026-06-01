from sqlalchemy import create_engine, text
from txtai import Embeddings

# MAKE SURE THE DATABASE EXISTS PRIOR TO RUNNING THE APP.
DB_CONN = (
    "postgresql+psycopg://postgres:postgres@localhost:5432/vector_testing"  # TODO: Env
)

DB_ENGINE = create_engine(DB_CONN)

with DB_ENGINE.connect() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS public"))
    conn.commit()

EMBEDDINGS = Embeddings(
    content=DB_CONN,  # Use a database to store the embeddings and metadata
    backend="pgvector",  # Use pgvector for efficient vector storage and search
    pgvector={
        "url": DB_CONN,
    },
    graph={
        "backend": "rdbms",
        "url": DB_CONN,
    },
)
EMBEDDINGS_CONFIG_NAME = "generated_embeddings_config"
