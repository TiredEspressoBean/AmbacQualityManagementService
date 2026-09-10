"""Drop the duplicate btree index on doc_chunks.doc_id.

DocChunk.Meta declared `models.Index(fields=['doc'])` on a column Django had
already indexed: ForeignKey does `kwargs.setdefault("db_index", True)`, so the
FK carries its own index unless you pass db_index=False. The table therefore
carried two identical btrees on doc_id --

    doc_chunks_doc_id_96a56202     (Django's implicit FK index)
    doc_chunks_doc_id_0eb459_idx   (the explicit Meta.indexes one)

-- and the planner can only use one of them while every write maintains both.

Dropping the explicit one rather than the implicit one: suppressing Django's
would mean db_index=False on the FK plus keeping the Meta entry, which reaches
the same single index by a less obvious route. Removing the Meta entry leaves
exactly one index and no override to explain.

The column itself stays indexed deliberately -- it is on three hot paths:
`for_user()` filters `doc_id__in=<accessible documents>` on every AI search
(that subquery is how chunks inherit tenant, classification and export-control
scoping, since DocChunk has none of those fields), `document.chunks.all()`
reverse lookups, and on_delete=CASCADE finding a document's chunks when it is
deleted. Without any index that last one becomes a sequential scan per delete.

Note this could not be settled from index statistics: doc_chunks is empty, so
pg_stat_user_indexes reports 0 scans for both, which reflects an absence of data
rather than an unused index. Two identical indexes are redundant by definition.

Dropped CONCURRENTLY to match how 0173 adds: a plain DROP INDEX takes an ACCESS
EXCLUSIVE lock on the table, and this runs inside the web container's start
command during a deploy.
"""

from django.contrib.postgres.operations import RemoveIndexConcurrently
from django.db import migrations


class Migration(migrations.Migration):

    # RemoveIndexConcurrently cannot run inside a transaction.
    atomic = False

    dependencies = [
        ("Tracker", "0173_docchunk_embedding_hnsw"),
    ]

    operations = [
        RemoveIndexConcurrently(
            model_name="docchunk",
            name="doc_chunks_doc_id_0eb459_idx",
        ),
    ]
