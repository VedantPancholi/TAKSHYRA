import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    redis_url: str
    output_dir: str
    fixture_path: str
    demo_passwords: dict[str, str]

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.getenv("APP_ENV")
        if env != "development":
            raise RuntimeError("M1 supports development only; production identity is not configured")
        demo_passwords = {}
        for slug in ("demo-a", "demo-b"):
            for role in ("executor", "viewer"):
                name = f"{slug}-{role}"
                key = f"DEMO_{slug[-1].upper()}_{role.upper()}_PASSWORD"
                password = os.getenv(key, "")
                if len(password) < 16 or password == "REPLACE_WITH_A_RANDOM_LOCAL_PASSWORD":
                    raise RuntimeError(f"{key} must be a non-placeholder value of at least 16 characters")
                demo_passwords[name] = password
        if len(set(demo_passwords.values())) != len(demo_passwords):
            raise RuntimeError("Demo identity passwords must be distinct")
        return cls(
            app_env=env,
            database_url=os.getenv("DATABASE_URL", ""),
            redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
            output_dir=os.getenv("OUTPUT_DIR", "/app/data/output"),
            fixture_path=os.getenv("FIXTURE_PATH", "/app/seed/synthetic_orders.csv"),
            demo_passwords=demo_passwords,
        )
