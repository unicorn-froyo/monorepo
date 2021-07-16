"""Shared utility functions"""

def get_transitive_files(label):
    """Get transitive sources for python files

    Args:
      label: A label of a python library.
    Returns:
      A list of transitive source files.
    """
    return label[PyInfo].transitive_sources.to_list()

def get_transitive_deps(deps):
    """Get Transitive Dependencies

      Args:
          deps: label list of dependencies
          provider: The provider of the dependencies. Defaults to PyInfo.

      Returns:
          [list]: List of files dependency files
      """
    transitive_deps = []

    for dep in deps:
        for d in dep[DefaultInfo].data_runfiles.files.to_list():
            if d not in transitive_deps:
                transitive_deps.append(d)
    return transitive_deps
