"""Shared utility functions"""

def get_transitive_files(label):
    """Get transitive sources for python files

    Args:
      label: A label of a python library.
    Returns:
      A list of transitive source files.
    """
    return label[PyInfo].transitive_sources.to_list()
