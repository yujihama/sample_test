"""add_sample_hierarchy

Revision ID: dc582fc60db9
Revises: 3e1d5461c376
Create Date: 2025-03-22 21:14:20.211412

"""
from typing import Sequence, Union
from datetime import datetime
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'dc582fc60db9'
down_revision: Union[str, None] = '3e1d5461c376'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 新規テーブル：sample_batches（バッチテーブル）
    op.create_table(
        'sample_batches',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('meta_data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 新規テーブル：samples（サンプルテーブル）
    op.create_table(
        'samples',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('batch_id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('file_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('meta_data', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['batch_id'], ['sample_batches.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 新規テーブル：sample_results（サンプル処理結果テーブル）
    op.create_table(
        'sample_results',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('workflow_id', sa.String(50), nullable=False),
        sa.Column('sample_id', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('result', sa.String(20), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('findings', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sample_id'], ['samples.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 新規テーブル：batch_upload_jobs（バッチアップロードジョブテーブル）
    op.create_table(
        'batch_upload_jobs',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('batch_id', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('total_folders', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processed_folders', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_files', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processed_files', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_files', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('errors', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('estimated_completion', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['batch_id'], ['sample_batches.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 既存テーブル変更：files（ファイルテーブル）- バッチモードで変更
    with op.batch_alter_table('files') as batch_op:
        batch_op.add_column(sa.Column('sample_id', sa.String(50), nullable=True))
        batch_op.create_foreign_key('fk_files_sample', 'samples', ['sample_id'], ['id'])
    
    # 既存テーブル変更：workflows（ワークフローテーブル）- バッチモードで変更
    with op.batch_alter_table('workflows') as batch_op:
        batch_op.add_column(sa.Column('sample_id', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('is_sample_level', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.create_foreign_key('fk_workflows_sample', 'samples', ['sample_id'], ['id'])
    
    # インデックス作成
    op.create_index('ix_sample_batches_created_at', 'sample_batches', ['created_at'])
    op.create_index('ix_samples_batch_id', 'samples', ['batch_id'])
    op.create_index('ix_samples_created_at', 'samples', ['created_at'])
    op.create_index('ix_sample_results_workflow_id', 'sample_results', ['workflow_id'])
    op.create_index('ix_sample_results_sample_id', 'sample_results', ['sample_id'])
    op.create_index('ix_files_sample_id', 'files', ['sample_id'])
    op.create_index('ix_workflows_sample_id', 'workflows', ['sample_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # インデックス削除
    op.drop_index('ix_workflows_sample_id', 'workflows')
    op.drop_index('ix_files_sample_id', 'files')
    op.drop_index('ix_sample_results_sample_id', 'sample_results')
    op.drop_index('ix_sample_results_workflow_id', 'sample_results')
    op.drop_index('ix_samples_created_at', 'samples')
    op.drop_index('ix_samples_batch_id', 'samples')
    op.drop_index('ix_sample_batches_created_at', 'sample_batches')
    
    # 外部キー制約削除とカラム削除 - バッチモードで変更
    with op.batch_alter_table('workflows') as batch_op:
        batch_op.drop_constraint('fk_workflows_sample', type_='foreignkey')
        batch_op.drop_column('is_sample_level')
        batch_op.drop_column('sample_id')
    
    with op.batch_alter_table('files') as batch_op:
        batch_op.drop_constraint('fk_files_sample', type_='foreignkey')
        batch_op.drop_column('sample_id')
    
    # テーブル削除
    op.drop_table('batch_upload_jobs')
    op.drop_table('sample_results')
    op.drop_table('samples')
    op.drop_table('sample_batches')
