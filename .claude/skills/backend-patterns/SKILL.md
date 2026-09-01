---
name: backend-patterns
description: Backend architecture patterns, API design, database optimization, and server-side best practices for Python and FastAPI applications. Use when building or reviewing FastAPI routes and their data access.
---

# Backend Development Patterns

Backend architecture patterns and best practices for scalable server-side applications.

## When to Activate

- Designing REST or GraphQL API endpoints
- Implementing repository, service, or controller layers
- Optimizing database queries (N+1, indexing, connection pooling)
- Adding caching (Redis, in-memory, HTTP cache headers)
- Setting up background jobs or async processing
- Structuring error handling and validation for APIs
- Building middleware (auth, logging, rate limiting)

## API Design Patterns

### RESTful API Structure

```python
# PASS: Resource-based URLs
GET    /api/markets
GET    /api/markets/{id}
POST   /api/markets
PUT    /api/markets/{id}
PATCH  /api/markets/{id}
DELETE /api/markets/{id}

# PASS: Query parameters for filtering, sorting, pagination
GET /api/markets?status=active&sort=volume&limit=20&offset=0
```

### Repository Pattern

```python
# Abstract data access logic
class MarketRepository(Protocol):
    async def find_all(self, filters: MarketFilters | None = None) -> list[Market]: ...
    async def find_by_id(self, id: str) -> Market | None: ...
    async def create(self, data: CreateMarketDto) -> Market: ...
    async def update(self, id: str, data: UpdateMarketDto) -> Market: ...
    async def delete(self, id: str) -> None: ...


class SqlAlchemyMarketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_all(self, filters: MarketFilters | None = None) -> list[Market]:
        query = select(Market)

        if filters and filters.status:
            query = query.where(Market.status == filters.status)

        if filters and filters.limit:
            query = query.limit(filters.limit)

        result = await self.session.scalars(query)
        return list(result)

    # Other methods...
```

### Service Layer Pattern

```python
# Business logic separated from data access
class MarketService:
    def __init__(self, market_repo: MarketRepository) -> None:
        self.market_repo = market_repo

    async def search_markets(
        self,
        query: str,
        limit: int = 10,
    ) -> list[Market]:
        # Business logic
        embedding = await generate_embedding(query)
        results = await self._vector_search(embedding, limit)

        # Fetch full data
        markets = await self.market_repo.find_by_ids([result.id for result in results])

        # Sort by similarity
        return sorted(
            markets,
            key=lambda market: next(
                (
                    result.score
                    for result in results
                    if result.id == market.id
                ),
                0,
            ),
        )

    async def _vector_search(self, embedding: list[float], limit: int):
        # Vector search implementation
        ...
```

### Middleware Pattern

```python
# Request/response processing pipeline
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


security = HTTPBearer()


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    try:
        user = verify_token(token)
        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


# Usage
@router.get("/markets")
async def get_markets(user=Depends(require_auth)):
    # Handler has access to user
    ...
```

## Database Patterns

### Query Optimization

```python
# PASS: GOOD: Select only needed columns
query = (
    select(
        Market.id,
        Market.name,
        Market.status,
        Market.volume,
    )
    .where(Market.status == "active")
    .order_by(Market.volume.desc())
    .limit(10)
)
data = (await session.execute(query)).all()

# FAIL: BAD: Select everything
query = select(Market)
```

### N+1 Query Prevention

```python
# FAIL: BAD: N+1 query problem
markets = await get_markets()

for market in markets:
    market.creator = await get_user(market.creator_id)  # N queries


# PASS: GOOD: Batch fetch
markets = await get_markets()
creator_ids = [market.creator_id for market in markets]
creators = await get_users(creator_ids)  # 1 query
creator_map = {creator.id: creator for creator in creators}

for market in markets:
    market.creator = creator_map.get(market.creator_id)
```

### Transaction Pattern

```python
async def create_market_with_position(
    market_data: CreateMarketDto,
    position_data: CreatePositionDto,
):
    async with session.begin():
        market = Market(**market_data.model_dump())
        session.add(market)
        await session.flush()

        position = Position(
            **position_data.model_dump(),
            market_id=market.id,
        )
        session.add(position)

    return market
```

## Caching Strategies

### Redis Caching Layer

```python
import json


class CachedMarketRepository:
    def __init__(self, base_repo: MarketRepository, redis: Redis) -> None:
        self.base_repo = base_repo
        self.redis = redis

    async def find_by_id(self, id: str) -> Market | None:
        # Check cache first
        cached = await self.redis.get(f"market:{id}")

        if cached:
            return Market.model_validate_json(cached)

        # Cache miss - fetch from database
        market = await self.base_repo.find_by_id(id)

        if market:
            # Cache for 5 minutes
            await self.redis.setex(
                f"market:{id}",
                300,
                market.model_dump_json(),
            )

        return market

    async def invalidate_cache(self, id: str) -> None:
        await self.redis.delete(f"market:{id}")
```

### Cache-Aside Pattern

```python
async def get_market_with_cache(id: str) -> Market:
    cache_key = f"market:{id}"

    # Try cache
    cached = await redis.get(cache_key)
    if cached:
        return Market.model_validate_json(cached)

    # Cache miss - fetch from DB
    market = await session.get(Market, id)

    if not market:
        raise Exception("Market not found")

    # Update cache
    await redis.setex(cache_key, 300, market.model_dump_json())

    return market
```

## Error Handling Patterns

### Centralized Error Handler

