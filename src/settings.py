"""This module contains all the software (not model) specific settings
"""
import os
from typing import List
from pydantic import (
    BaseSettings,
    AnyHttpUrl,
    SecretStr,
    HttpUrl,
)
import pytz


class Settings(BaseSettings):
    LOCAL_TZ = pytz.timezone("Europe/Copenhagen")
    BUCKET_NAME: str


class ScraperSettings(BaseSettings):
    Hello = "No"


class GuadianSiteSettings(BaseSettings):
    BASE_URL = "https://www.theguardian.com/football/premierleague+tone/matchreports"


settings = Settings()
scrabersettings = ScraperSettings()
guardiansitesettings = GuadianSiteSettings()
