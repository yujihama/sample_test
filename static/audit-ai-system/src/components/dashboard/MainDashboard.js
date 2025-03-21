import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Chip,
  Avatar,
  CircularProgress,
  Alert,
  LinearProgress,
  IconButton,
  Button
} from '@mui/material';
import {
  AssignmentTurnedIn as AssignmentTurnedInIcon,
  Assignment as AssignmentIcon,
  AssignmentLate as AssignmentLateIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
  ArrowUpward as ArrowUpwardIcon,
  ArrowDownward as ArrowDownwardIcon
} from '@mui/icons-material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { dashboardApi } from '../../services/api';
import useApi from '../../hooks/useApi';

// 円グラフの色
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

const MainDashboard = () => {
  // APIからダッシュボード概要データを取得
  const { 
    data: summaryData, 
    loading: summaryLoading, 
    error: summaryError,
    refetch: refetchSummary
  } = useApi(dashboardApi.getSummary, [], {
    onSuccess: (data) => {
      console.log('取得したサマリーデータ詳細:', JSON.stringify(data));
    },
    onError: (error) => {
      console.error('サマリーデータ取得エラー詳細:', error);
    }
  });

  // APIから処理状況データを取得
  const {
    data: processStatusData,
    loading: processStatusLoading,
    error: processStatusError,
    refetch: refetchProcessStatus,
  } = useApi(dashboardApi.getProcessStatus, []);

  // APIからアクティビティログを取得
  const {
    data: activityLogData,
    loading: activityLogLoading,
    error: activityLogError,
    refetch: refetchActivityLog,
  } = { data: null, loading: false, error: null, refetch: () => {} };
  
  // APIからアラートデータを取得
  const {
    data: alertsData,
    loading: alertsLoading,
    error: alertsError,
    refetch: refetchAlerts,
  } = { data: null, loading: false, error: null, refetch: () => {} };

  // 全データを再取得する関数
  const refreshAllData = () => {
    refetchSummary();
    refetchProcessStatus();
    // 非活性化したアクティビティログとアラートデータの再取得は行わない
    // refetchActivityLog();
    // refetchAlerts();
  };

  // サマリーデータの取得
  const getSummaryData = () => {
    console.log('summaryData:', summaryData);
    if (!summaryData) {
      console.log('サマリーデータ取得失敗', {summaryData});
      return null;
    }
    
    // 直接summaryが存在する場合（修正後のAPIレスポンス）
    if (summaryData.summary) {
      return summaryData.summary;
    }
    
    // summaryがresponse.dataに直接ある場合（json-serverの直接レスポンス）
    if (summaryData) {
      return summaryData;
    }
    
    console.log('dashboard.summaryが見つかりません', {summaryData});
    return null;
  };

  // カテゴリ別サンプル数のデータ変換（円グラフ用）
  const getCategoryData = () => {
    console.log('processStatusData:', processStatusData);
    if (!processStatusData) return [];
    
    // 修正後のAPIレスポンス
    if (processStatusData["process-status"] && processStatusData["process-status"].categories) {
      return processStatusData["process-status"].categories;
    }
    
    // json-serverの直接レスポンス形式
    if (processStatusData.categories) {
      return processStatusData.categories;
    }
    
    return [];
  };

  // 期間別処理数のデータ変換（棒グラフ用）
  const getPeriodData = () => {
    if (!processStatusData) return [];
    
    // 修正後のAPIレスポンス
    if (processStatusData["process-status"] && processStatusData["process-status"].periodData) {
      return processStatusData["process-status"].periodData;
    }
    
    // json-serverの直接レスポンス形式
    if (processStatusData.periodData) {
      return processStatusData.periodData;
    }
    
    return [];
  };

  // サンプルステータスの処理
  const getSampleStatusData = () => {
    if (!processStatusData) return [];
    
    // 修正後のAPIレスポンス
    if (processStatusData["process-status"] && processStatusData["process-status"].sampleStatus) {
      return processStatusData["process-status"].sampleStatus;
    }
    
    // json-serverの直接レスポンス形式
    if (processStatusData.sampleStatus) {
      return processStatusData.sampleStatus;
    }
    
    return [];
  };

  // アクティビティログデータの取得関数も使用しないため削除
  
  // アラートデータの取得関数も使用しないため削除

  // ステータス別の色を返す関数
  const getStatusColor = (status) => {
    switch(status) {
      case 'completed': return '#4caf50';
      case 'processing': return '#2196f3';
      case 'pending': return '#ff9800';
      default: return '#757575';
    }
  };

  // トレンド矢印を取得
  const getTrendArrow = (trend) => {
    if (trend > 0) {
      return <ArrowUpwardIcon fontSize="small" sx={{ color: trend > 0 ? 'success.main' : 'error.main' }} />;
    } else if (trend < 0) {
      return <ArrowDownwardIcon fontSize="small" sx={{ color: trend < 0 ? 'error.main' : 'success.main' }} />;
    }
    return null;
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          監査ダッシュボード
        </Typography>
        <Button 
          variant="outlined" 
          startIcon={<RefreshIcon />}
          onClick={refreshAllData}
        >
          更新
        </Button>
      </Box>

      {/* サマリーカード */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          {summaryLoading ? (
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 5 }}>
                <CircularProgress size={30} />
              </CardContent>
            </Card>
          ) : summaryError ? (
            <Card>
              <CardContent>
                <Alert severity="error">データを読み込めませんでした</Alert>
              </CardContent>
            </Card>
          ) : summaryData && summaryData.summary ? (
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <AssignmentIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6" component="div">
                    処理中サンプル
                  </Typography>
                </Box>
                <Typography variant="h4" component="div" sx={{ mb: 1 }}>
                  {getSummaryData().processingSamples}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {getTrendArrow(getSummaryData().processingSamplesTrend)}
                  <Typography variant="body2" color="text.secondary">
                    前週比 {getSummaryData().processingSamplesTrend > 0 ? '+' : ''}{getSummaryData().processingSamplesTrend}%
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          ) : null}
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          {summaryLoading ? (
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 5 }}>
                <CircularProgress size={30} />
              </CardContent>
            </Card>
          ) : summaryError ? (
            <Card>
              <CardContent>
                <Alert severity="error">データを読み込めませんでした</Alert>
              </CardContent>
            </Card>
          ) : summaryData && summaryData.summary ? (
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <AssignmentTurnedInIcon color="success" sx={{ mr: 1 }} />
                  <Typography variant="h6" component="div">
                    完了サンプル
                  </Typography>
                </Box>
                <Typography variant="h4" component="div" sx={{ mb: 1 }}>
                  {getSummaryData().completedSamples}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {getTrendArrow(getSummaryData().completedSamplesTrend)}
                  <Typography variant="body2" color="text.secondary">
                    前週比 {getSummaryData().completedSamplesTrend > 0 ? '+' : ''}{getSummaryData().completedSamplesTrend}%
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          ) : null}
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          {summaryLoading ? (
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 5 }}>
                <CircularProgress size={30} />
              </CardContent>
            </Card>
          ) : summaryError ? (
            <Card>
              <CardContent>
                <Alert severity="error">データを読み込めませんでした</Alert>
              </CardContent>
            </Card>
          ) : summaryData && summaryData.summary ? (
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <AssignmentLateIcon color="warning" sx={{ mr: 1 }} />
                  <Typography variant="h6" component="div">
                    保留中サンプル
                  </Typography>
                </Box>
                <Typography variant="h4" component="div" sx={{ mb: 1 }}>
                  {getSummaryData().pendingSamples}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {getTrendArrow(getSummaryData().pendingSamplesTrend)}
                  <Typography variant="body2" color="text.secondary">
                    前週比 {getSummaryData().pendingSamplesTrend > 0 ? '+' : ''}{getSummaryData().pendingSamplesTrend}%
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          ) : null}
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          {summaryLoading ? (
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 5 }}>
                <CircularProgress size={30} />
              </CardContent>
            </Card>
          ) : summaryError ? (
            <Card>
              <CardContent>
                <Alert severity="error">データを読み込めませんでした</Alert>
              </CardContent>
            </Card>
          ) : summaryData && summaryData.summary ? (
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <WarningIcon color="error" sx={{ mr: 1 }} />
                  <Typography variant="h6" component="div">
                    アラート
                  </Typography>
                </Box>
                <Typography variant="h4" component="div" sx={{ mb: 1 }}>
                  {getSummaryData().alertCount}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {getTrendArrow(getSummaryData().alertCountTrend)}
                  <Typography variant="body2" color="text.secondary">
                    前週比 {getSummaryData().alertCountTrend > 0 ? '+' : ''}{getSummaryData().alertCountTrend}件
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          ) : null}
        </Grid>
      </Grid>

      {/* チャートと活動ログ */}
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              処理状況分析
            </Typography>
            
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  カテゴリ別サンプル数
                </Typography>
                {processStatusLoading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                    <CircularProgress />
                  </Box>
                ) : processStatusError ? (
                  <Alert severity="error">データを読み込めませんでした</Alert>
                ) : processStatusData && processStatusData["process-status"] && processStatusData["process-status"].categories ? (
                  <Box height={240}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={getCategoryData()}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                          outerRadius={80}
                          fill="#8884d8"
                          dataKey="count"
                          nameKey="name"
                        >
                          {getCategoryData().map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </Box>
                ) : (
                  <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', p: 4 }}>
                    データが利用できません
                  </Typography>
                )}
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  期間別処理数
                </Typography>
                {processStatusLoading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                    <CircularProgress />
                  </Box>
                ) : processStatusError ? (
                  <Alert severity="error">データを読み込めませんでした</Alert>
                ) : processStatusData && processStatusData["process-status"] && processStatusData["process-status"].periodData ? (
                  <Box height={240}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={getPeriodData()}
                        margin={{
                          top: 5,
                          right: 30,
                          left: 20,
                          bottom: 5,
                        }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="period" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="processed" name="処理数" fill="#8884d8" />
                        <Bar dataKey="anomalies" name="異常検出" fill="#f44336" />
                      </BarChart>
                    </ResponsiveContainer>
                  </Box>
                ) : (
                  <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', p: 4 }}>
                    データが利用できません
                  </Typography>
                )}
              </Grid>
            </Grid>
            
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                進行中のサンプル
              </Typography>
              {processStatusLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                  <CircularProgress size={24} />
                </Box>
              ) : processStatusError ? (
                <Alert severity="error" sx={{ mt: 1 }}>データを読み込めませんでした</Alert>
              ) : processStatusData && processStatusData["process-status"] && processStatusData["process-status"].sampleStatus ? (
                <Grid container spacing={2}>
                  {getSampleStatusData().map((sample) => (
                    <Grid item xs={12} sm={6} key={sample.id}>
                      <Card variant="outlined">
                        <CardContent sx={{ pb: 1 }}>
                          <Typography variant="subtitle2" noWrap>{sample.name}</Typography>
                          <Typography variant="caption" color="text.secondary" display="block">
                            最終更新: {sample.lastUpdated}
                          </Typography>
                          <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                            <Box sx={{ flex: 1, mr: 1 }}>
                              <LinearProgress 
                                variant="determinate" 
                                value={sample.progress} 
                                sx={{ 
                                  height: 8, 
                                  borderRadius: 1,
                                  bgcolor: 'rgba(0, 0, 0, 0.08)'
                                }} 
                              />
                            </Box>
                            <Typography variant="body2" color="text.secondary">
                              {sample.progress}%
                            </Typography>
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
                  表示するサンプルがありません
                </Typography>
              )}
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default MainDashboard; 