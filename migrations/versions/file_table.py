"""
ファイルテーブル作成用のマイグレーション
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime
from sqlalchemy.sql import column, table

# 修正バージョンID
revision = 'file_table_2025_03_21'
down_revision = 'ac59d644c636'  # 直前のマイグレーションID
branch_labels = None
depends_on = None

def upgrade():
    """
    ファイルテーブルを作成する
    """
    op.create_table(
        'files',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=True),
        sa.Column('related_id', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.now),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # インデックスの作成
    op.create_index('ix_files_related_id', 'files', ['related_id'])
    op.create_index('ix_files_file_type', 'files', ['file_type'])
    op.create_index('ix_files_created_at', 'files', ['created_at'])

def downgrade():
    """
    ファイルテーブルを削除する
    """
    op.drop_index('ix_files_created_at', 'files')
    op.drop_index('ix_files_file_type', 'files')
    op.drop_index('ix_files_related_id', 'files')
    op.drop_table('files') 