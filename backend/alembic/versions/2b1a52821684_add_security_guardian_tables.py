"""add_security_guardian_tables

Revision ID: 2b1a52821684
Revises: 1a0c41410573
Create Date: 2026-10-23 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b1a52821684'
down_revision: Union[str, None] = '1a0c41410573'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'security_findings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('patch_id', sa.String(length=36), nullable=True),
        sa.Column('patch_revision', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('patch_hash', sa.String(length=64), nullable=False),
        sa.Column('base_commit_sha', sa.String(length=40), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('rule_id', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('confidence', sa.String(length=20), nullable=False, server_default='HIGH'),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('line_start', sa.Integer(), nullable=True),
        sa.Column('line_end', sa.Integer(), nullable=True),
        sa.Column('evidence_redacted', sa.Text(), nullable=True),
        sa.Column('remediation', sa.Text(), nullable=True),
        sa.Column('scanner_name', sa.String(length=50), nullable=False),
        sa.Column('scanner_version', sa.String(length=50), nullable=True),
        sa.Column('advisory_id', sa.String(length=100), nullable=True),
        sa.Column('is_blocking', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['patch_id'], ['patches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('security_findings', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_security_findings_run_id'), ['run_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_security_findings_patch_id'), ['patch_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_security_findings_patch_hash'), ['patch_hash'], unique=False)
        batch_op.create_index(batch_op.f('ix_security_findings_category'), ['category'], unique=False)
        batch_op.create_index(batch_op.f('ix_security_findings_rule_id'), ['rule_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_security_findings_severity'), ['severity'], unique=False)

    op.create_table(
        'security_scan_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('patch_id', sa.String(length=36), nullable=True),
        sa.Column('patch_revision', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('patch_hash', sa.String(length=64), nullable=False),
        sa.Column('base_commit_sha', sa.String(length=40), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('findings_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('critical_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('high_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('medium_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('low_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('info_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('block_reasons', sa.JSON(), nullable=False),
        sa.Column('scanners_executed', sa.JSON(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['patch_id'], ['patches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('security_scan_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_security_scan_records_run_id'), ['run_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_security_scan_records_patch_id'), ['patch_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_security_scan_records_patch_hash'), ['patch_hash'], unique=False)
        batch_op.create_index(batch_op.f('ix_security_scan_records_status'), ['status'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('security_scan_records', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_security_scan_records_status'))
        batch_op.drop_index(batch_op.f('ix_security_scan_records_patch_hash'))
        batch_op.drop_index(batch_op.f('ix_security_scan_records_patch_id'))
        batch_op.drop_index(batch_op.f('ix_security_scan_records_run_id'))
    op.drop_table('security_scan_records')

    with op.batch_alter_table('security_findings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_security_findings_severity'))
        batch_op.drop_index(batch_op.f('ix_security_findings_rule_id'))
        batch_op.drop_index(batch_op.f('ix_security_findings_category'))
        batch_op.drop_index(batch_op.f('ix_security_findings_patch_hash'))
        batch_op.drop_index(batch_op.f('ix_security_findings_patch_id'))
        batch_op.drop_index(batch_op.f('ix_security_findings_run_id'))
    op.drop_table('security_findings')
