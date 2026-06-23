"""Database reset utility - use with caution!"""

import asyncio
import asyncpg
import logging

logger = logging.getLogger(__name__)


async def reset_database_schema():
    """
    DANGEROUS: Drop and recreate the database schema completely.
    Only call this during development when you really need to reset!
    """
    conn = None
    try:
        # Connect WITHOUT specifying the graphmind database
        conn = await asyncpg.connect(
            user="postgres",
            password="student",
            host="localhost",
            port=5432,
            database="postgres",  # Connect to postgres db first
        )

        # Terminate connections to graphmind
        await conn.execute(
            "SELECT pg_terminate_backend(pg_stat_activity.pid) "
            "FROM pg_stat_activity "
            "WHERE pg_stat_activity.datname = 'graphmind' "
            "AND pid <> pg_backend_pid()"
        )
        logger.info(" Terminated connections to graphmind")

        # Drop the database
        await conn.execute("DROP DATABASE IF EXISTS graphmind")
        logger.info(" Dropped graphmind database")

        # Recreate the database
        await conn.execute("CREATE DATABASE graphmind OWNER postgres")
        logger.info(" Recreated graphmind database")

        await conn.close()
        logger.info(" Database schema reset complete")

    except Exception as e:
        logger.error(f" Failed to reset database: {e}")
        if conn:
            await conn.close()
        raise


if __name__ == "__main__":
    asyncio.run(reset_database_schema())
