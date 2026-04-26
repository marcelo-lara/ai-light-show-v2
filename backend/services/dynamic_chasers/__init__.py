from typing import Dict, Any, Callable, List
from .wave import dynamic_wave_generator

# Registry for dynamic generator lookup
# This allows the expansion engine to resolve generator_id to a function
GENERATORS: Dict[str, Callable[[Dict[str, Any]], List[Dict[str, Any]]]] = {
    "dynamic_wave_generator": dynamic_wave_generator,
}