"""Gemeinsame Test-Konfiguration."""
from pathlib import Path

import custom_components
import pytest

# Das Test-Plugin bringt ein eigenes `custom_components`-Paket mit; den Ordner
# dieses Repos dort einhängen, damit `custom_components.maico_kwl` gefunden wird.
_MINE = str(Path(__file__).resolve().parents[1] / "custom_components")
if _MINE not in custom_components.__path__:
    custom_components.__path__.append(_MINE)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
