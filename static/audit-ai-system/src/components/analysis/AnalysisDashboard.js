import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  PictureAsPdf as PdfIcon,
  InsertDriveFile as ExcelIcon,
  Slideshow as PptIcon,
  FilterList as FilterListIcon,
  PieChart as PieChartIcon,
  BarChart as BarChartIcon,
  BubbleChart as BubbleChartIcon,
  Timeline as TimelineIcon
} from '@mui/icons-material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart as RechartsePieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  ZAxis
} from 'recharts';
import { analysisApi } from '../../services/api';
import useApi from '../../hooks/useApi';

// チャート用の色
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

const AnalysisDashboard = () => {
  const [period, setPeriod] = useState('all');
  const [category, setCategory] = useState('all');

  // 異常検出データを取得
  const { 
    data: anomalyData, 
    loading: anomalyLoading, 
    error: anomalyError,
    refetch: refetchAnomalies 
  } = useApi(analysisApi.getAnomalyData, []);

  // カテゴリデータを取得
  const { 
    data: categoryData, 
    loading: categoryLoading, 
    error: categoryError,
    refetch: refetchCategories 
  } = useApi(analysisApi.getCategoryData, []);

  // トレンドデータを取得
  const { 
    data: trendData, 
    loading: trendLoading, 
    error: trendError,
    refetch: refetchTrends 
  } = useApi(analysisApi.getTrendData, []);

  // リスク相関データを取得
  const { 
    data: riskCorrelationData, 
    loading: riskCorrelationLoading, 
    error: riskCorrelationError,
    refetch: refetchRiskCorrelation 
  } = useApi(analysisApi.getRiskCorrelation, []);

  // AIインサイトを取得
  const { 
    data: insightData, 
    loading: insightLoading, 
    error: insightError,
    refetch: refetchInsights 
  } = useApi(analysisApi.getInsights, []);

  // レポート一覧を取得
  const { 
    data: reportData, 
    loading: reportLoading, 
    error: reportError,
    refetch: refetchReports 
  } = useApi(analysisApi.getReports, []);

  // すべてのデータを再取得
  const refreshAllData = () => {
    refetchAnomalies();
    refetchCategories();
    refetchTrends();
    refetchRiskCorrelation();
    refetchInsights();
    refetchReports();
  };

  // 期間選択ハンドラ
  const handlePeriodChange = (event) => {
    setPeriod(event.target.value);
  };

  // カテゴリ選択ハンドラ
  const handleCategoryChange = (event) => {
    setCategory(event.target.value);
  };

  // トレンド状態に応じたアイコンを返す
  const getTrendIcon = (trend) => {
    switch(trend) {
      case 'up': return <TrendingUpIcon color="error" />;
      case 'down': return <TrendingDownIcon color="success" />;
      default: return null;
    }
  };

  // 深刻度に応じた色を返す
  const getSeverityColor = (severity) => {
    switch(severity) {
      case 'high': return '#f44336';
      case 'medium': return '#ff9800';
      case 'low': return '#4caf50';
      default: return '#757575';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        分析ダッシュボード
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" paragraph>
        過去の監査結果を分析し、リスク傾向や異常パターンを可視化します。
      </Typography>

      <Grid container spacing={3}>
        {/* フィルター */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2, display: 'flex', alignItems: 'center' }}>
            <Grid container spacing={2} alignItems="center">
              <Grid item>
                <FilterListIcon color="primary" />
              </Grid>
              <Grid item xs={12} sm={3}>
                <FormControl fullWidth size="small">
                  <InputLabel>期間</InputLabel>
                  <Select
                    value={period}
                    label="期間"
                    onChange={handlePeriodChange}
                  >
                    <MenuItem value="all">すべての期間</MenuItem>
                    <MenuItem value="1m">直近1ヶ月</MenuItem>
                    <MenuItem value="3m">直近3ヶ月</MenuItem>
                    <MenuItem value="6m">直近6ヶ月</MenuItem>
                    <MenuItem value="1y">直近1年</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={3}>
                <FormControl fullWidth size="small">
                  <InputLabel>カテゴリ</InputLabel>
                  <Select
                    value={category}
                    label="カテゴリ"
                    onChange={handleCategoryChange}
                  >
                    <MenuItem value="all">すべてのカテゴリ</MenuItem>
                    {categoryData && categoryData.categories && categoryData.categories.map((cat, index) => (
                      <MenuItem key={index} value={cat.name}>{cat.name}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm="auto" sx={{ ml: 'auto' }}>
                <Button 
                  variant="outlined" 
                  onClick={refreshAllData}
                >
                  更新
                </Button>
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* 異常検出 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <WarningIcon color="error" sx={{ mr: 1 }} />
              <Typography variant="h6">
                異常検出パターン
              </Typography>
            </Box>
            {anomalyLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : anomalyError ? (
              <Alert severity="error">
                異常検出データの読み込み中にエラーが発生しました。
              </Alert>
            ) : anomalyData && anomalyData.anomalies ? (
              <Box>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>パターン</TableCell>
                        <TableCell align="right">件数</TableCell>
                        <TableCell align="right">割合</TableCell>
                        <TableCell align="right">傾向</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {anomalyData.anomalies.map((row) => (
                        <TableRow key={row.name}>
                          <TableCell>
                            <Typography 
                              component="span" 
                              sx={{ 
                                display: 'inline-block', 
                                width: 8, 
                                height: 8, 
                                borderRadius: '50%', 
                                backgroundColor: getSeverityColor(row.severity),
                                mr: 1 
                              }} 
                            />
                            {row.name}
                          </TableCell>
                          <TableCell align="right">{row.count}</TableCell>
                          <TableCell align="right">{row.percent}%</TableCell>
                          <TableCell align="right">{getTrendIcon(row.trend)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
                <Box sx={{ height: 200, mt: 2 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <RechartsePieChart>
                      <Pie
                        data={anomalyData.anomalies}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="count"
                        nameKey="name"
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      >
                        {anomalyData.anomalies.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </RechartsePieChart>
                  </ResponsiveContainer>
                </Box>
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', p: 4 }}>
                データが利用できません
              </Typography>
            )}
          </Paper>
        </Grid>

        {/* カテゴリ分析 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <PieChartIcon color="primary" sx={{ mr: 1 }} />
              <Typography variant="h6">
                カテゴリ別分析
              </Typography>
            </Box>
            {categoryLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : categoryError ? (
              <Alert severity="error">
                カテゴリデータの読み込み中にエラーが発生しました。
              </Alert>
            ) : categoryData && categoryData.categories ? (
              <ResponsiveContainer width="100%" height={300}>
                <RechartsePieChart>
                  <Pie
                    data={categoryData.categories}
                    cx="50%"
                    cy="50%"
                    labelLine={true}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                    nameKey="name"
                    label={({ name, value }) => `${name}: ${value}%`}
                  >
                    {categoryData.categories.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </RechartsePieChart>
              </ResponsiveContainer>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', p: 4 }}>
                データが利用できません
              </Typography>
            )}
          </Paper>
        </Grid>

        {/* 月次トレンド */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <BarChartIcon color="primary" sx={{ mr: 1 }} />
              <Typography variant="h6">
                月次トレンド
              </Typography>
            </Box>
            {trendLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : trendError ? (
              <Alert severity="error">
                トレンドデータの読み込み中にエラーが発生しました。
              </Alert>
            ) : trendData && trendData.trends ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={trendData.trends}
                  margin={{
                    top: 5,
                    right: 30,
                    left: 20,
                    bottom: 5,
                  }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="total" name="処理サンプル数" fill="#8884d8" />
                  <Bar dataKey="anomalies" name="異常検出数" fill="#f44336" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', p: 4 }}>
                データが利用できません
              </Typography>
            )}
          </Paper>
        </Grid>

        {/* リスク相関 */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <BubbleChartIcon color="primary" sx={{ mr: 1 }} />
              <Typography variant="h6">
                リスク相関分析
              </Typography>
            </Box>
            {riskCorrelationLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : riskCorrelationError ? (
              <Alert severity="error">
                リスク相関データの読み込み中にエラーが発生しました。
              </Alert>
            ) : riskCorrelationData && riskCorrelationData.correlation ? (
              <Box>
                <Typography variant="caption" color="text.secondary" paragraph>
                  X軸: サンプル複雑性、Y軸: 検出異常数、サイズ: 重要度
                </Typography>
                <ResponsiveContainer width="100%" height={350}>
                  <ScatterChart
                    margin={{
                      top: 20,
                      right: 20,
                      bottom: 20,
                      left: 20,
                    }}
                  >
                    <CartesianGrid />
                    <XAxis type="number" dataKey="x" name="複雑性" />
                    <YAxis type="number" dataKey="y" name="異常数" />
                    <ZAxis type="number" dataKey="z" range={[100, 500]} name="重要度" />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }} formatter={(value, name, props) => {
                      if (name === '複雑性' || name === '異常数' || name === '重要度') {
                        return [value, name];
                      }
                      return [props.payload.name, '取引ID'];
                    }} />
                    <Scatter name="取引" data={riskCorrelationData.correlation} fill="#8884d8" />
                  </ScatterChart>
                </ResponsiveContainer>
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', p: 4 }}>
                データが利用できません
              </Typography>
            )}
          </Paper>
        </Grid>

        {/* AIインサイト */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <InfoIcon color="primary" sx={{ mr: 1 }} />
              <Typography variant="h6">
                AIインサイト
              </Typography>
            </Box>
            {insightLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : insightError ? (
              <Alert severity="error">
                インサイトデータの読み込み中にエラーが発生しました。
              </Alert>
            ) : insightData && insightData.insights ? (
              <List>
                {insightData.insights.map((insight) => (
                  <ListItem 
                    key={insight.id} 
                    alignItems="flex-start"
                    sx={{ 
                      mb: 1, 
                      borderLeft: `3px solid ${insight.priority === 'high' ? '#f44336' : insight.priority === 'medium' ? '#ff9800' : '#4caf50'}`,
                      backgroundColor: 'rgba(0, 0, 0, 0.02)',
                      borderRadius: '4px'
                    }}
                  >
                    <ListItemText
                      primary={insight.title}
                      secondary={
                        <React.Fragment>
                          <Typography
                            component="span"
                            variant="body2"
                            color="text.primary"
                          >
                            {insight.description}
                          </Typography>
                        </React.Fragment>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', p: 4 }}>
                データが利用できません
              </Typography>
            )}
          </Paper>
        </Grid>

        {/* レポート */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <PdfIcon color="primary" sx={{ mr: 1 }} />
              <Typography variant="h6">
                分析レポート
              </Typography>
            </Box>
            {reportLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : reportError ? (
              <Alert severity="error">
                レポートデータの読み込み中にエラーが発生しました。
              </Alert>
            ) : reportData && reportData.reports ? (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>レポート名</TableCell>
                      <TableCell>作成日</TableCell>
                      <TableCell>カテゴリ</TableCell>
                      <TableCell>作成者</TableCell>
                      <TableCell align="right">アクション</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {reportData.reports.map((report) => (
                      <TableRow key={report.id}>
                        <TableCell>{report.name}</TableCell>
                        <TableCell>{report.createdAt}</TableCell>
                        <TableCell>
                          <Chip 
                            size="small" 
                            label={report.category} 
                          />
                        </TableCell>
                        <TableCell>{report.author}</TableCell>
                        <TableCell align="right">
                          <Stack direction="row" spacing={1} justifyContent="flex-end">
                            {report.format === 'pdf' && <PdfIcon color="primary" fontSize="small" />}
                            {report.format === 'excel' && <ExcelIcon color="success" fontSize="small" />}
                            {report.format === 'ppt' && <PptIcon color="warning" fontSize="small" />}
                            <IconButton size="small">
                              <InfoIcon fontSize="small" />
                            </IconButton>
                          </Stack>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', p: 4 }}>
                データが利用できません
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default AnalysisDashboard; 