import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

TEST_IO = {
    "name": "test",
    "schedule": "@manually",
    "command": "echo 1",
    "description": "test job",
}


@pytest.mark.webtest
def test_dkron_admin_views(prep_dkron, test_cfg, live_server):
    test_cfg.driver.get(f"{live_server.url}/login/")
    assert "Login" in test_cfg.driver.title

    test_cfg.driver.find_element(by=By.ID, value="id_username").send_keys(
        test_cfg.username
    )
    test_cfg.driver.find_element(by=By.ID, value="id_password").send_keys(
        f"{test_cfg.password}"
    )
    test_cfg.driver.find_element(
        by=By.XPATH, value='//button[text()="Submit"]'
    ).send_keys(Keys.ENTER)

    assert "Home | Surface" == test_cfg.driver.title

    test_cfg.driver.get(f"{live_server.url}/dkron/job/add/")
    assert "Add job | Surface" == test_cfg.driver.title

    test_cfg.driver.find_element(by=By.ID, value="id_name").send_keys(TEST_IO["name"])
    test_cfg.driver.find_element(by=By.ID, value="id_schedule").send_keys(
        TEST_IO["schedule"]
    )
    test_cfg.driver.find_element(by=By.ID, value="id_command").send_keys(
        TEST_IO["command"]
    )
    test_cfg.driver.find_element(by=By.ID, value="id_description").send_keys(
        TEST_IO["description"]
    )
    test_cfg.driver.find_element(by=By.ID, value="id_use_shell").click()
    test_cfg.driver.find_element(by=By.ID, value="id_notify_on_error").click()

    test_cfg.driver.find_element(by=By.NAME, value="_save").send_keys(Keys.ENTER)

    test_cfg.driver.get(f"{live_server.url}/dkron/job")
    assert "Select job to change | Surface" == test_cfg.driver.title

    for k, v in TEST_IO.items():
        assert v == test_cfg.driver.find_element(by=By.CLASS_NAME, value=f"field-{k}").text