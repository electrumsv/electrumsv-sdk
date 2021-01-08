The ElectrumSV-SDK documentation
================================

This uses the `Sphinx documentation generator <https://www.sphinx-doc.org/en/master/>`_ in
combination with the `Read the docs theme <https://sphinx-rtd-theme.readthedocs.io/en/stable/>`_
to produce HTML-based documentation.

Before you can generate the documentation you need to install the dependencies.

Windows::

    cd docs
    py -3.7 -m pip install -r requirements.txt

MacOS/Linux::

    cd docs
    python3.7 -m pip install -r requirements.txt

To develop the documentation with the aid of a web browser, you can generate it in-place after
making local changes. The built documentation should not be checked in.

Windows::

    cd docs
    ./make html

MacOS/Linux::

    cd docs
    make html

The generated documentation will be available in the ``_build\html`` sub-directory. You can
navigate here and open ``index.html``.
