import enum
from typing import ClassVar, Optional


class State(enum.Enum):
    pass


class Event(enum.Enum):
    pass


class Action(enum.Enum):
    pass


class ActionError:
    pass


ActionSuccessMap = dict[Action, tuple[Optional[Action], Optional[State]]]


ActionFailureMap = dict[
    tuple[Action, Optional[ActionError]],
    tuple[Optional[Action], Optional[State]],
]


StateEventMap = dict[
    tuple[Optional[State], Optional[Event]],
    tuple[Optional[Action], Optional[State]],
]


class Core:

    initial_state: State

    action_success_map: ActionSuccessMap

    action_failure_map: ActionFailureMap

    state_event_map: StateEventMap

    def wait_for_event(self) -> Event:
        raise NotImplementedError

    def do_action(self, action: Action) -> Optional[ActionError]:
        raise NotImplementedError

    def __init__(self) -> None:
        self.state: State = self.__class__.initial_state

    def run(self):
        while True:
            event = self.wait_for_event()
            action, state = self.get_action_or_state(event)
            self.apply_action_or_change_state(action, state)

    def apply_action_or_change_state(
        self,
        action: Optional[Action],
        state: Optional[State],
    ) -> None:
        if action is None:
            self.state = state
            return

        error = self.do_action(action)
        if error is None:
            action, state = self.on_action_success(action)
        else:
            action, state = self.on_action_failure(action, error)
        self.apply_action_or_change_state(action, state)

    def get_action_or_state(
        self,
        event: Event,
    ) -> tuple[Optional[Action], Optional[State]]:
        if (self.state, event) in self.state_event_map:
            return self.state_event_map[(self.state, event)]
        return self.state_event_map[(None, event)]

    def on_action_success(
        self,
        action: Action,
    ) -> tuple[Optional[Action], Optional[State]]:
        return self.action_success_map[action]

    def on_action_failure(
        self,
        action: Action,
        error: ActionError,
    ) -> tuple[Optional[Action], Optional[State]]:
        if (action, error) in self.action_failure_map:
            return self.action_failure_map[(action, error)]
        return self.action_failure_map[(action, None)]
