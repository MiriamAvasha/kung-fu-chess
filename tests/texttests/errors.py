class ScriptParseError(Exception):
    def __init__(self, line: str, reason: str):
        self.line = line
        self.reason = reason
        super().__init__(f"Invalid command '{line}': {reason}")
