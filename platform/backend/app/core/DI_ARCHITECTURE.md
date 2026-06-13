# DI Container Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                          │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              FastAPI Routes & Endpoints                       │  │
│  │                                                                │  │
│  │  @app.get("/tests/{test_id}")                                 │  │
│  │  async def get_test(                                          │  │
│  │      test_id: str,                                            │  │
│  │      service: ExecutionService = DependsExecutionService  ◄───┼──┤
│  │  ):                                                            │  │
│  │      return await service.get_test(test_id)                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                 │                                   │
│                                 │ Depends (FastAPI)                │
│                                 ▼                                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              DI Container (app/core/container.py)             │  │
│  │                                                                │  │
│  │  ┌──────────────────────────────────────────────────────┐   │  │
│  │  │ Provider Functions                                    │   │  │
│  │  │                                                       │   │  │
│  │  │ provide_execution_service()                          │   │  │
│  │  │   └─ @inject + Depends(Provide[...])                │   │  │
│  │  │                                                       │   │  │
│  │  │ provide_schedule_resolver()                          │   │  │
│  │  │ provide_analytics_service()                          │   │  │
│  │  └──────────────────────────────────────────────────────┘   │  │
│  │                                │                             │  │
│  │                                │ @inject                     │  │
│  │                                ▼                             │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │ Container Providers (DeclarativeContainer)            │ │  │
│  │  │                                                        │ │  │
│  │  │ execution_service = providers.Singleton(               │ │  │
│  │  │     ExecutionService,                                 │ │  │
│  │  │     schedule_resolver=schedule_resolver,              │ │  │
│  │  │     status_manager=run_status_manager,                │ │  │
│  │  │     result_persister=result_persister                 │ │  │
│  │  │ )                                                      │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  │                                │                             │  │
│  │                                │ Auto-wiring                │  │
│  │                                ▼                             │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │ Service Instances (Singleton)                         │ │  │
│  │  │                                                        │ │  │
│  │  │ ┌─────────────────────────────────────────────────┐  │ │  │
│  │  │ │ ExecutionService                                 │  │ │  │
│  │  │ │ ├── schedule_resolver: ScheduleResolver         │  │ │  │
│  │  │ │ ├── status_manager: RunStatusManager           │  │ │  │
│  │  │ │ ├── result_persister: ResultPersister          │  │ │  │
│  │  │ │ └── test_run_repository: ITestRunRepository    │  │ │  │
│  │  │ └─────────────────────────────────────────────────┘  │ │  │
│  │  │                                                        │ │  │
│  │  │ ┌─────────────────────────────────────────────────┐  │ │  │
│  │  │ │ ScheduleResolver                                 │  │ │  │
│  │  │ │ └── factory: ScheduleResolverFactory            │  │ │  │
│  │  │ └─────────────────────────────────────────────────┘  │ │  │
│  │  │                                                        │ │  │
│  │  │ ┌─────────────────────────────────────────────────┐  │ │  │
│  │  │ │ AnalyticsService                                 │  │ │  │
│  │  │ │ ├── test_run_repository: ITestRunRepository    │  │ │  │
│  │  │ │ └── test_definition_repository: ...              │  │ │  │
│  │  │ └─────────────────────────────────────────────────┘  │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  │                                │                             │  │
│  └────────────────────────────────┼─────────────────────────────┘  │
│                                   │                                 │
│                                   │ Implements                       │
│                                   ▼                                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                  Repository Layer                              │  │
│  │                                                                │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │ ITestRunRepository (interface)                         │  │  │
│  │  │     └── SQLAlchemyTestRunRepository (implementation)   │  │  │
│  │  │                                                           │  │  │
│  │  │ ITestDefinitionRepository (interface)                   │  │  │
│  │  │     └── SQLAlchemyTestDefinitionRepository              │  │  │
│  │  │                                                           │  │  │
│  │  │ IScheduleRepository (interface)                        │  │  │
│  │  │     └── SQLAlchemyScheduleRepository                   │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                 │                                   │
│                                 │ Uses                              │
│                                 ▼                                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                  Database Layer                                │  │
│  │                                                                │  │
│  │  ┌─────────────────┐    ┌──────────────────────────────────┐  │  │
│  │  │ PostgreSQL      │    │ AsyncSession (Factory)          │  │  │
│  │  │ (asyncpg)       │◄───│ └─ new session per request      │  │  │
│  │  └─────────────────┘    └──────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Dependency Injection Flow

