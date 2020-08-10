from pynixify import nixpkgs_sources

class NoSemaphore:
    async def __aenter__(self):
        return

    async def __aexit__(self, exc_type, exc_value, traceback):
        return

# pytest-asyncio uses diferent event loops per test and using a global
# semaphore will fail with horrible error messages
nixpkgs_sources.sem = NoSemaphore()  # type: ignore
