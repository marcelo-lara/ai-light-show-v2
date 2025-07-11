from pathlib import Path
import json
from typing import Optional

class FixtureModel:
    def __init__(self, id: str, name: str, fixture_type: str, channels: int):
        """
        Initialize a fixture model.
        Args:
            name (str): Name of the fixture.
            fixture_type (str): Type of the fixture (e.g., 'parcan', 'moving_head').
            channels (int): Number of DMX channels used by the fixture.
        """
        self.id = id
        self.name = name
        self.fixture_type = fixture_type
        self.channels = channels
    
    def arm(self) -> dict:
        """
        Arm the fixture for use.
        Returns:
            dict: Fixture properties.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    def set_color(self, color: tuple) -> None:
        """
        Set the color of the fixture.
        Args:
            color (tuple): RGB color values as a tuple (R, G, B).
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    def set_channel_value(self, channel: int, value: int) -> None:
        """
        Set a specific DMX channel value.
        Args:
            channel (int): DMX channel number (0-511).
            value (int): Value to set (0-255).
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    def get_channel(self, channel: str) -> int:
        """
        Get the DMX channel number of given channel .
        Args:
            channel (int): DMX channel number (0-511).
        Returns:
            int: Value of the specified channel (0-255).
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    def render_action(self, action: str, parameters: dict) -> None:
        """
        Render a specific action on the fixture.
        Args:
            action (str): Action name (e.g., 'flash', 'fade').
            parameters (dict): Parameters for the action.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    def __str__(self) -> str:
        """
        String representation of the fixture.
        Returns:
            str: Fixture name and type.
        """
        return f"[{self.fixture_type}|{self.name}]"

class RgbParcan(FixtureModel):
    def __init__(self, id: str, name: str):
        """
        Initialize an RGB Parcan fixture.
        Args:
            id (str): Unique identifier for the fixture.
            name (str): Name of the fixture.
        """
        super().__init__(id, name, 'parcan', 3)  # RGB Parcan uses 3 channels (R, G, B)
    
    def arm(self) -> dict:
        """
        Arm the RGB Parcan fixture.
        Returns:
            dict: Fixture properties.
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.fixture_type,
            "channels": self.channels
        }

class MovingHead(FixtureModel):
    def __init__(self, id: str, name: str):
        """
        Initialize an Moving Head fixture.
        Args:
            id (str): Unique identifier for the fixture.
            name (str): Name of the fixture.
        """
        super().__init__(id, name, 'moving_head', 3)  # RGB Parcan uses 3 channels (R, G, B)
    
    def arm(self) -> dict:
        """
        Arm the Moving Head fixture.
        Returns:
            dict: Fixture properties.
        """
        
        return {
            "id": self.id,
            "name": self.name,
            "type": self.fixture_type,
            "channels": self.channels
        }
    
class FixturesModel:
    def __init__(self, fixtures_config_file:Path, debug=False):
        """
        Initialize the FixturesModel with an empty fixture list.
        """
        self.fixtures = {}
        self.load_fixtures(fixtures_config_file, debug)

    def add_fixture(self, fixture: FixtureModel) -> None:
        """
        Add a fixture to the model.
        Args:
            fixture (FixtureModel): The fixture to add.
        """
        self.fixtures[fixture.id] = fixture

    def get_fixture(self, id: str) -> Optional[FixtureModel]:
        """
        Get a fixture by its ID.
        Args:
            id (str): Unique identifier of the fixture.
        Returns:
            Optional[FixtureModel]: The requested fixture, or None if not found.
        """
        return self.fixtures.get(id)
    
    def load_fixtures(self, fixtures_config_file:Path, debug=False) -> None:
        """
        Load fixtures from the fixtures.json file.
        This method initializes fixtures based on the provided data.
        Args:
            fixtures_data (list): List of fixture data dictionaries.
        """
        if not fixtures_config_file.exists():
            raise FileNotFoundError(f"Fixtures configuration file {fixtures_config_file} not found.")
        
        with open(fixtures_config_file, 'r') as f:
            fixtures_data = json.load(f)

        for fixture_data in fixtures_data:
            if fixture_data['type'] == 'rgb':
                fixture = RgbParcan(fixture_data['id'], fixture_data['name'])
            elif fixture_data['type'] == 'moving_head':
                fixture = MovingHead(fixture_data['id'], fixture_data['name'])
            else:
                continue
            self.add_fixture(fixture)
        
        if debug:
            print(f"Loaded {len(self.fixtures)} fixtures:")
            for fixture in self.fixtures.values():
                print(f"  - {fixture}")

        