"""
規程情報テーブルのメタデータフィールド名を変更するマイグレーション

Revision ID: regulation_metadata_field
Create Date: 2025-03-28 10:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'regulation_metadata_field'
down_revision = 'c1c390fac0d0'  # 初期スキーマのリビジョンID
branch_labels = None
depends_on = None


def upgrade():
    """メタデータフィールド名を 'meta_info' から 'meta_data' に変更"""
    # PostgreSQLでの実行方法
    # op.alter_column('regulations', 'meta_info', new_column_name='meta_data')
    
    # SQLiteでの実行方法（開発環境用）
    # 1. regulations_backupテーブルを作成
    # 2. データをコピー
    # 3. 古いテーブルを削除
    # 4. 新しいテーブルをリネーム
    
    # SQLite用の代替手段
    # 一時テーブルを作成
    op.execute('''
        CREATE TABLE regulations_backup (
            id VARCHAR PRIMARY KEY,
            code VARCHAR NOT NULL UNIQUE,
            title VARCHAR NOT NULL,
            category VARCHAR NOT NULL,
            content TEXT NOT NULL,
            structured_content TEXT,
            version VARCHAR NOT NULL,
            effective_date TIMESTAMP NOT NULL,
            expiration_date TIMESTAMP,
            parent_id VARCHAR,
            keywords TEXT,
            meta_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES regulations (id)
        )
    ''')
    
    # データを移行
    op.execute('''
        INSERT INTO regulations_backup 
        SELECT
            id, code, title, category, content, structured_content, 
            version, effective_date, expiration_date, parent_id, 
            keywords, meta_info, created_at, updated_at
        FROM regulations
    ''')
    
    # 元のテーブルを削除
    op.execute('DROP TABLE regulations')
    
    # 新しいテーブルをリネーム
    op.execute('ALTER TABLE regulations_backup RENAME TO regulations')


def downgrade():
    """メタデータフィールド名を 'meta_data' から 'meta_info' に戻す"""
    # PostgreSQLでの実行方法
    op.alter_column('regulations', 'meta_data', new_column_name='meta_info')
    
    # SQLiteでの実行方法（開発環境用）は省略（上記と同様のアプローチ） 