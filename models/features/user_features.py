from dataclasses import dataclass

@dataclass(frozen=True)
class UserFeatures:
    user_id: str
    recipe_id: str
    rating: int
    time_viewed: int
    times_cooked: int
    saved: bool

