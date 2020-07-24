
class StartupError(Exception):
    def __repr__(self) -> str:
        return f"Error: {self.args[0]}" # pylint: disable=unsubscriptable-object
