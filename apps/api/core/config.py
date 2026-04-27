from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_NAME: str = "TerahBank API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    PORT: int = 8000

    DATABASE_URL: str
    DATABASE_URL_READ: str = ""
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_SESSION_DB: int = 0
    REDIS_CACHE_DB: int = 1
    REDIS_JOBS_DB: int = 2

    JWT_PRIVATE_KEY_PATH: str
    JWT_PUBLIC_KEY_PATH: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "RS256"

    OTP_EXPIRE_MINUTES: int = 5
    OTP_MAX_RESEND_ATTEMPTS: int = 3
    OTP_SESSION_LOCK_MINUTES: int = 30

    BCRYPT_ROUNDS: int = 12
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # AWS / S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "af-south-1"
    AWS_S3_KYC_BUCKET: str = "terahbank-kyc-documents"

    # KYC upload limits
    KYC_MAX_FILE_SIZE_MB: int = 10

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str) -> str:
        return v  # kept as str; split when used: settings.CORS_ORIGINS.split(",")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # MTN Mobile Money
    MTN_MOMO_BASE_URL: str = "https://sandbox.momodeveloper.mtn.com"
    MTN_MOMO_API_KEY: str = ""
    MTN_MOMO_API_SECRET: str = ""
    MTN_MOMO_SUBSCRIPTION_KEY: str = ""
    MTN_MOMO_COLLECTION_USER_ID: str = ""
    MTN_MOMO_DISBURSEMENT_SUBSCRIPTION_KEY: str = ""
    MTN_MOMO_DISBURSEMENT_USER_ID: str = ""
    MTN_MOMO_DISBURSEMENT_API_KEY: str = ""
    MTN_MOMO_ENVIRONMENT: str = "sandbox"          # sandbox | production
    MTN_MOMO_WEBHOOK_SECRET: str = ""              # HMAC-SHA256 secret for callback validation
    MTN_MOMO_CALLBACK_URL: str = "https://api.terahbank.com/api/v1/webhooks/mtn-momo"
    MTN_MOMO_TIMEOUT_SECONDS: int = 120

    # VISA Card-Issuing Partner Gateway
    VISA_GATEWAY_BASE_URL: str = "https://api.visa-partner.com"       # Replace with real partner URL
    VISA_GATEWAY_API_KEY: str = ""
    VISA_GATEWAY_MERCHANT_ID: str = ""
    VISA_GATEWAY_WEBHOOK_SECRET: str = ""                              # HMAC-SHA256 for callback validation
    VISA_GATEWAY_CALLBACK_URL: str = "https://api.terahbank.com/api/v1/webhooks/visa-card"
    VISA_GATEWAY_SUCCESS_URL: str = "https://app.terahbank.com/deposit/success"
    VISA_GATEWAY_CANCEL_URL: str = "https://app.terahbank.com/deposit/cancel"
    VISA_GATEWAY_ENVIRONMENT: str = "sandbox"                         # sandbox | production
    VISA_MAX_CARDS_PER_USER: int = 3                                  # Configurable in admin

    # Orange Money
    ORANGE_MONEY_BASE_URL: str = "https://api.orange.com"
    ORANGE_MONEY_CLIENT_ID: str = ""
    ORANGE_MONEY_CLIENT_SECRET: str = ""
    ORANGE_MONEY_MERCHANT_ID: str = ""
    ORANGE_MONEY_MERCHANT_KEY: str = ""
    ORANGE_MONEY_WEBHOOK_SECRET: str = ""          # HMAC-SHA256 secret for callback validation
    ORANGE_MONEY_CALLBACK_URL: str = "https://api.terahbank.com/api/v1/webhooks/orange-money"
    ORANGE_MONEY_ENVIRONMENT: str = "sandbox"      # sandbox | production

    # Feature flags
    FEATURE_MTN_MOMO: bool = True
    FEATURE_ORANGE_MONEY: bool = True
    FEATURE_CARD_DEPOSIT: bool = True
    FEATURE_VIRTUAL_CARD: bool = True
    FEATURE_INSURANCE: bool = False
    FEATURE_AUTO_SAVE: bool = False
    FEATURE_MAINTENANCE_MODE: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
