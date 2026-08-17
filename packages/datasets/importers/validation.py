from packages.benchmark.models.task import EvaluationConfig, Task

from ..models import DatasetManifest, DatasetPack


class ValidationImporter:
    """Provides a small, consistent 10-task set for provider validation."""

    def __init__(self):
        eval_conf = EvaluationConfig(
            extractor="code_block", normalizer="noop", judge="exact_match", metrics=["accuracy"]
        )

        def make_task(id_num: int, name: str, prompt: str, tests: str) -> Task:
            return Task(
                task_id=f"val-{id_num}",
                title=f"Validation {id_num}",
                description=prompt,
                input=prompt,
                expected_output="",
                hidden_tests=tests.split("\n"),
                evaluation=eval_conf,
                metadata={"entry_point": name},
                dataset_version_id=None,
            )

        self.tasks = [
            make_task(
                1,
                "reverse_string",
                "Write a python function `reverse_string(s: str) -> str` that returns the reversed string.",
                "assert reverse_string('hello') == 'olleh'\nassert reverse_string('') == ''",
            ),
            make_task(
                2,
                "is_palindrome",
                "Write a python function `is_palindrome(s: str) -> bool` that checks if a string is a palindrome.",
                "assert is_palindrome('racecar') == True\nassert is_palindrome('hello') == False",
            ),
            make_task(
                3,
                "binary_search",
                "Write a python function `binary_search(arr: list, target: int) -> int` that returns the index of target in a sorted list arr, or -1 if not found.",
                "assert binary_search([1,2,3,4,5], 4) == 3\nassert binary_search([1,2], 3) == -1",
            ),
            make_task(
                4,
                "fibonacci",
                "Write a python function `fibonacci(n: int) -> int` that returns the nth Fibonacci number, where fibonacci(0)=0 and fibonacci(1)=1.",
                "assert fibonacci(0) == 0\nassert fibonacci(1) == 1\nassert fibonacci(5) == 5\nassert fibonacci(10) == 55",
            ),
            make_task(
                5,
                "fizzbuzz",
                "Write a python function `fizzbuzz(n: int) -> list` that returns a list of strings from 1 to n where multiples of 3 are 'Fizz', multiples of 5 are 'Buzz', multiples of both are 'FizzBuzz', else the string representation of the number.",
                "assert fizzbuzz(3) == ['1', '2', 'Fizz']\nassert fizzbuzz(5) == ['1', '2', 'Fizz', '4', 'Buzz']\nassert fizzbuzz(15)[14] == 'FizzBuzz'",
            ),
            make_task(
                6,
                "is_balanced",
                "Write a python function `is_balanced(s: str) -> bool` that returns True if parentheses '()' are balanced.",
                "assert is_balanced('()') == True\nassert is_balanced('(()())') == True\nassert is_balanced(')(') == False\nassert is_balanced('(()') == False",
            ),
            make_task(
                7,
                "LRUCache",
                "Write a python class `LRUCache` with methods `__init__(self, capacity: int)`, `get(self, key: int) -> int` (returns -1 if not found), and `put(self, key: int, value: int) -> None`.",
                "cache = LRUCache(2)\ncache.put(1, 1)\ncache.put(2, 2)\nassert cache.get(1) == 1\ncache.put(3, 3)\nassert cache.get(2) == -1",
            ),
            make_task(
                8,
                "merge_intervals",
                "Write a python function `merge_intervals(intervals: list[list[int]]) -> list[list[int]]` that merges overlapping intervals.",
                "assert merge_intervals([[1,3],[2,6],[8,10],[15,18]]) == [[1,6],[8,10],[15,18]]\nassert merge_intervals([[1,4],[4,5]]) == [[1,5]]",
            ),
            make_task(
                9,
                "topological_sort",
                "Write a python function `topological_sort(num_nodes: int, edges: list[list[int]]) -> list[int]` that returns a valid topological ordering or an empty list if there's a cycle.",
                "res = topological_sort(2, [[1,0]])\nassert res == [1,0] or res == [0,1]\nassert topological_sort(2, [[1,0],[0,1]]) == []",
            ),
            make_task(
                10,
                "dijkstra",
                "Write a python function `dijkstra(n: int, edges: list[list[int]], start: int) -> list[int]` where edges are [u, v, weight]. Return a list of shortest distances from start to all nodes (0 to n-1), use float('inf') if unreachable.",
                "assert dijkstra(3, [[0,1,1],[1,2,2]], 0) == [0, 1, 3]\nassert dijkstra(3, [[0,1,4],[0,2,1],[2,1,1]], 0) == [0, 2, 1]",
            ),
        ]

    def import_pack(self) -> DatasetPack:
        manifest = DatasetManifest(
            id="validation",
            name="Validation",
            version="1.0",
            source="Atlas",
            license="MIT",
            citation="",
            language="python",
            evaluation="execution",
            metric="pass@1",
            tasks=10,
            tags=["validation"],
        )
        return DatasetPack(manifest=manifest, tasks=self.tasks)