### 1. Application Startup
```
FastAPI App Start
    │
    ├─► lifespan() context manager
    │       │
    │       ├─► startup_container()
    │       │       │
    │       │       ├─► init_db()  # Database connection
    │       │       │
    │       │       └─► init_container()
    │       │               │
    │       │               ├─► Create Container instance
    │       │               │
    │       │               ├─► Wire modules (enable @inject)
    │       │               │   ├─► app.api.v1.api
    │       │               │   ├─► app.services
    │       │               │   └─► app.temporal.*
    │       │               │
    │       │               └─► Return container instance
    │       │
    └─► App ready to handle requests
```

### 2. Request Handling
```
HTTP Request
    │
    ├─► FastAPI Route Handler
    │       │
    │       ├─► Depends(provide_execution_service)
    │       │       │
    │       │       ├─► @inject decorator activates
    │       │       │
    │       │       ├─► Provide[Container.execution_service]
    │       │       │       │
    │       │       │       └─► Container.execution_service()
    │       │       │               │
    │       │       │               ├─► Check if singleton exists
    │       │       │               │   └─► Yes: Return existing instance
    │       │       │               │   └─► No: Create new instance
    │       │       │               │           │
    │       │       │               │           ├─► Resolve dependencies
    │       │       │               │           │   ├─► schedule_resolver
    │       │       │               │           │   ├─► status_manager
    │       │       │               │           │   ├─► result_persister
    │       │       │               │           │   └─► test_run_repository
    │       │       │               │           │
    │       │       │               │           └─► Return ExecutionService instance
    │       │       │               │
    │       │       │               └─► Return singleton instance
    │       │       │
    │       │       └─► Return service to route handler
    │       │
    │       ├─► Route handler uses injected service
    │       │
    │       └─► Return response
    │
    └─► HTTP Response
```

### 3. Service Dependency Resolution
```
Service Instantiation (ExecutionService example)
    │
    ├─► Container.execution_service() called
    │       │
    │       ├─► Check singleton cache
    │       │   └─► Not cached
    │       │
    │       ├─► Resolve dependencies recursively
    │       │
    │       ├─► schedule_resolver = Container.schedule_resolver()
    │       │       │
    │       │       ├─► Check singleton cache
    │       │       │   └─► Not cached
    │       │       │
    │       │       ├─► Resolve: factory = Container.schedule_resolver_factory()
    │       │       │
    │       │       └─► Create ScheduleResolver instance
    │       │
    │       ├─► status_manager = Container.run_status_manager()
    │       │       │
    │       │       ├─► Check singleton cache
    │       │       │   └─► Not cached
    │       │       │
    │       │       ├─► Resolve: test_run_repository = Container.test_run_repository()
    │       │       │
    │       │       └─► Create RunStatusManager instance
    │       │
    │       ├─► result_persister = Container.result_persister()
    │       │       │
    │       │       ├─► Check singleton cache
    │       │       │   └─► Not cached
    │       │       │
    │       │       ├─► Resolve repositories
    │       │       │   ├─► test_run_repository
    │       │       │   ├─► test_case_repository
    │       │       │   └─► test_definition_repository
    │       │       │
    │       │       └─► Create ResultPersister instance
    │       │
    │       ├─► test_run_repository = Container.test_run_repository()
    │       │       │
    │       │       ├─► Check singleton cache
    │       │       │   └─► Not cached
    │       │       │
    │       │       └─► Create SQLAlchemyTestRunRepository instance
    │       │
    │       ├─► Create ExecutionService instance with all dependencies
    │       │
    │       └─► Cache singleton instance
    │
    └─► Return ExecutionService instance
```

## Lifecycle Management

### Singleton Lifecycle
```
Application Startup
    │
    ├─► Container initialized
    │
    ├─► First request for service
    │       │
    │       ├─► Service instance created
    │       │
    │       └─► Cached in container
    │
    ├─► Subsequent requests for same service
    │       │
    │       └─► Return cached instance (no creation)
    │
    ├─► Application shutdown
    │       │
    │       ├─► shutdown_container()
    │       │
    │       └─► All singletons destroyed
    │
    └─► Application stopped
```

### Factory Lifecycle (Database Sessions)
```
HTTP Request
    │
    ├─► Route handler needs database session
    │       │
    │       ├─► Depends(provide_db_session)
    │       │       │
    │       │       ├─► Container.db_session()
    │       │       │
    │       │       └─► Factory creates NEW session instance
    │       │
    │       ├─► Route handler uses session
    │       │
    │       └─► Response sent
    │
    ├─► Another HTTP request
    │       │
    │       ├─► Factory creates ANOTHER NEW session instance
    │       │
    │       └─► Different from previous session
    │
    └─► Each request gets its own session
```

