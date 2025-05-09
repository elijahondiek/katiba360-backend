import os
from decouple import config

ENVIRONMENT = config("ENVIRONMENT")

DATABASE_URL = config("DATABASE_URL")
REDIS_URL = config("REDIS_URL")