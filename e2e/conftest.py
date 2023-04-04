import subprocess
import time
from dataclasses import dataclass

import pytest
from django.contrib.auth import get_user_model
from scanners.models import ScannerImage
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver


@dataclass
class Config:
    username: str
    password: str
    driver: WebDriver


def setup_config(username: str, password: str) -> Config:
    opts = Options()
    opts.add_argument("--incognito")
    opts.add_argument("--headless")
    return Config(
        username=username, password=password, driver=webdriver.Chrome(options=opts)
    )


def prep_users(username: str, password: str):
    User = get_user_model()
    User.objects.create_superuser(username=username, password=password)


def cleanup_users(username: str):
    User = get_user_model()
    User.objects.filter(username=username).delete()


@pytest.fixture
def prep_dkron():
    p = subprocess.Popen(["surface/manage.py", "run_dkron", "-s"])
    time.sleep(5)  # puke, but required to start dkron properly
    yield p
    p.kill()


@pytest.fixture
def prep_scanners():
    ScannerImage.objects.update_or_create(
        name="example", defaults={"image": "ghcr.io/surface-security/scanner-example"}
    )
    ScannerImage.objects.update_or_create(
        name="httpx", defaults={"image": "ghcr.io/surface-security/scanner-httpx"}
    )
    ScannerImage.objects.update_or_create(
        name="nmap", defaults={"image": "ghcr.io/surface-security/scanner-nmap"}
    )
    yield
    ScannerImage.objects.filter(name__in=["example", "httpx", "nmap"]).delete()


@pytest.fixture
def test_cfg(settings):
    """
    setupTests is a fixture to setup a generic environment to run the selenium tests.
    Setup should be comprised of setting up the test configuration (TestConfig) and generating dummy data for the tests.
    """
    # Setup env
    settings.USERNAME = "admin"
    settings.PASSWORD = "admin"
    settings.SURF_ALLOWED_HOSTS = "*"

    cfg = setup_config(settings.USERNAME, settings.PASSWORD)
    prep_users(settings.USERNAME, settings.PASSWORD)

    # Run tests
    yield cfg

    # Teardown
    cfg.driver.close()
    cleanup_users(settings.USERNAME)
