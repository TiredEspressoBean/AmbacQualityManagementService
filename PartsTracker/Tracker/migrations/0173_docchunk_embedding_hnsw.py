"""HNSW index on doc_chunks.embedding for cosine similarity search.

Semantic search (Tracker/ai_viewsets.py: vector_search and the hybrid search)
orders DocChunk by cosine distance. With no index every query sequentially
scanned doc_chunks and computed a 768-dimension distance per row, so cost grew
linearly with the corpus.

HNSW rather than IVFFlat: IVFFlat has to be built against representative data
(its `lists` parameter is tuned to row count) and is useless when built on an
empty or small table, which is exactly the state a fresh install is in. HNSW
builds incrementally and needs no training pass.

vector_cosine_ops matches the CosineDistance / `<=>` operator the queries use.
An index built for a different operator class is simply never chosen.

ef_construction=128 rather than pgvector's default of 64. It governs how hard
the build works to place each node in the graph, so it trades insert cost for
permanent recall. This table suits that trade: chunks arrive in batches at
document-ingest time and are then read on every search, so paying more per
insert once buys better retrieval forever. m=16 is left at the default -- fine
at 768 dimensions, and raising it costs memory for the life of the index.

Note ef_construction affects ongoing INSERTs too, not just the initial build:
each new chunk does a graph search to find its neighbours. That is acceptable
here because ingest is batched; it would not be for a row-at-a-time write path.

Note the query has to cooperate: pgvector can only serve `ORDER BY <distance>
ASC LIMIT n`. A DESC order, or ordering by an expression that wraps the distance
(e.g. `1 - (embedding <=> q)`), forces a sequential scan and this index goes
unused. The queries were fixed to order on the raw distance ascending in the
same change that added this.

Created CONCURRENTLY so it does not take an ACCESS EXCLUSIVE lock on
doc_chunks. The web container runs `migrate` inside its start command against a
300s healthcheck, and an HNSW build over a large corpus is not fast -- a blocking
build there would stall both the deploy and live search.
"""

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations
from pgvector.django import HnswIndex


class Migration(migrations.Migration):

    # AddIndexConcurrently cannot run inside a transaction.
    atomic = False

    dependencies = [
        ("Tracker", "0172_workcenter_is_critical"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="docchunk",
            index=HnswIndex(
                name="doc_chunks_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=128,
                opclasses=["vector_cosine_ops"],
            ),
        ),
    ]
