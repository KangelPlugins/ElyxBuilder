class ParseError(Exception):
    def __init__(self, message, file, line):
        self.message = message
        self.file = file
        self.line = line
        super().__init__(str(self))
    def __str__(self):
        return f"[parse error] {self.file}:{self.line}: {self.message}"


class ElyxRuntimeError(Exception):
    def __init__(self, message, step=None):
        self.message = message
        self.step = step
        super().__init__(str(self))
    def __str__(self):
        if self.step:
            return f"[{self.step}] {self.message}"
        return self.message

class ScriptExit(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(f"script exit with code {code}")


class ContextError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)
    def __str__(self):
        return self.message
