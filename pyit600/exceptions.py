"""Exceptions for Salus iT600 smart devices."""


class IT600AuthenticationError(Exception):
    """Salus iT600 authentication exception."""

    pass


class IT600CommandError(Exception):
    """Salus iT600 command exception."""

    pass


class IT600ConnectionError(Exception):
    """Salus iT600 connection exception."""

    pass
