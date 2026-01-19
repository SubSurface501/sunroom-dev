The virtual environment setup instructions have been saved to `docs/virtual_environment_setup.md`.

Regarding the Celery `--pool=solo` command:

My current instructions, and the `README.md` for this project, specify `python -m celery -A worker.src.agents.tasks worker -l info --pool=solo` for local development.

**Why `--pool=solo` is used in local development:**
*   **Simplicity and Debugging:** The `--pool=solo` option forces the Celery worker to run in a single process, single-threaded mode. This significantly simplifies debugging, as you don't have to deal with the complexities of multiple processes or threads, making it easier to trace execution flow and catch errors.
*   **Resource Management:** For local development, where the workload might not be heavy and resources are often limited, a solo worker is sufficient and less resource-intensive.

**For Production Environments:**
You are absolutely correct that `--pool=solo` is generally **not used** in production. For production deployments, Celery workers are typically configured with a concurrent pool (like `prefork` for multiprocessing, `gevent` for coroutine-based concurrency, or `eventlet`) to handle many tasks in parallel, maximizing throughput and efficiency.

**To answer your question directly:** For the purpose of simplified local development and debugging, using `--pool=solo` is the intended approach as per the project's current documentation.

Do you recall a specific reason or previous decision to move away from using `--pool=solo` for local development? If you'd like to configure the local development environment for concurrency, I can certainly provide instructions for using a different pool, but it would come with increased complexity for debugging.