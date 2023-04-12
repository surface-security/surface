# End-To-End Integration Tests

This folder contains end-to-end integration tests for the Surface project. The suite should be kept simple and minimal 
as its main purpose is to ensure minimum functionality of the UI, either in dependency upgrade scenarios or in feature 
changes, bug fixes, and so on.

The ultimate goal for this suite is to have added validations that any change does not cause backward incompatibilities. 
Everytime there is a breaking change, we can opt to write a regression test to ensure it does not happen again.

Tests run in headless mode, so you will not see the browser effectively performing the actions. For debugging purposes, 
you can disable the `headless` option in the custom pytest fixture `setup_cfg` in `conftest.py` and add Python's `pdb` in 
between to check the actions and watch the application behave.

Another feature of this suite is that most of the setup is handled in Python code (in this case, it's mostly about `pytest` 
fixtures), so there are no external dependencies and it should be kept this way.

## Running Locally

To run the above test suite locally, you need to install the test dependencies and call pytest from the project root dir:
- `pip install -r surface/requirements_test.txt` (preferably from a specific Python environment);
- Install the Selenium webdriver(s) for the chosen browser(s): https://www.selenium.dev/downloads/
- `pytest -v e2e`

Pytest setup considers invoking directory as the root, which is needed to call some of the commands during the setup. 
This is the case for `run_dkron`, which starts the Dkron server in the background.

The test suite does not need any `local.env` or environment variables, as things are hardcoded for simplicity. Any need 
to tweak the tweaks, configuration-wise, should be done by adjusting the `settings` module in the `conftest.py`.


## Running in CI

The test suite contains a custom pytest fixture that loads the necessary environment for the corresponding test. The 
procedure to run these tests in your CI system is pretty much the same as [Running Locally](#running-locally): install 
test dependencies, install selenium webdriver (or if on GitHub use the action with all this prepared for you - 
see [`./github/workflows/integration.yml`](./github/workflows/integration.yml)), and run 
pytest from the project root.
