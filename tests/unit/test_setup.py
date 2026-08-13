"""Scaffold smoke tests - these fail loudly if the environment is wrong."""


def test_environment_matches_the_lockfile():
    import anthropic
    import httpx
    import pydantic

    assert pydantic.VERSION.startswith("2."), "pydantic-settings needs Pydantic v2"


def test_own_package_is_installed():
    """src layout means capstone_ai must be *installed*, not merely present on disk."""
    from capstone_ai.core.config import Settings

    assert Settings().max_tokens > 0


def test_python_is_new_enough_for_stage_2():
    """Lab Stage 2 uses asyncio.TaskGroup, added in Python 3.11."""
    import asyncio
    import sys

    assert sys.version_info >= (3, 11), f"Stage 2 needs Python 3.11+, this is {sys.version.split()[0]}"
    assert hasattr(asyncio, "TaskGroup")
