class PromptResolver:
    @staticmethod
    def resolve(template: str, input_data: dict) -> str:
        """
        Hydrates a prompt template with the given input data using basic Python string formatting.
        Handles missing keys gracefully.
        """
        try:
            return template.format(**input_data)
        except KeyError as e:
            # Fallback if the template references a key not in input_data
            # In a real system, we might want to fail the test case, but returning the raw string
            # or partial formatting could also work. Let's fail fast for missing keys for now.
            raise ValueError(f"Missing key in input_data for prompt template: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid format in prompt template: {e}")
