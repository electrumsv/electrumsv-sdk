Testing
=======

For now this is a simple list of things that should be tested, and how they should work. It can
be formalised later.

* Ensuring that stopped processes exit gracefully.

  * On Windows, when running `electrumsv-sdk start` with `--background`, `--inline` and
    `--new-terminal` (the default when none of these are provided) verify that running
    `electrumsv-sdk stop` allows ElectrumSV to exit cleanly. This can be checked by looking at
    the logs for ElectrumSV and ensuring it closes down.

    Note that this behaves differently in CI than it does when run locally, so it is not guaranteed
    that CI-based testing for Windows at least, can ever replace manual testing.
