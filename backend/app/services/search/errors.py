"""Search provider errors."""


class SearchError(Exception):
    """Base class for search provider failures."""


class SearchProviderNotConfiguredError(SearchError):
    """A requested provider lacks the configuration it requires."""
