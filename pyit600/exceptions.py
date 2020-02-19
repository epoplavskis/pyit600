"""Exceptions for Salus iT600 smart devices."""


class IT600Error(Exception):
    """Salus iT600 exception."""

    pass


class IT600AuthenticationError(IT600Error):
    """Salus iT600 authentication exception."""

    pass


class IT600CommandError(IT600Error):
    """Salus iT600 command exception."""

    pass


class IT600ConnectionError(IT600Error):
    """Salus iT600 connection exception."""

    pass
