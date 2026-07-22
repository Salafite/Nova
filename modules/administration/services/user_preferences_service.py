from modules.administration.repositories.user_preferences_repo import UserPreferencesRepo


class UserPreferencesService:
    def __init__(self):
        self.repo = UserPreferencesRepo()

    def get_all(self, user_id: int) -> dict[str, str]:
        return self.repo.get_all(user_id)

    def save(self, user_id: int, preferences: dict[str, str]) -> dict:
        updated = self.repo.upsert(user_id, preferences)
        return {'updated': updated, 'preferences': self.repo.get_all(user_id)}
