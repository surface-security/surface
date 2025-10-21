import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


@pytest.mark.webtest
def test_login(live_server, test_cfg):
    test_cfg.driver.get(f"{live_server.url}/login/")
    assert "Log in" in test_cfg.driver.title

    test_cfg.driver.find_element(by=By.ID, value="id_username").send_keys(test_cfg.username)
    test_cfg.driver.find_element(by=By.ID, value="id_password").send_keys(f"{test_cfg.password}")
    test_cfg.driver.find_element(by=By.XPATH, value='//button[text()="Log in"]').send_keys(Keys.ENTER)

    assert "Home | Surface" == test_cfg.driver.title
