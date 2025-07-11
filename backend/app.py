from backend.models.fixtures_model import FixturesModel
from backend.config import FIXTURES_CONFIG

## Setup
fixtures = FixturesModel(fixtures_config_file=FIXTURES_CONFIG, debug=True)

