import enum
from typing import Optional


class ActionError:
    pass

class Core:
    class State(enum.Enum):
        pass

    class Event(enum.Enum):
        pass

    class Action(enum.Enum):
        pass

    initial_state = None

    action_success_map: dict[Action, tuple[Optional[Action], Optional[State]]] = {}

    action_failure_map: dict[tuple[Action, Optional[ActionError]], tuple[Optional[Action], Optional[State]]] = {}

    state_event_map = dict[tuple[Optional[State], Optional[Event]], tuple[Optional[Action], Optional[State]]] = {}

    def wait_for_event(self) -> Event:
        raise NotImplementedError

    def do_action(self, action: Action) -> Optional[ActionError]:
        raise NotImplementedError

    def __init__(self) -> None:
        self.state: self.State = self.__class__.initial_state

    def run(self):
        while True:
            event = self.wait_for_event()
            action, state = self.get_action_or_state(event)
            self.apply_action_or_change_state(action, state)

    def apply_action_or_change_state(self, action: Optional[Action], state: Optional[State]) -> None:
        if action is None:
            self.state = state
            return None

        error = self.do_action(action)
        if error is None:
            action, state = self.on_action_success(action)
        else:
            action, state = self.on_action_failure(action, error)
        self.apply_action_or_change_state(action, state)

    def get_action_or_state(self, event: Event) -> tuple[Optional[Action], Optional[State]]:
        if (self.state, event) in self.state_event_map:
            return self.state_event_map[(self.state, event)]
        return self.state_event_map[(None, event)]

    def on_action_success(self, action: Action) -> tuple[Optional[Action], Optional[State]]:
        return self.action_success_map[action]

    def on_action_failure(self, action: Action, error: ActionError) -> tuple[Optional[Action], Optional[State]]:
        if (action, error) in self.action_failure_map:
            return self.action_failure_map[(action, error)]
        return self.action_failure_map[(action, None)]
