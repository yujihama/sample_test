"""
プロンプトテンプレート機能を提供するモジュール
"""

import os
import re
import json
from src.utils import json_utils
import yaml
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class PromptTemplate:
    """
    プロンプトテンプレートを管理するクラス
    
    テンプレート内の変数を置換する機能を提供します。
    変数は {{variable_name}} の形式で指定します。
    """
    
    def __init__(self, template: str, metadata: Dict = None):
        """
        初期化
        
        Args:
            template: テンプレート文字列
            metadata: テンプレートに関するメタデータ
        """
        self.template = template
        self.metadata = metadata or {}
        self._variable_pattern = r'\{\{([^}]+)\}\}'
        
    def render(self, variables: Dict[str, Any]) -> str:
        """
        テンプレート内の変数を置換する
        
        Args:
            variables: 変数名と値のマッピング
            
        Returns:
            str: 変数が置換されたテンプレート文字列
        """
        result = self.template
        
        # 変数置換
        for match in re.finditer(self._variable_pattern, self.template):
            var_name = match.group(1).strip()
            
            if var_name in variables:
                value = variables[var_name]
                # 辞書やリストの場合はJSONに変換
                if isinstance(value, (dict, list)):
                    value = json_utils.json_serialize(value)
                result = result.replace(match.group(0), str(value))
            else:
                logger.warning(f"テンプレート変数 '{var_name}' が見つかりません")
                
        return result
        
    def extract_variables(self) -> List[str]:
        """
        テンプレート内の変数名を抽出する
        
        Returns:
            List[str]: テンプレート内の変数名リスト
        """
        variables = []
        for match in re.finditer(self._variable_pattern, self.template):
            var_name = match.group(1).strip()
            if var_name not in variables:
                variables.append(var_name)
                
        return variables
        
    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> 'PromptTemplate':
        """
        ファイルからテンプレートを読み込む
        
        Args:
            file_path: テンプレートファイルのパス
            
        Returns:
            PromptTemplate: 読み込まれたテンプレート
            
        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ValueError: 不正なフォーマットの場合
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"テンプレートファイルが見つかりません: {file_path}")
            
        # ファイル拡張子に応じた読み込み処理
        if file_path.suffix in ['.yml', '.yaml']:
            # YAMLファイルからの読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            if not isinstance(data, dict):
                raise ValueError(f"不正なYAMLフォーマット: {file_path}")
                
            template = data.get('template', '')
            metadata = {k: v for k, v in data.items() if k != 'template'}
            
        elif file_path.suffix == '.json':
            # JSONファイルからの読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            template = data.get('template', '')
            metadata = {k: v for k, v in data.items() if k != 'template'}
            
        else:
            # プレーンテキストとして読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                template = f.read()
            metadata = {'file_path': str(file_path)}
            
        return cls(template, metadata)
        
    def to_file(self, file_path: Union[str, Path], format: str = 'yaml'):
        """
        テンプレートをファイルに保存する
        
        Args:
            file_path: 保存先ファイルパス
            format: 保存形式（'yaml', 'json', 'text'）
            
        Raises:
            ValueError: 不正なフォーマット指定の場合
        """
        file_path = Path(file_path)
        
        # ディレクトリが存在しない場合は作成
        os.makedirs(file_path.parent, exist_ok=True)
        
        if format == 'yaml':
            # YAMLとして保存
            data = {'template': self.template, **self.metadata}
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
                
        elif format == 'json':
            # JSONとして保存
            data = {'template': self.template, **self.metadata}
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        elif format == 'text':
            # プレーンテキストとして保存
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.template)
                
        else:
            raise ValueError(f"不正なフォーマット指定: {format}")


def load_prompt_template(agent_type: str, template_name: str) -> PromptTemplate:
    """
    指定されたエージェントタイプとテンプレート名からプロンプトテンプレートを読み込む
    
    Args:
        agent_type: エージェントタイプ（'agent_a', 'agent_b', 'agent_c', 'agent_d', 'common'）
        template_name: テンプレート名
        
    Returns:
        PromptTemplate: 読み込まれたテンプレート
        
    Raises:
        FileNotFoundError: テンプレートが見つからない場合
        ValueError: 不正なエージェントタイプの場合
    """
    valid_agent_types = ['agent_a', 'agent_b', 'agent_c', 'agent_d', 'common']
    
    if agent_type not in valid_agent_types:
        raise ValueError(f"不正なエージェントタイプ: {agent_type}. 有効な値: {valid_agent_types}")
        
    # プロジェクトのルートからの相対パスでテンプレートディレクトリを特定
    base_dir = Path(__file__).parent
    
    # テンプレート候補となるパスのリスト
    template_paths = [
        base_dir / agent_type / f"{template_name}.yaml",
        base_dir / agent_type / f"{template_name}.yml",
        base_dir / agent_type / f"{template_name}.json",
        base_dir / agent_type / f"{template_name}.txt",
        base_dir / agent_type / template_name,  # 拡張子なしの場合
    ]
    
    # 存在するパスを探す
    for path in template_paths:
        if path.exists():
            return PromptTemplate.from_file(path)
            
    # テンプレートが見つからない場合
    raise FileNotFoundError(
        f"テンプレート '{template_name}' がエージェント '{agent_type}' のディレクトリに見つかりません。"
        f"検索パス: {[str(p) for p in template_paths]}"
    ) 