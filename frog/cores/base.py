from dataclasses import dataclass
from enum import Enum
from typing import Callable


class State(Enum):
    pass


@dataclass(slots=True)
class Context:
    state: State


class Event(Exception):
    pass


class ActionError(Event):
    pass


class Action:
    def __init__(
        self,
        fun: Callable[[Context], None],
        exception_to_action_error_map: dict[type[Exception], ActionError],
        unknown_exception_error: ActionError,
    ) -> None:
        self.exception_to_action_error_map = exception_to_action_error_map
        self.unknown_exception_error = unknown_exception_error
        self.fun = fun

    def run(self, context: Context) -> None:
        try:
            self.fun(context)
        except Exception as e:
            raise self.get_action_error(e) from e

    def get_action_error(self, exception: Exception) -> ActionError:
        for exception_class, error in self.exception_to_action_error_map.items():
            if isinstance(exception, (exception_class,)):
                return error
        return self.unknown_exception_error


class ChangeState(Action):
    def __init__(self, state: State) -> None:
        self._state = state

    def run(self, context: Context) -> None:
        context.state = self._state
