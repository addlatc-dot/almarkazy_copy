"""Add queue_position column

Revision ID: 550c8b2f2d9a
Revises: 33610eb7d65e
Create Date: 2026-04-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '550c8b2f2d9a'
down_revision = '33610eb7d65e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('visit', schema=None) as batch_op:
        batch_op.add_column(sa.Column('queue_position', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('visit', schema=None) as batch_op:
        batch_op.drop_column('queue_position')
