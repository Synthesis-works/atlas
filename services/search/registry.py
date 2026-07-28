from services.search.providers.base import SearchProvider


class SearchRegistry:
    """
    Registry for search providers.
    Allows registering multiple providers and querying them.
    """
    def __init__(self):
        self._providers: list[SearchProvider] = []

    def register(self, provider: SearchProvider) -> None:
        self._providers.append(provider)

    def providers(self) -> list[SearchProvider]:
        return self._providers.copy()
