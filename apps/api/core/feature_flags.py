import os


class FeatureFlags:
    @staticmethod
    def is_enabled(flag: str) -> bool:
        return os.getenv(f"FEATURE_{flag.upper()}", "false").lower() == "true"

    @property
    def mtn_momo(self) -> bool:
        return self.is_enabled("MTN_MOMO")

    @property
    def orange_money(self) -> bool:
        return self.is_enabled("ORANGE_MONEY")

    @property
    def virtual_card(self) -> bool:
        return self.is_enabled("VIRTUAL_CARD")

    @property
    def insurance(self) -> bool:
        return self.is_enabled("INSURANCE")

    @property
    def auto_save(self) -> bool:
        return self.is_enabled("AUTO_SAVE")

    @property
    def maintenance_mode(self) -> bool:
        return self.is_enabled("MAINTENANCE_MODE")

    @property
    def read_only_mode(self) -> bool:
        return self.is_enabled("READ_ONLY_MODE")


flags = FeatureFlags()
