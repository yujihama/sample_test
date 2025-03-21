import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  CardHeader,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Badge,
  LinearProgress,
  Button,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import WarningIcon from '@mui/icons-material/Warning';
import { Refresh as RefreshIcon } from '@mui/icons-material';

// APIサービスとカスタムフックをインポート
import { dashboardApi } from '../../frontend/services/api';
import useApi from '../../frontend/hooks/useApi';

// 円グラフの色
const COLORS = ['#4caf50', '#3f51b5', '#ff9800', '#f44336'];

const MainDashboard = () => {
  // APIからダッシュボード概要データを取得
  const { 
    data: summaryData, 
    loading: summaryLoading, 
    error: summaryError,
    refetch: refetchSummary
  } = useApi(() => dashboardApi.getSummary(), {
    dependencies: [],
    cacheResults: true,
    cacheTime: 5 * 60 * 1000, // 5分間キャッシュ
    retryCount: 1
  });

  // APIから処理状況データを取得
  const { 
    data: processStatusData, 
    loading: processStatusLoading, 
    error: processStatusError,
    refetch: refetchProcessStatus
  } = useApi(() => dashboardApi.getProcessStatus(), {
    dependencies: [],
    cacheResults: true,
    cacheTime: 5 * 60 * 1000, // 5分間キャッシュ
    retryCount: 1
  });

  // APIからアクティビティログを取得
  const { 
    data: activityLogData, 
    loading: activityLogLoading, 
    error: activityLogError,
    refetch: refetchActivityLog
  } = useApi(() => dashboardApi.getActivityLog({ limit: 10 }), {
    dependencies: [],
    cacheResults: true,
    cacheTime: 2 * 60 * 1000, // 2分間キャッシュ
    retryCount: 1
  });

  // APIからアラートデータを取得
  const { 
    data: alertsData, 
    loading: alertsLoading, 
    error: alertsError,
    refetch: refetchAlerts
  } = useApi(() => dashboardApi.getAlerts({ limit: 5 }), {
    dependencies: [],
    cacheResults: true,
    cacheTime: 2 * 60 * 1000, // 2分間キャッシュ
    retryCount: 1
  });

  // 全データを再取得する関数
  const refreshAllData = () => {
    refetchSummary(true); // キャッシュを無視して強制リフレッシュ
    refetchProcessStatus(true);
    refetchActivityLog(true);
    refetchAlerts(true);
  };

  // カテゴリ別サンプル数のデータ変換（円グラフ用）
  const getCategoryData = () => {
    if (!processStatusData?.success || !processStatusData?.data?.['process-status']?.categories) {
      return [];
    }
    return processStatusData.data['process-status'].categories;
  };

  // 期間別処理数のデータ変換（棒グラフ用）
  const getPeriodData = () => {
    if (!processStatusData?.success || !processStatusData?.data?.['process-status']?.periodData) {
      return [];
    }
    return processStatusData.data['process-status'].periodData;
  };

  // アクティビティログデータの取得
  const getActivityLogData = () => {
    if (!activityLogData?.success || !activityLogData?.data?.activities) {
      return [];
    }
    return activityLogData.data.activities;
  };

  // アラートデータの取得
  const getAlertsData = () => {
    if (!alertsData?.success || !alertsData?.data?.alerts) {
      return [];
    }
    return alertsData.data.alerts;
  };

  // 概要データの取得
  const getSummaryData = () => {
    if (!summaryData?.success || !summaryData?.data?.summary) {
      return {
        processingSamples: 0,
        processingSamplesTrend: 0,
        completedSamples: 0,
        completedSamplesTrend: 0,
        pendingSamples: 0,
        pendingSamplesTrend: 0,
        alertCount: 0,
        alertCountTrend: 0
      };
    }
    return summaryData.data.summary;
  };

  // 画面に表示する概要データ
  const summary = getSummaryData();

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" gutterBottom sx={{ flexGrow: 1 }}>
          統合監視ダッシュボード
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={refreshAllData}
          sx={{ ml: 2 }}
          disabled={summaryLoading || processStatusLoading || activityLogLoading || alertsLoading}
        >
          更新
        </Button>
      </Box>
      
      {/* KPI概要 */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {summaryLoading ? (
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          </Grid>
        ) : summaryError ? (
          <Grid item xs={12}>
            <Alert severity="error">
              データの読み込みに失敗しました: {summaryError}
            </Alert>
          </Grid>
        ) : (
          <>
            <Grid item xs={12} sm={6} md={3}>
              <Paper 
                elevation={2} 
                sx={{ 
                  p: 2, 
                  display: 'flex', 
                  flexDirection: 'column', 
                  height: 140,
                  borderLeft: '4px solid #4caf50'
                }}
              >
                <Typography variant="subtitle2" color="textSecondary">
                  処理中サンプル
                </Typography>
                <Typography 
                  variant="h4" 
                  component="div" 
                  sx={{ fontWeight: 'bold', my: 1 }}
                >
                  {summary.processingSamples}
                </Typography>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    color: summary.processingSamplesTrend >= 0 ? 'green' : 'red',
                    mt: 'auto'
                  }}
                >
                  {summary.processingSamplesTrend > 0 ? '+' : ''}{summary.processingSamplesTrend}% 前回比
                </Typography>
              </Paper>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Paper 
                elevation={2} 
                sx={{ 
                  p: 2, 
                  display: 'flex', 
                  flexDirection: 'column', 
                  height: 140,
                  borderLeft: '4px solid #3f51b5'
                }}
              >
                <Typography variant="subtitle2" color="textSecondary">
                  完了サンプル
                </Typography>
                <Typography 
                  variant="h4" 
                  component="div" 
                  sx={{ fontWeight: 'bold', my: 1 }}
                >
                  {summary.completedSamples}
                </Typography>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    color: summary.completedSamplesTrend >= 0 ? 'green' : 'red',
                    mt: 'auto'
                  }}
                >
                  {summary.completedSamplesTrend > 0 ? '+' : ''}{summary.completedSamplesTrend}% 前回比
                </Typography>
              </Paper>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Paper 
                elevation={2} 
                sx={{ 
                  p: 2, 
                  display: 'flex', 
                  flexDirection: 'column', 
                  height: 140,
                  borderLeft: '4px solid #ff9800'
                }}
              >
                <Typography variant="subtitle2" color="textSecondary">
                  保留中サンプル
                </Typography>
                <Typography 
                  variant="h4" 
                  component="div" 
                  sx={{ fontWeight: 'bold', my: 1 }}
                >
                  {summary.pendingSamples}
                </Typography>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    color: summary.pendingSamplesTrend <= 0 ? 'green' : 'red',
                    mt: 'auto'
                  }}
                >
                  {summary.pendingSamplesTrend > 0 ? '+' : ''}{summary.pendingSamplesTrend}% 前回比
                </Typography>
              </Paper>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Paper 
                elevation={2} 
                sx={{ 
                  p: 2, 
                  display: 'flex', 
                  flexDirection: 'column', 
                  height: 140,
                  borderLeft: '4px solid #f44336'
                }}
              >
                <Typography variant="subtitle2" color="textSecondary">
                  アラート
                </Typography>
                <Typography 
                  variant="h4" 
                  component="div" 
                  sx={{ fontWeight: 'bold', my: 1 }}
                >
                  {summary.alertCount}
                </Typography>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    color: summary.alertCountTrend <= 0 ? 'green' : 'red',
                    mt: 'auto'
                  }}
                >
                  {summary.alertCountTrend > 0 ? '+' : ''}{summary.alertCountTrend}% 前回比
                </Typography>
              </Paper>
            </Grid>
          </>
        )}
      </Grid>
      
      {/* メインコンテンツ */}
      <Grid container spacing={3}>
        {/* 処理状況グラフ */}
        <Grid item xs={12} md={8}>
          <Paper elevation={2} sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              処理状況
            </Typography>
            
            {processStatusLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
              </Box>
            ) : processStatusError ? (
              <Alert severity="error">
                データの読み込みに失敗しました: {processStatusError}
              </Alert>
            ) : (
              <>
                <Box sx={{ height: 300, mt: 2 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={getPeriodData()}
                      margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="period" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="completed" name="完了" fill="#4caf50" />
                      <Bar dataKey="processing" name="処理中" fill="#3f51b5" />
                      <Bar dataKey="pending" name="保留中" fill="#ff9800" />
                      <Bar dataKey="errors" name="エラー" fill="#f44336" />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
                
                <Divider sx={{ my: 2 }} />
                
                <Box sx={{ height: 200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={getCategoryData()}
                        dataKey="count"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={(entry) => entry.name}
                      >
                        {getCategoryData().map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              </>
            )}
          </Paper>
        </Grid>
        
        {/* アクティビティとアラート */}
        <Grid item xs={12} md={4}>
          <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              アクティビティログ
            </Typography>
            
            {activityLogLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
              </Box>
            ) : activityLogError ? (
              <Alert severity="error">
                データの読み込みに失敗しました: {activityLogError}
              </Alert>
            ) : (
              <List dense sx={{ maxHeight: 200, overflow: 'auto' }}>
                {getActivityLogData().length > 0 ? (
                  getActivityLogData().map((activity, index) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        {activity.type === 'success' ? (
                          <CheckCircleOutlineIcon color="success" />
                        ) : activity.type === 'warning' ? (
                          <WarningIcon color="warning" />
                        ) : (
                          <ErrorOutlineIcon color="error" />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={activity.message}
                        secondary={activity.timestamp ? new Date(activity.timestamp).toLocaleString() : ''}
                      />
                    </ListItem>
                  ))
                ) : (
                  <ListItem>
                    <ListItemText primary="アクティビティが記録されていません" />
                  </ListItem>
                )}
              </List>
            )}
          </Paper>
          
          <Paper elevation={2} sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              <Badge 
                badgeContent={getAlertsData().length} 
                color="error"
                sx={{ '& .MuiBadge-badge': { right: -20 } }}
              >
                アラート
              </Badge>
            </Typography>
            
            {alertsLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
              </Box>
            ) : alertsError ? (
              <Alert severity="error">
                データの読み込みに失敗しました: {alertsError}
              </Alert>
            ) : (
              <List dense sx={{ maxHeight: 200, overflow: 'auto' }}>
                {getAlertsData().length > 0 ? (
                  getAlertsData().map((alert, index) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        {alert.severity === 'high' ? (
                          <ErrorOutlineIcon color="error" />
                        ) : alert.severity === 'medium' ? (
                          <WarningIcon color="warning" />
                        ) : (
                          <WarningIcon color="info" />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={alert.message}
                        secondary={alert.timestamp ? new Date(alert.timestamp).toLocaleString() : ''}
                      />
                    </ListItem>
                  ))
                ) : (
                  <ListItem>
                    <ListItemText primary="アラートはありません" />
                  </ListItem>
                )}
              </List>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default MainDashboard; 