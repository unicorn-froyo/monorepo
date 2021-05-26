"""Shared utility functions"""

def get_transitive_files(label):
    """Get transitive sources for python files

    Args:
      label: A label of a python library.
    Returns:
      A list of transitive source files.
    """
    return label[PyInfo].transitive_sources.to_list()

def get_transitive_deps(deps, provider = PyInfo):
    """Get Transitive Dependencies

      Args:
          deps (label_list): label list of dependencies
          provider ([Provider, optional): The provider of the dependencies. Defaults to PyInfo.

      Returns:
          [list]: List of files dependency files
      """
    transitive_deps = []

    for dep in deps:
        for d in dep[provider].transitive_sources.to_list():
            if d not in transitive_deps:
                transitive_deps.append(d)
    return transitive_deps