```python
class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        is_operational: bool = True,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.is_operational = is_operational


@app.exception_handler(ApiError)
async def api_error_handler(
    request: Request,
    error: ApiError,
) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"success": False, "error": error.message},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": "Validation failed",
            "details": error.errors(),
        },
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(
    request: Request,
    error: Exception,
) -> JSONResponse:
    # Log unexpected errors
    logger.exception("Unexpected error")

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
        },
    )


# Usage
@router.get("/data")
async def get_data():
    data = await fetch_data()
    return {"success": True, "data": data}
```

### Retry with Exponential Backoff

```python
import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar


T = TypeVar("T")


async def fetch_with_retry(
    fn: Callable[[], Awaitable[T]],
    max_retries: int = 3,
) -> T:
    last_error: Exception | None = None

    for i in range(max_retries):
        try:
            return await fn()
        except Exception as error:
            last_error = error

            if i < max_retries - 1:
                # Exponential backoff: 1s, 2s, 4s
                delay = (2**i)
                await asyncio.sleep(delay)

    assert last_error is not None
    raise last_error


# Usage
data = await fetch_with_retry(fetch_from_api)
```

## Authentication & Authorization

### JWT Token Validation

```python
import jwt
from pydantic import BaseModel


class JWTPayload(BaseModel):
    user_id: str
    email: str
    role: str


def verify_token(token: str) -> JWTPayload:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
        )
        return JWTPayload.model_validate(payload)
    except jwt.PyJWTError:
        raise ApiError(401, "Invalid token")


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> JWTPayload:
    token = credentials.credentials

    if not token:
        raise ApiError(401, "Missing authorization token")

    return verify_token(token)


# Usage in API route
@router.get("/data")
async def get_data(
    user: JWTPayload = Depends(require_auth),
):
    data = await get_data_for_user(user.user_id)

    return {"success": True, "data": data}
```

### Role-Based Access Control

```python
from enum import StrEnum


class Permission(StrEnum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


class Role(StrEnum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"


role_permissions: dict[Role, list[Permission]] = {
    Role.ADMIN: [
        Permission.READ,
        Permission.WRITE,
        Permission.DELETE,
        Permission.ADMIN,
    ],
    Role.MODERATOR: [
        Permission.READ,
        Permission.WRITE,
        Permission.DELETE,
    ],
    Role.USER: [
        Permission.READ,
        Permission.WRITE,
    ],
}


def has_permission(user: User, permission: Permission) -> bool:
    return permission in role_permissions[user.role]


def require_permission(permission: Permission):
    async def dependency(user: User = Depends(require_auth)) -> User:
        if not has_permission(user, permission):
            raise ApiError(403, "Insufficient permissions")

        return user

    return dependency


# Usage
@router.delete("/markets/{id}")
async def delete_market(
    id: str,
    user: "User" = Depends(require_permission(Permission.DELETE)),
):
    # Handler receives authenticated user with verified permission
    return Response(status_code=200)
```

## Rate Limiting

Rate limiting must use a shared store such as Redis, a gateway, or the platform's native limiter. Do not use per-process in-memory counters for production APIs: they reset on deploy, split across replicas, and fail open in serverless or multi-instance environments.

Keep the backend layer responsible for choosing the integration point and error shape; use `api-design` for the HTTP contract and `security-review` for abuse case review.

## Background Jobs & Queues

### Simple Queue Pattern

```python
import asyncio
from collections import deque
from typing import Generic, TypeVar


T = TypeVar("T")


class JobQueue(Generic[T]):
    def __init__(self) -> None:
        self.queue: deque[T] = deque()
        self.processing = False

    async def add(self, job: T) -> None:
        self.queue.append(job)

        if not self.processing:
            await self.process()

    async def process(self) -> None:
        self.processing = True

        while self.queue:
            job = self.queue.popleft()

            try:
                await self.execute(job)
            except Exception:
                logger.exception("Job failed")

        self.processing = False

    async def execute(self, job: T) -> None:
        # Job execution logic
        ...


# Usage for indexing markets
class IndexJob(BaseModel):
    market_id: str


index_queue = JobQueue[IndexJob]()


@router.post("/index")
async def index_market(job: IndexJob):
    # Add to queue instead of blocking
    await index_queue.add(job)

    return {
        "success": True,
        "message": "Job queued",
    }
```

## Logging & Monitoring

### Structured Logging

```python
import json
import logging
from datetime import UTC, datetime
from typing import Any


class Logger:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def log(
        self,
        level: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level,
            "message": message,
            **(context or {}),
        }

        self.logger.log(
            getattr(logging, level.upper()),
            json.dumps(entry),
        )

    def info(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.log("info", message, context)

    def warn(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.log("warn", message, context)

    def error(
        self,
        message: str,
        error: Exception,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.log(
            "error",
            message,
            {
                **(context or {}),
                "error": str(error),
            },
        )


logger = Logger()


# Usage
@router.get("/markets")
async def get_markets(request: Request):
    request_id = str(uuid4())

    logger.info(
        "Fetching markets",
        {
            "request_id": request_id,
            "method": "GET",
            "path": "/api/markets",
        },
    )

    try:
        markets = await fetch_markets()
        return {
            "success": True,
            "data": markets,
        }
    except Exception as error:
        logger.error(
            "Failed to fetch markets",
            error,
            {"request_id": request_id},
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal error"},
        )
```

**Remember**: Backend patterns enable scalable, maintainable server-side applications. Choose patterns that fit your complexity level.
