"""ENESKO Category 2 database baseline."""
from alembic import op
from app.database import Base
import app.models,app.phase3,app.phase4,app.phase5,app.phase6,app.phase7,app.phase8,app.phase9,app.phase10,app.phase12,app.security,app.audit
revision="0001_category2_baseline"
down_revision=None
branch_labels=None
depends_on=None
def upgrade(): Base.metadata.create_all(bind=op.get_bind())
def downgrade(): Base.metadata.drop_all(bind=op.get_bind())
