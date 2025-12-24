"""add upload_limit_mb to user

Revision ID: f9a23bc45d67
Revises: 1a31ce608336
Create Date: 2024-12-24 17:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f9a23bc45d67'
down_revision = '1a31ce608336'
branch_labels = None
depends_on = None


def upgrade():
    # Add upload_limit_mb column to user table
    op.add_column('user', sa.Column('upload_limit_mb', sa.Integer(), nullable=False, server_default='100'))
    # Remove server_default after adding the column
    op.alter_column('user', 'upload_limit_mb', server_default=None)


def downgrade():
    # Remove upload_limit_mb column from user table
    op.drop_column('user', 'upload_limit_mb')

