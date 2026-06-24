"""Neo4j retry handler with exponential backoff for transient failures"""

import asyncio
import logging
from typing import Callable, TypeVar, Any
from neo4j.exceptions import TransientError, ServiceUnavailable

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_neo4j_operation(
    operation: Callable[[], Any],
    max_retries: int = 3,
    initial_delay: float = 0.5,
) -> Any:
    """
    Execute Neo4j operation with exponential backoff for transient failures.

    CRITICAL: Only retries on TransientError or ServiceUnavailable.
    Does NOT retry on other exceptions (security, validation, etc.).

    Error categories:
    - TransientError: Network blip, lock contention  RETRY
    - ServiceUnavailable: Temporary cluster issue  RETRY
    - Other exceptions: Code bug, validation failure  FAIL FAST

    Args:
        operation: Async callable to execute (e.g., neo4j_repo.execute_write(...))
        max_retries: Maximum retry attempts (3 = 4 total attempts)
        initial_delay: Initial backoff delay in seconds (0.5 = 500ms)

    Returns:
        Result of operation if successful

    Raises:
        TransientError: If operation fails after max_retries
        Any other exception: Raised immediately (no retry)

    Example:
        result = await retry_neo4j_operation(
            lambda: neo4j_repo.execute_write(query, params)
        )
    """
    delay = initial_delay
    attempt = 0
    last_error = None

    while attempt <= max_retries:
        try:
            logger.debug(f"Neo4j operation attempt {attempt + 1}/{max_retries + 1}")
            result = await operation()
            if attempt > 0:
                logger.info(f" Neo4j operation succeeded after {attempt} retries")
            return result

        except (TransientError, ServiceUnavailable) as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(
                    f" Transient Neo4j error (attempt {attempt + 1}/{max_retries + 1}): {e}"
                )
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff: 0.5s  1s  2s  4s
                attempt += 1
            else:
                logger.error(
                    f" Neo4j operation failed after {max_retries} retries: {e}"
                )
                raise

        except Exception as e:
            # Do NOT retry on non-transient errors (code bugs, validation, etc.)
            logger.error(
                f" Neo4j operation failed (non-transient error): {type(e).__name__}: {e}"
            )
            raise

    # This should never happen, but just in case
    if last_error:
        raise last_error
