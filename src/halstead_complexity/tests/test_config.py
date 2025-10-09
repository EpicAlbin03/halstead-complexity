from dataclasses import dataclass
from pathlib import Path

import pytest

from ..config import ConfigManager


@dataclass
class ConfigScenario:
    config: ConfigManager
    scenario: str
    local_exists: bool
    global_exists: bool


@pytest.fixture(scope="module")
def default_config_content():
    default_config_path = Path(__file__).parent.parent / "default_config.json"
    with open(default_config_path, "r") as f:
        return f.read()


@pytest.fixture(params=["both", "local_only", "global_only", "none"])
def config_scenario(
    request: pytest.FixtureRequest, tmp_path: Path, default_config_content: str
) -> ConfigScenario:
    scenario = request.param

    ConfigManager.reset_instance()

    local_config = tmp_path / "hc_config.json"
    global_config = tmp_path / "global_config.json"

    if scenario in ["both", "local_only"]:
        local_config.write_text(default_config_content)

    if scenario in ["both", "global_only"]:
        global_config.write_text(default_config_content)

    config = ConfigManager(
        local_file=str(local_config),
        global_file=str(global_config),
    )

    return ConfigScenario(
        config=config,
        scenario=scenario,
        local_exists=local_config.exists(),
        global_exists=global_config.exists(),
    )


class TestConfigPath:
    def test_no_flag(self, config_scenario: ConfigScenario) -> None:
        path, exists, config_type = config_scenario.config.get_config_file_path()
        config = ConfigManager.get_instance()

        if config_scenario.scenario == "both":
            assert config_type == "local"
            assert exists is True
            assert path == config.local_file
        elif config_scenario.scenario == "local_only":
            assert config_type == "local"
            assert exists is True
            assert path == config.local_file
        elif config_scenario.scenario == "global_only":
            assert config_type == "global"
            assert exists is True
            assert path == config.global_file
        elif config_scenario.scenario == "none":
            assert config_type == "default"
            assert exists is True
            assert path == config.default_file

    def test_global_flag(self, config_scenario: ConfigScenario) -> None:
        path, exists, config_type = config_scenario.config.get_config_file_path(
            global_=True
        )
        config = ConfigManager.get_instance()

        if config_scenario.scenario == "both":
            assert config_type == "global"
            assert exists is True
            assert path == config.global_file
        elif config_scenario.scenario == "local_only":
            assert config_type == "local"
            assert exists is False
            assert path == config.local_file
        elif config_scenario.scenario == "global_only":
            assert config_type == "global"
            assert exists is True
            assert path == config.global_file
        elif config_scenario.scenario == "none":
            assert config_type == "default"
            assert exists is False
            assert path == config.default_file

    def test_local_flag(self, config_scenario: ConfigScenario) -> None:
        path, exists, config_type = config_scenario.config.get_config_file_path(
            local=True
        )
        config = ConfigManager.get_instance()

        if config_scenario.scenario in ["both", "local_only"]:
            assert config_type == "local"
            assert exists is True
            assert path == config.local_file
        elif config_scenario.scenario == "global_only":
            assert config_type == "global"
            assert exists is False
            assert path == config.global_file
        elif config_scenario.scenario == "none":
            assert config_type == "default"
            assert exists is False
            assert path == config.default_file
