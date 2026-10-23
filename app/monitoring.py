"""Lightweight performance monitoring: time each operation and count
the MongoDB commands it sends. A small stand-in for OpenTelemetry."""

import time
from contextvars import ContextVar

from pymongo import monitoring
from strawberry.extensions import SchemaExtension


# The counter for the operation currently running (None outside GraphQL).
current_db_queries: ContextVar[list[int] | None] = ContextVar(
    "current_db_queries",
    default=None,
)


class DatabaseQueryCounter(monitoring.CommandListener):
    """PyMongo calls `started` for every command sent to MongoDB."""

    def started(self, event):
        counter = current_db_queries.get()

        if counter is not None:
            counter[0] += 1

    def succeeded(self, event):
        pass

    def failed(self, event):
        pass


class OperationStats(SchemaExtension):

    def on_operation(self):
        self.db_queries = [0]
        token = current_db_queries.set(self.db_queries)
        started_at = time.perf_counter()

        yield

        self.duration_ms = (time.perf_counter() - started_at) * 1000
        current_db_queries.reset(token)

    def get_results(self):
        return {
            "stats": {
                "dbQueries": self.db_queries[0],
                "durationMs": round(self.duration_ms, 1),
            }
        }
