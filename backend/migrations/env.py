from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config,pool
from app.config import settings
from app.database import Base
import app.models,app.phase3,app.phase4,app.phase5,app.phase6,app.phase7,app.phase8,app.phase9,app.phase10,app.phase12,app.security,app.audit
config=context.config
config.set_main_option("sqlalchemy.url",settings.database_url)
if config.config_file_name: fileConfig(config.config_file_name)
target_metadata=Base.metadata
def offline():
    context.configure(url=settings.database_url,target_metadata=target_metadata,literal_binds=True,compare_type=True)
    with context.begin_transaction(): context.run_migrations()
def online():
    connectable=engine_from_config(config.get_section(config.config_ini_section),prefix="sqlalchemy.",poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection,target_metadata=target_metadata,compare_type=True)
        with context.begin_transaction(): context.run_migrations()
offline() if context.is_offline_mode() else online()
