"""Helpers shared by more than one provider's process module."""

from __future__ import annotations


def _decode(output: str | bytes | None) -> str:
    """Decode subprocess output that may be ``str``, ``bytes``, or ``None``.

    Parameters
    ----------
    output : str | bytes | None
        Captured standard output or standard error. ``subprocess.run``
        normally decodes this per ``text``/``encoding``, but
        ``TimeoutExpired`` always carries raw bytes regardless of those
        settings.

    Returns
    -------
    str
        Decoded text, or an empty string when ``output`` is ``None``.
    """
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output