## Testing Architecture

### Provider Overriding
```
Test Setup
    │
    ├─► Initialize container
    │       │
    │       └─► container = init_container()
    │
    ├─► Create mock service
    │       │
    │       └─► mock_service = Mock()
    │
    ├─► Override provider
    │       │
    │       └─► override_provider("execution_service", mock_service)
    │               │
    │               └─► Container.execution_service() now returns mock
    │
    ├─► Run tests
    │       │
    │       ├─► container.execution_service() returns mock_service
    │       │
    │       └─► Test behavior with mock
    │
    ├─► Cleanup
    │       │
    │       ├─► reset_provider("execution_service")
    │       │
    │       └─► Container.execution_service() returns real service
    │
    └─► Test complete
```

### TestContainer Pattern
```
Test Setup
    │
    ├─► Create TestContainer
    │       │
    │       └─► test_container = TestContainer()
    │
    ├─► Override providers with mocks
    │       │
    │       ├─► test_container.execution_service.override(
    │       │       providers.Object(mock_service)
    │       │   )
    │
    ├─► Wire test container with test modules
    │       │
    │       └─► test_container.wire(modules=["app.api.v1.endpoints.tests"])
    │
    ├─► Run tests
    │       │
    │       └─► Tests use mocked dependencies
    │
    ├─► Cleanup
    │       │
    │       └─► test_container.unwire()
    │
    └─► Test complete
```

## Key Design Patterns

### 1. Dependency Injection
- Services declare dependencies in constructor
- Container provides dependencies automatically
- Loose coupling between components

### 2. Singleton Pattern
- One instance per application lifetime
- Shared across all requests
- Efficient for stateless services

### 3. Factory Pattern
- New instance per request
- Used for request-scoped resources
- Prevents state leakage

### 4. Strategy Pattern
- ScheduleResolver uses Strategy pattern
- Different strategies for different schedule types
- Easy to extend with new strategies

### 5. Repository Pattern
- Abstract database access
- Interface-based dependencies
- Easy to swap implementations

### 6. Service Layer Pattern
- Business logic in services
- Services use repositories
- Clean separation of concerns

## Benefits

### 1. Maintainability
- Centralized dependency configuration
- Clear dependency graph
- Easy to understand relationships

### 2. Testability
- Easy to inject mocks
- Isolated unit testing
- Fast test execution

### 3. Flexibility
- Easy to swap implementations
- Configuration-based behavior
- Environment-specific overrides

### 4. Performance
- Singleton reuse
- Minimal overhead
- Lazy initialization

### 5. Type Safety
- Full type hints
- IDE autocomplete
- Compile-time checking

### 6. Scalability
- Easy to add new services
- Clear extension points
- Minimal code changes

## Performance Characteristics

### Singleton Resolution
```
Time: ~1-2 microseconds
Process:
  1. Check cache (O(1))
  2. Return cached instance
Memory: One instance per service
```

### Factory Resolution
```
Time: ~2-5 microseconds
Process:
  1. Call factory function
  2. Create new instance
  3. Return instance
Memory: New instance per call
```

### Dependency Graph Traversal
```
Time: O(depth) where depth = dependency tree depth
Typical depth: 3-5 levels
Worst case: < 10 levels
```

## Comparison: Before vs After

### Before (Manual Dependency Injection)
```python
class ExecutionService:
    def __init__(self, db_session=None):
        self.db_session = db_session
        self.schedule_resolver = ScheduleResolver()  # Manual creation
        self.status_manager = RunStatusManager()     # Manual creation
        self.repository = RepositoryFactory.get_test_run_repository()  # Factory
```

### After (DI Container)
```python
class ExecutionService:
    def __init__(
        self,
        schedule_resolver: ScheduleResolver,        # Injected
        status_manager: RunStatusManager,           # Injected
        test_run_repository: ITestRunRepository    # Injected
    ):
        self.schedule_resolver = schedule_resolver  # Provided by container
        self.status_manager = status_manager        # Provided by container
        self.test_run_repository = test_run_repository  # Provided by container
```

### Benefits Realized
- ✅ No manual dependency creation
- ✅ Automatic dependency injection
- ✅ Type-safe dependencies
- ✅ Easy testing with mocks
- ✅ Centralized configuration
- ✅ Clear dependency graph

This architecture provides a solid foundation for building maintainable, testable, and scalable applications.
