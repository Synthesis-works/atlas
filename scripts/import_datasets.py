import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packages.datasets.importers.humaneval import HumanEvalImporter
from packages.datasets.importers.mbpp import MBPPImporter


def main():
    print("Testing HumanEval Importer...")
    he_importer = HumanEvalImporter()
    he_pack = he_importer.import_pack()
    print("HumanEval Pack Manifest:")
    print(json.dumps(he_pack.manifest.model_dump(), indent=2))
    print("\nHumanEval Import Stats:")
    print(json.dumps(he_pack.stats.model_dump(), indent=2))
    print(f"\nSample Task ID: {he_pack.tasks[0].task_id}")
    print(f"Sample Input: {he_pack.tasks[0].input[:50]}...")

    print("-" * 50)

    print("Testing MBPP Importer...")
    mbpp_importer = MBPPImporter()
    mbpp_pack = mbpp_importer.import_pack()
    print("MBPP Pack Manifest:")
    print(json.dumps(mbpp_pack.manifest.model_dump(), indent=2))
    print("\nMBPP Import Stats:")
    print(json.dumps(mbpp_pack.stats.model_dump(), indent=2))
    print(f"\nSample Task ID: {mbpp_pack.tasks[0].task_id}")
    print(f"Sample Input: {mbpp_pack.tasks[0].input[:50]}...")


if __name__ == "__main__":
    main()
