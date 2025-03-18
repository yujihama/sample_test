"""
マイグレーションマネージャ

データベーススキーマのマイグレーションを管理するユーティリティ
"""

import os
import importlib
import pkgutil
from datetime import datetime
import uuid
from pathlib import Path
from loguru import logger
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from core.config import settings
from models.db_models import Base


class MigrationManager:
    """
    データベースマイグレーションを管理するクラス
    """
    
    def __init__(self, database_url=None):
        """
        マイグレーションマネージャを初期化
        
        Args:
            database_url: データベース接続URL（省略時はsettingsから取得）
        """
        self.database_url = database_url or settings.DATABASE_URL
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # migrations_versionテーブルが存在しない場合は作成
        self._ensure_migrations_table()
    
    def _ensure_migrations_table(self):
        """migrations_versionテーブルが存在することを確認"""
        try:
            inspector = inspect(self.engine)
            if not inspector.has_table("migrations_version"):
                with self.engine.begin() as conn:
                    conn.execute(text("""
                    CREATE TABLE migrations_version (
                        id VARCHAR(36) PRIMARY KEY,
                        version VARCHAR(255) NOT NULL,
                        applied_at TIMESTAMP NOT NULL
                    )
                    """))
                logger.info("migrations_versionテーブルを作成しました")
        except Exception as e:
            logger.error(f"migrations_versionテーブルの作成中にエラーが発生しました: {e}")
            raise
    
    def get_applied_migrations(self):
        """適用済みのマイグレーションの一覧を取得"""
        with self.SessionLocal() as session:
            result = session.execute(text("SELECT version FROM migrations_version ORDER BY applied_at"))
            return [row[0] for row in result.fetchall()]
    
    def record_migration(self, version):
        """マイグレーションを記録"""
        with self.SessionLocal() as session:
            try:
                migration_id = str(uuid.uuid4())
                now = datetime.utcnow()
                session.execute(
                    text("INSERT INTO migrations_version (id, version, applied_at) VALUES (:id, :version, :applied_at)"),
                    {"id": migration_id, "version": version, "applied_at": now}
                )
                session.commit()
                logger.info(f"マイグレーション {version} を記録しました")
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"マイグレーションの記録中にエラーが発生しました: {e}")
                raise
    
    def run_migrations(self):
        """すべてのマイグレーションを実行"""
        logger.info("データベースマイグレーションを開始します...")
        
        # 適用済みのマイグレーションを取得
        applied_migrations = self.get_applied_migrations()
        logger.debug(f"適用済みのマイグレーション: {applied_migrations}")
        
        # マイグレーションスクリプトを取得
        migrations_dir = Path(__file__).parent / "versions"
        if not migrations_dir.exists():
            logger.warning(f"マイグレーションディレクトリが存在しません: {migrations_dir}")
            return
        
        # スクリプトをソートして実行
        migration_files = sorted([f.name for f in migrations_dir.glob("*.py") if f.name != "__init__.py"])
        
        if not migration_files:
            logger.info("実行するマイグレーションがありません")
            return
        
        for migration_file in migration_files:
            # ファイル名からバージョンを取得
            version = migration_file.replace(".py", "")
            
            # 既に適用済みならスキップ
            if version in applied_migrations:
                logger.debug(f"マイグレーション {version} は既に適用済みです")
                continue
            
            try:
                # マイグレーションモジュールをインポート
                module_path = f"src.migrations.versions.{version}"
                migration_module = importlib.import_module(module_path)
                
                # upgradeメソッドを実行
                if hasattr(migration_module, "upgrade"):
                    logger.info(f"マイグレーション {version} を適用しています...")
                    migration_module.upgrade(self.engine)
                    
                    # 成功したらレコードに追加
                    self.record_migration(version)
                    logger.info(f"マイグレーション {version} を適用しました")
                else:
                    logger.warning(f"マイグレーション {version} にupgradeメソッドがありません")
            
            except Exception as e:
                logger.error(f"マイグレーション {version} の適用中にエラーが発生しました: {e}")
                raise
        
        logger.info("すべてのマイグレーションが完了しました")
    
    def create_migration(self, name):
        """新しいマイグレーションファイルを作成"""
        # マイグレーションディレクトリを作成
        migrations_dir = Path(__file__).parent / "versions"
        migrations_dir.mkdir(exist_ok=True)
        
        # __init__.pyが存在しない場合は作成
        init_file = migrations_dir / "__init__.py"
        if not init_file.exists():
            with open(init_file, "w", encoding="utf-8") as f:
                f.write('"""マイグレーションバージョン"""')
        
        # タイムスタンプベースのバージョン
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        version = f"{timestamp}_{name}"
        
        # マイグレーションファイルを作成
        migration_file = migrations_dir / f"{version}.py"
        
        with open(migration_file, "w", encoding="utf-8") as f:
            f.write(f'''"""
マイグレーション: {name}
作成日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

from sqlalchemy import text


def upgrade(engine):
    """マイグレーションを適用"""
    with engine.begin() as conn:
        # ここにマイグレーションのSQLを記述
        # 例: conn.execute(text("CREATE TABLE example (id INTEGER PRIMARY KEY)"))
        pass


def downgrade(engine):
    """マイグレーションを戻す"""
    with engine.begin() as conn:
        # ここにロールバック用のSQLを記述
        # 例: conn.execute(text("DROP TABLE IF EXISTS example"))
        pass
''')
        
        logger.info(f"マイグレーションファイルを作成しました: {migration_file}")
        return str(migration_file)
    
    def create_initial_migration(self):
        """初期マイグレーションを作成"""
        migrations_dir = Path(__file__).parent / "versions"
        migrations_dir.mkdir(exist_ok=True)
        
        # __init__.pyが存在しない場合は作成
        init_file = migrations_dir / "__init__.py"
        if not init_file.exists():
            with open(init_file, "w", encoding="utf-8") as f:
                f.write('"""マイグレーションバージョン"""')
        
        # 初期マイグレーションファイル
        version = "20230101000000_initial"
        migration_file = migrations_dir / f"{version}.py"
        
        with open(migration_file, "w", encoding="utf-8") as f:
            f.write('''"""
初期マイグレーション
Base.metadata.create_all()を使用してすべてのテーブルを作成
"""

from models.db_models import Base


def upgrade(engine):
    """初期スキーマを作成"""
    Base.metadata.create_all(bind=engine)


def downgrade(engine):
    """すべてのテーブルを削除"""
    Base.metadata.drop_all(bind=engine)
''')
        
        logger.info(f"初期マイグレーションファイルを作成しました: {migration_file}")
        return str(migration_file)


def run_migrations():
    """マイグレーションを実行するユーティリティ関数"""
    manager = MigrationManager()
    manager.run_migrations()


if __name__ == "__main__":
    # マイグレーションマネージャを初期化して実行
    manager = MigrationManager()
    manager.run_migrations() 