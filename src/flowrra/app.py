from typing import Callable, TYPE_CHECKING

from flowrra.config import Config, BrokerConfig, BackendConfig
from flowrra.executors.io_executor import IOExecutor
from flowrra.executors.cpu_executor import CPUExecutor
from flowrra.task import TaskResult

if TYPE_CHECKING:
    from flowrra.scheduler import Scheduler


class Flowrra:
    """Unified Flowrra application for task execution.

    Automatically routes tasks to appropriate executors based on task type.

    Usage:
        # Using Config
        config = Config(
            broker=BrokerConfig(url='redis://localhost:6379/0'),
            backend=BackendConfig(url='redis://localhost:6379/1')
        )
        app = Flowrra(config=config)

        # Using from_urls()
        app = Flowrra.from_urls(
            broker='redis://localhost:6379/0',
            backend='redis://localhost:6379/1'
        )

        # I/O-bound task (default)
        @app.task()
        async def fetch_data(url: str):
            return await fetch(url)

        # CPU-bound task
        @app.task(cpu_bound=True)
        def heavy_compute(n: int):
            return sum(i**2 for i in range(n))
    """

    def __init__(self, config: Config | None = None):
        if config is None:
            config = Config()

        self._config = config
        self._io_executor: IOExecutor | None = None
        self._cpu_executor: CPUExecutor | None = None
        self._scheduler: "Scheduler | None" = None
        self._running = False

    def _init_executor(self, cpu_bound: bool):
        if cpu_bound:
            if self._cpu_executor is None:
                if self._config.backend is None:
                    raise ValueError("CPU-bound tasks require backend for cross-process results")
                self._cpu_executor = CPUExecutor(config=self._config)
            return self._cpu_executor
        else:
            if self._io_executor is None:
                self._io_executor = IOExecutor(config=self._config)
            return self._io_executor

    @classmethod
    def from_urls(
        cls,
        broker: str | None = None,
        backend: str | None = None,
    ) -> "Flowrra":
        """Convenience method to create Flowrra from URLs.

        Args:
            broker: Broker connection URL (optional, None = asyncio.PriorityQueue)
            backend: Backend connection URL (optional, None = InMemoryBackend for IO, required for CPU)

        Returns:
            Flowrra instance

        """
        broker_config = BrokerConfig(url=broker) if broker else None
        backend_config = BackendConfig(url=backend) if backend else None
        config = Config(broker=broker_config, backend=backend_config)

        return cls(config=config)

    def task(
        self,
        name: str | None = None,
        cpu_bound: bool = False,
        **kwargs
    ):
        """Register a task with automatic executor routing.

        Args:
            name: Custom task name (defaults to function name)
            cpu_bound: If True, uses CPUExecutor; if False, uses IOExecutor (default)

        Returns:
            Decorator function
        """
        executor = self._cpu_executor if cpu_bound else self._io_executor
        if executor is None:
            executor = self._init_executor(cpu_bound)

        # Register task in executor registry
        decorator = executor.task(name=name, **kwargs)

        # Attach executor reference to decorated function for easy submit
        def wrapper(func):
            func._executor = executor
            return decorator(func)

        return wrapper

    async def submit(
        self,
        task_func: Callable,
        *args,
        **kwargs
    ) -> str:
        """Submit a task for execution.

        Args:
            task_func: Registered task function
            *args: Positional arguments for the task
            **kwargs: Keyword arguments for the task

        Returns:
            task_id: Unique identifier for tracking
        """
        executor = getattr(task_func, "_executor", self._io_executor)
        if executor is None:
            raise RuntimeError("Task function is not registered with this app")
        return await executor.submit(task_func, *args, **kwargs)

    async def wait_for_result(
        self,
        task_id: str,
        timeout: float | None = None
    ) -> TaskResult:
        """Wait for a task to complete and return its result.

        Args:
            task_id: Task identifier
            timeout: Max seconds to wait (None = wait forever)

        Returns:
            TaskResult with status, result, and error information
        """
        if self._io_executor and self._io_executor.is_running:
            result = await self._io_executor.get_result(task_id)
            if result:
                if result.is_complete:
                    return result
                return await self._io_executor.wait_for_result(task_id, timeout=timeout)

        if self._cpu_executor and self._cpu_executor.is_running:
            result = await self._cpu_executor.get_result(task_id)
            if result:
                if result.is_complete:
                    return result
                return await self._cpu_executor.wait_for_result(task_id, timeout=timeout)

        raise ValueError(f"Task {task_id} not found in any executor")

    async def get_result(self, task_id: str) -> TaskResult | None:
        if self._io_executor:
            result = await self._io_executor.get_result(task_id)
            if result:
                return result

        if self._cpu_executor:
            result = await self._cpu_executor.get_result(task_id)
            if result:
                return result

        return None

    async def start(self):
        if self._running:
            return

        self._running = True

        if self._io_executor:
            await self._io_executor.start()

        if self._cpu_executor:
            await self._cpu_executor.start()

        if self._scheduler:
            await self._scheduler.start()

    def create_scheduler(
        self,
        backend: "BaseSchedulerBackend | str | None" = None,
        check_interval: float = 60.0
    ) -> "Scheduler":
        """Create a scheduler integrated with this app's executors.

        The scheduler is automatically registered with the app and will start/stop
        with the app lifecycle. Access it via app.scheduler property or use
        FlowrraManager for comprehensive schedule management.

        Args:
            backend: Scheduler backend (URL string or instance)
                - None: Uses default SQLite backend (.flowrra_schedule.db)
                - String: Database URL (e.g., "postgresql://localhost/db")
                - Instance: Custom BaseSchedulerBackend instance
            check_interval: How often to check for due tasks (seconds)

        Returns:
            Scheduler instance configured with this app's executors

        Example:
            app = Flowrra.from_urls()

            @app.task()
            async def send_report():
                return "Report sent"

            # Create integrated scheduler (auto-registered)
            scheduler = app.create_scheduler()

            # Schedule tasks
            await scheduler.schedule_cron(
                task_name="send_report",
                cron="0 9 * * *"
            )

            # Start app (automatically starts scheduler too)
            await app.start()

            # Or use FlowrraManager for comprehensive management
            from flowrra.management import FlowrraManager
            manager = FlowrraManager(app)
            schedules = await manager.list_schedules()
        """
        from flowrra.scheduler import Scheduler
        from flowrra.scheduler.backends import get_scheduler_backend

        if isinstance(backend, str):
            scheduler_backend = get_scheduler_backend(backend)
        elif backend is None:
            scheduler_backend = get_scheduler_backend()
        else:
            scheduler_backend = backend

        scheduler = Scheduler(
            backend=scheduler_backend,
            registry=self.registry,
            check_interval=check_interval,
            io_executor=self._io_executor,
            cpu_executor=self._cpu_executor
        )

        # Store reference for management access
        self._scheduler = scheduler

        return scheduler

    async def stop(self, wait: bool = True, timeout: float | None = 30.0):
        """Stop the Flowrra application and all executors.

        Args:
            wait: If True, wait for pending tasks to complete
            timeout: Max seconds to wait for pending tasks
        """
        if not self._running:
            return

        self._running = False

        if self._io_executor:
            await self._io_executor.stop(wait=wait, timeout=timeout)

        if self._cpu_executor:
            await self._cpu_executor.stop(wait=wait, timeout=timeout)

        if self._scheduler:
            await self._scheduler.stop()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def registry(self):
        """Get the task registry from the IO executor.

        Returns:
            TaskRegistry instance

        Note:
            Both IOExecutor and CPUExecutor share the same registry instance
        """
        if self._io_executor:
            return self._io_executor.registry
        elif self._cpu_executor:
            return self._cpu_executor.registry
        else:
            self._init_executor(cpu_bound=False)
            return self._io_executor.registry

    @property
    def scheduler(self) -> "Scheduler | None":
        """Get the registered scheduler instance.

        Returns:
            Scheduler instance if created via create_scheduler(), None otherwise

        Note:
            The scheduler is optional. It only exists if create_scheduler()
            was called.
        """
        return self._scheduler
