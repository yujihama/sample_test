"""
ファイルテーブル作成用のマイグレーション
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, String, Integer, Text, DateTime
from datetime import datetime

# 修正バージョンID
revision = 'file_table_v1'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """
    ファイルテーブルを作成する
    """
    op.create_table(
        'files',
        Column('id', String, primary_key=True),
        Column('filename', String, nullable=False),
        Column('file_path', String, nullable=False),
        Column('file_type', String, nullable=False),
        Column('file_size', Integer, nullable=False),
        Column('content_type', String, nullable=True),
        Column('related_id', String, nullable=True, index=True),
        Column('description', Text, nullable=True),
        Column('file_metadata', Text, nullable=True),
        Column('created_at', DateTime, default=datetime.now),
        Column('updated_at', DateTime, nullable=True)
    )
    
    # インデックスの作成
    op.create_index('ix_files_file_type', 'files', ['file_type'])
    op.create_index('ix_files_created_at', 'files', ['created_at'])

def downgrade():
    """
    ファイルテーブルを削除する
    """
    op.drop_index('ix_files_created_at', 'files')
    op.drop_index('ix_files_file_type', 'files')
    op.drop_table('files') 