# This file is part of the "your-package-name" project.
# It is licensed under the "Custom Non-Commercial License".
# You may not use this file for commercial purposes without
# explicit permission from the author.


import os


def path_to_this_file(file: str) -> str:
    """Return the absolute parent directory path for a file path.

    Args:
        file: File path that should be converted to an absolute directory path.

    Returns:
        The absolute directory path that contains ``file``.
    """

    return os.path.dirname(os.path.realpath(file))


def join(*args: str) -> str:
    """Join path parts into a single normalized path string.

    Args:
        *args: One or many path segments to join.

    Returns:
        A single path string built from all provided segments.
    """

    return os.path.join(*args)
