"""
画像処理ツール - 領収書などの画像ファイルの処理を行う
"""

import os
from typing import Dict, List, Any, Optional
import uuid
from datetime import datetime
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import base64
from io import BytesIO

from loguru import logger
from src.core.tool_base import ToolBase, ToolResult
from src.core.config import settings


class ImageProcessor(ToolBase):
    """画像処理ツール"""
    
    def __init__(self, tool_id: str = None):
        """
        画像処理ツールの初期化
        
        Args:
            tool_id: ツールID（省略時は自動生成）
        """
        super().__init__(tool_id)
        self.description = "画像処理ツール - 画像の拡大・鮮明化・解析などを行う"
        self.version = "1.0.0"
        self.capabilities = [
            "partial_enlarge",  # 部分拡大
            "enhance_clarity",  # 鮮明化
            "extract_text",     # テキスト抽出
            "compare_images",   # 画像比較
            "detect_stamp"      # 印影検出
        ]
        
        # 一時ファイル保存先
        self.temp_dir = os.path.join(settings.UPLOAD_DIR, "processed_images")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        logger.info(f"画像処理ツール初期化完了: {self.tool_id}")
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        パラメータのバリデーション
        
        Args:
            params: 検証するパラメータ
            
        Returns:
            bool: 検証結果
        """
        # 基本的なバリデーション
        if "operation" not in params:
            logger.error("operation パラメータが必要です")
            return False
            
        operation = params["operation"]
        
        # 操作タイプ別のバリデーション
        if operation not in self.capabilities:
            logger.error(f"サポートされていない操作です: {operation}")
            return False
            
        # 画像ファイルパスの確認
        if "image_path" not in params and "image_data" not in params:
            logger.error("image_path または image_data が必要です")
            return False
            
        # 操作別の必須パラメータ確認
        if operation == "partial_enlarge":
            required = ["x1", "y1", "x2", "y2", "scale"]
            if not all(k in params for k in required):
                logger.error(f"操作 {operation} には次のパラメータが必要です: {required}")
                return False
        
        return True
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        ツール実行のメイン処理
        
        Args:
            params: 実行パラメータ
            
        Returns:
            ToolResult: 実行結果
        """
        try:
            operation = params["operation"]
            
            # 画像の読み込み
            image = self._load_image(params)
            if image is None:
                return ToolResult(
                    tool_id=self.tool_id,
                    status="error",
                    data={},
                    error_message="画像の読み込みに失敗しました"
                )
            
            # 操作の実行
            result_data = {}
            
            if operation == "partial_enlarge":
                result_image, result_data = self._process_partial_enlarge(image, params)
            elif operation == "enhance_clarity":
                result_image, result_data = self._process_enhance_clarity(image, params)
            elif operation == "detect_stamp":
                result_image, result_data = self._process_detect_stamp(image, params)
            else:
                # 未実装の機能
                return ToolResult(
                    tool_id=self.tool_id,
                    status="error",
                    data={},
                    error_message=f"操作 {operation} は未実装です"
                )
            
            # 結果画像の保存
            if result_image:
                output_path = self._save_result_image(result_image, params)
                result_data["output_path"] = output_path
                
                # Base64形式の画像データを追加（小さい画像のみ）
                if params.get("include_base64", False) and os.path.getsize(output_path) < 1024 * 1024:  # 1MB以下の場合
                    result_data["image_base64"] = self._image_to_base64(result_image)
            
            return ToolResult(
                tool_id=self.tool_id,
                status="success",
                data=result_data
            )
            
        except Exception as e:
            return await self.handle_error(e, params)
    
    def _load_image(self, params: Dict[str, Any]) -> Optional[Image.Image]:
        """
        画像の読み込み
        
        Args:
            params: パラメータ辞書
            
        Returns:
            Image.Image: 読み込まれた画像
        """
        try:
            if "image_path" in params:
                # ファイルパスからの読み込み
                image_path = params["image_path"]
                if not os.path.exists(image_path):
                    # アップロードディレクトリ内で探す
                    image_path = os.path.join(settings.UPLOAD_DIR, os.path.basename(image_path))
                
                if os.path.exists(image_path):
                    return Image.open(image_path)
                else:
                    logger.error(f"画像ファイルが見つかりません: {image_path}")
                    return None
                    
            elif "image_data" in params:
                # Base64データからの読み込み
                image_data = params["image_data"]
                image_bytes = base64.b64decode(image_data)
                return Image.open(BytesIO(image_bytes))
                
        except Exception as e:
            logger.error(f"画像読み込みエラー: {e}")
            return None
    
    def _process_partial_enlarge(self, image: Image.Image, params: Dict[str, Any]) -> tuple:
        """
        部分拡大処理
        
        Args:
            image: 元画像
            params: パラメータ辞書
            
        Returns:
            tuple: (処理後画像, 結果データ)
        """
        # パラメータの取得
        x1 = int(params["x1"])
        y1 = int(params["y1"])
        x2 = int(params["x2"])
        y2 = int(params["y2"])
        scale = float(params["scale"])
        
        # 部分領域の切り出し
        crop_region = image.crop((x1, y1, x2, y2))
        
        # 拡大
        new_size = (int((x2 - x1) * scale), int((y2 - y1) * scale))
        enlarged = crop_region.resize(new_size, Image.LANCZOS)
        
        # 結果データの作成
        result_data = {
            "original_size": image.size,
            "crop_region": (x1, y1, x2, y2),
            "enlarged_size": new_size,
            "scale": scale
        }
        
        return enlarged, result_data
    
    def _process_enhance_clarity(self, image: Image.Image, params: Dict[str, Any]) -> tuple:
        """
        鮮明化処理
        
        Args:
            image: 元画像
            params: パラメータ辞書
            
        Returns:
            tuple: (処理後画像, 結果データ)
        """
        # パラメータの取得（デフォルト値あり）
        sharpness_factor = float(params.get("sharpness", 2.0))
        contrast_factor = float(params.get("contrast", 1.5))
        
        # 鮮明化処理
        enhanced = image
        
        # シャープネス調整
        sharpness_enhancer = ImageEnhance.Sharpness(enhanced)
        enhanced = sharpness_enhancer.enhance(sharpness_factor)
        
        # コントラスト調整
        contrast_enhancer = ImageEnhance.Contrast(enhanced)
        enhanced = contrast_enhancer.enhance(contrast_factor)
        
        # 結果データの作成
        result_data = {
            "original_size": image.size,
            "sharpness_factor": sharpness_factor,
            "contrast_factor": contrast_factor
        }
        
        return enhanced, result_data
    
    def _process_detect_stamp(self, image: Image.Image, params: Dict[str, Any]) -> tuple:
        """
        印影検出処理（シンプルな実装例）
        
        Args:
            image: 元画像
            params: パラメータ辞書
            
        Returns:
            tuple: (検出結果の可視化画像, 結果データ)
        """
        # グレースケールに変換
        gray_image = image.convert("L")
        
        # コントラスト強調
        enhancer = ImageEnhance.Contrast(gray_image)
        enhanced = enhancer.enhance(2.0)
        
        # 輪郭検出（シンプルなエッジ検出フィルタ）
        edges = enhanced.filter(ImageFilter.FIND_EDGES)
        
        # しきい値処理（印影検出の実装例として）
        threshold = params.get("threshold", 128)
        binary = edges.point(lambda x: 255 if x > threshold else 0)
        
        # 結果データの作成
        result_data = {
            "stamp_detected": True,  # 実際には検出ロジックに基づいて判断
            "confidence": 0.85,       # 検出信頼度の例
            "threshold": threshold
        }
        
        # 元画像に検出結果を重ねて可視化（実際のプロジェクトでは適切な可視化方法を選択）
        result_image = image.copy()
        # この部分は実際のプロジェクトで検出結果を可視化する適切な方法を実装
        
        return binary, result_data  # 簡易デモとして二値化画像を返す
    
    def _save_result_image(self, image: Image.Image, params: Dict[str, Any]) -> str:
        """
        結果画像の保存
        
        Args:
            image: 保存する画像
            params: パラメータ辞書
            
        Returns:
            str: 保存先パス
        """
        # ファイル名の生成
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_filename = f"{params['operation']}_{timestamp}_{uuid.uuid4().hex[:6]}.png"
        
        # 保存先パスの生成
        output_path = os.path.join(self.temp_dir, output_filename)
        
        # 保存
        image.save(output_path)
        logger.info(f"処理結果を保存しました: {output_path}")
        
        return output_path
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """
        画像をBase64形式に変換
        
        Args:
            image: 変換する画像
            
        Returns:
            str: Base64エンコードされた画像データ
        """
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode('utf-8') 