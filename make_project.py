from pathlib import Path


FOLDERS = [
    ".github/workflows",
    "cmake",
    "csrc/include/core",
    "csrc/include/bindings",
    "csrc/src",
    "csrc/bindings",
    "src/tct_engine/ingestion",
    "src/tct_engine/microstructure",
    "src/tct_engine/execution",
    "src/tct_engine/risk",
    "src/tct_engine/utils",
    "tests/unit",
    "tests/integration",
    "tests/cpp",
    "config",
    "scripts",
]

PACKAGE_FILES = [
    "src/tct_engine/__init__.py",
    "src/tct_engine/ingestion/__init__.py",
    "src/tct_engine/microstructure/__init__.py",
    "src/tct_engine/execution/__init__.py",
    "src/tct_engine/risk/__init__.py",
    "src/tct_engine/utils/__init__.py",
]


def create_directories() -> None:
    for folder in FOLDERS:
        Path(folder).mkdir(parents=True, exist_ok=True)


def create_package_files() -> None:
    for package_file in PACKAGE_FILES:
        Path(package_file).touch(exist_ok=True)


def create_gitignore() -> None:
    Path(".gitignore").write_text(
        "\n".join(
            [
                "__pycache__/",
                "*.py[cod]",
                "*.pyd",
                "*.so",
                "*.dll",
                ".pytest_cache/",
                ".ruff_cache/",
                ".mypy_cache/",
                "build/",
                "dist/",
                "*.egg-info/",
                ".venv/",
                ".env",
                "*.log",
                "",
            ]
        ),
        encoding="utf-8",
    )


def create_pyproject() -> None:
    Path("pyproject.toml").write_text(
        """[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "tct-quant-engine"
version = "0.1.0"
description = "Event-driven TCT/Wyckoff liquidity and market microstructure engine"
readme = "README.md"
requires-python = ">=3.11,<3.13"
dependencies = [
    "numpy>=1.26",
    "pandas>=2.1",
    "polars>=0.20",
    "pydantic>=2.5",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "black>=24.0",
    "ruff>=0.4",
    "mypy>=1.10",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-ra"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.black]
line-length = 100
target-version = ["py311"]
""",
        encoding="utf-8",
    )


def create_types_module() -> None:
    Path("src/tct_engine/utils/types.py").write_text(
        """from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto


class MarketBias(Enum):
    BULLISH = auto()
    BEARISH = auto()
    NEUTRAL = auto()


class RangeStatus(Enum):
    FORMING = auto()
    ACTIVE = auto()
    DEVIATING = auto()
    INVALIDATED = auto()
    COMPLETED = auto()


@dataclass(frozen=True, slots=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class SwingPoint:
    index: int
    price: float
    is_high: bool
    timestamp: datetime
""",
        encoding="utf-8",
    )


def create_initial_test() -> None:
    Path("tests/unit/test_types.py").write_text(
        """from tct_engine.utils.types import MarketBias, RangeStatus


def test_market_bias_values_are_distinct() -> None:
    assert MarketBias.BULLISH is not MarketBias.BEARISH


def test_range_status_values_are_distinct() -> None:
    assert RangeStatus.ACTIVE is not RangeStatus.INVALIDATED
""",
        encoding="utf-8",
    )


def create_readme() -> None:
    Path("README.md").write_text(
        "# TCT Quant Engine\n\n"
        "Event-driven TCT/Wyckoff liquidity and market microstructure engine.\n",
        encoding="utf-8",
    )


def main() -> None:
    create_directories()
    create_package_files()
    create_gitignore()
    create_pyproject()
    create_types_module()
    create_initial_test()
    create_readme()

    print("Project skeleton successfully created in D:\\TCT")


if __name__ == "__main__":
    main()