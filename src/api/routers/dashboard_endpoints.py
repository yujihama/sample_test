#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ダッシュボード関連APIエンドポイント
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel

router = APIRouter(tags=["dashboard"])

# モデル定義
class Summary(BaseModel):
    """ダッシュボード概要データモデル"""
    processingSamples: int
    processingSamplesTrend: float
    completedSamples: int
    completedSamplesTrend: float
    pendingSamples: int
    pendingSamplesTrend: float
    alertCount: int
    alertCountTrend: float

class Category(BaseModel):
    """カテゴリデータモデル"""
    name: str
    count: int

class PeriodData(BaseModel):
    """期間データモデル"""
    period: str
    completed: int
    processing: int
    pending: int
    errors: int

class SampleStatus(BaseModel):
    """サンプルステータスデータモデル"""
    id: str
    name: str
    status: str
    progress: float

class ProcessStatus(BaseModel):
    """処理状況データモデル"""
    categories: List[Category]
    periodData: List[PeriodData]
    sampleStatus: List[SampleStatus]

class Activity(BaseModel):
    """アクティビティログモデル"""
    id: str
    timestamp: datetime
    type: str
    message: str
    details: Optional[Dict[str, Any]] = None

class Alert(BaseModel):
    """アラートモデル"""
    id: str
    timestamp: datetime
    severity: str
    message: str
    resolved: bool
    details: Optional[Dict[str, Any]] = None

# モックデータの作成関数
def get_mock_summary() -> Summary:
    """モックのサマリーデータを取得"""
    return Summary(
        processingSamples=5,
        processingSamplesTrend=10.5,
        completedSamples=42,
        completedSamplesTrend=15.2,
        pendingSamples=8,
        pendingSamplesTrend=-5.3,
        alertCount=3,
        alertCountTrend=0.0
    )

def get_mock_process_status() -> ProcessStatus:
    """モックの処理状況データを取得"""
    # カテゴリデータ
    categories = [
        Category(name="財務", count=12),
        Category(name="業務", count=8),
        Category(name="IT", count=15),
        Category(name="リスク", count=5)
    ]
    
    # 期間データ
    now = datetime.now()
    period_data = []
    for i in range(6):
        date = now - timedelta(days=i*7)
        period_str = date.strftime("%m/%d")
        period_data.append(
            PeriodData(
                period=period_str,
                completed=25 - i*3,
                processing=5 - (i % 3),
                pending=8 - (i % 4),
                errors=i % 3
            )
        )
    period_data.reverse()  # 古いものから新しいものへ
    
    # サンプルステータス
    sample_status = [
        SampleStatus(id="sample-001", name="財務データ検証", status="completed", progress=100.0),
        SampleStatus(id="sample-002", name="リスク評価レポート", status="processing", progress=65.0),
        SampleStatus(id="sample-003", name="内部統制検証", status="pending", progress=0.0)
    ]
    
    return ProcessStatus(
        categories=categories,
        periodData=period_data,
        sampleStatus=sample_status
    )

def get_mock_activities(limit: int = 10) -> List[Activity]:
    """モックのアクティビティログを取得"""
    now = datetime.now()
    activities = [
        Activity(
            id=f"activity-{i}",
            timestamp=now - timedelta(hours=i*2),
            type="success" if i % 3 == 0 else ("warning" if i % 3 == 1 else "error"),
            message=f"サンプル処理{'完了' if i % 3 == 0 else ('警告発生' if i % 3 == 1 else 'エラー発生')}",
            details={"sample_id": f"sample-{i%3+1}", "agent": f"agent_{chr(97+i%5)}"}
        )
        for i in range(limit)
    ]
    return activities

def get_mock_alerts(limit: int = 5) -> List[Alert]:
    """モックのアラートを取得"""
    now = datetime.now()
    alerts = [
        Alert(
            id=f"alert-{i}",
            timestamp=now - timedelta(hours=i*3),
            severity="high" if i % 3 == 0 else ("medium" if i % 3 == 1 else "low"),
            message=f"アラート: {'重大な問題が発生' if i % 3 == 0 else ('要注意事項あり' if i % 3 == 1 else '軽微な警告')}",
            resolved=i % 2 == 0,
            details={"sample_id": f"sample-{i%3+1}", "agent": f"agent_{chr(97+i%5)}"}
        )
        for i in range(limit)
    ]
    return alerts

# エンドポイント定義

@router.get("/dashboard/summary", response_model=Dict[str, Summary])
async def get_dashboard_summary():
    """ダッシュボードの概要データを取得"""
    summary = get_mock_summary()
    return {"summary": summary}

@router.get("/dashboard/process-status", response_model=Dict[str, ProcessStatus])
async def get_process_status():
    """処理状況データを取得"""
    process_status = get_mock_process_status()
    return {"process-status": process_status}

@router.get("/dashboard/activity", response_model=Dict[str, List[Activity]])
async def get_activity_log(limit: int = Query(10, ge=1, le=100)):
    """アクティビティログを取得"""
    activities = get_mock_activities(limit)
    return {"activities": activities}

@router.get("/dashboard/alerts", response_model=Dict[str, List[Alert]])
async def get_alerts(limit: int = Query(5, ge=1, le=50)):
    """アラートを取得"""
    alerts = get_mock_alerts(limit)
    return {"alerts": alerts} 