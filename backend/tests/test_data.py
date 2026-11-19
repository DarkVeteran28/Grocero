import importlib.util
from pathlib import Path


def _generator():
    path = Path(__file__).resolve().parents[2] / "data" / "generate_data.py"
    spec = importlib.util.spec_from_file_location("generate_data", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_dataset_rules():
    module = _generator()
    datasets = module.build_datasets()
    module.validate_datasets(datasets)
    assert (module.DATA_DIR / "prices.csv").is_file()
    assert (module.DATA_DIR / "products.csv").is_file()
