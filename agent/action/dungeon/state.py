from dataclasses import dataclass


@dataclass
class DungeonState:
    current_layer: int = 1
    should_leave: bool = False
    same_layer_retries: int = 0
    last_observed_layer: int = -1
    preprocessed_layer: int = -1

    def observe_layer(self, layer: int) -> bool:
        if layer <= 0:
            return False
        if layer != self.last_observed_layer:
            self.same_layer_retries = 0
            self.last_observed_layer = layer
        self.current_layer = layer
        return True

    def mark_retry(self) -> None:
        self.same_layer_retries += 1

    def mark_new_layer(self) -> None:
        self.preprocessed_layer = -1
