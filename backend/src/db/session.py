"""Database session management using asyncpg."""

from typing import AsyncGenerator

import asyncpg
from asyncpg import Pool

from ..core.config import get_settings
from ..core.logging import get_logger

logger = get_logger(__name__)

# Global pool instance
_pool: Pool | None = None


async def get_pool() -> Pool:
    """Get or create the asyncpg connection pool.
    
    Returns:
        Asyncpg connection pool.
        
    Raises:
        RuntimeError: If the pool has not been initialized.
    """
    global _pool
    
    if _pool is None:
        settings = get_settings()
        
        logger.info(
            "Creating database connection pool",
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
        )
        
        _pool = await asyncpg.create_pool(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password,
            min_size=5,
            max_size=20,
            command_timeout=60,
        )
        
        logger.info("Database connection pool created successfully")
    
    return _pool


async def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    
    if _pool is not None:
        logger.info("Closing database connection pool")
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


async def init_pool() -> Pool:
    """Initialize the connection pool.
    
    This should be called during application startup.
    
    Returns:
        Initialized connection pool.
    """
    return await get_pool()


async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get a database connection from the pool.
    
    Yields:
        Database connection.
        
    Example:
        async with get_connection() as conn:
            result = await conn.fetch("SELECT * FROM users")
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def execute_query(
    query: str,
    *args: object,
    fetch: bool = True
) -> list[asyncpg.Record] | str:
    """Execute a query with automatic connection management.
    
    Args:
        query: SQL query string.
        *args: Query parameters.
        fetch: Whether to fetch results.
        
    Returns:
        Query results or status message.
    """
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        if fetch:
            result = await conn.fetch(query, *args)
            return list(result)
        else:
            status = await conn.execute(query, *args)
            return status


async def test_connection() -> bool:
    """Test database connectivity.
    
    Returns:
        True if connection is successful, False otherwise.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            return result == 1
    except Exception as e:
        logger.error("Database connection test failed", error=str(e))
        return False