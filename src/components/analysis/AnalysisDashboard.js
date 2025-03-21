import React, { useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Paper,
  Card,
  CardContent,
  CardHeader,
  Divider,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tabs,
  Tab,
  IconButton,
  Tooltip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  ToggleButtonGroup,
  ToggleButton,
  Alert,
  InputAdornment,
  CircularProgress
} from '@mui/material';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  ZAxis,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar
} from 'recharts';
import {
  Timeline as TimelineIcon,
  PieChart as PieChartIcon,
  BarChart as BarChartIcon,
  BubbleChart as BubbleChartIcon,
  ShowChart as ShowChartIcon,
  TrendingUp as TrendingUpIcon,
  FilterList as FilterListIcon,
  FileDownload as FileDownloadIcon,
  Refresh as RefreshIcon,
  InsertDriveFile as InsertDriveFileIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Info as InfoIcon,
  BugReport as BugReportIcon,
  Search as SearchIcon,
  Save as SaveIcon,
  Print as PrintIcon,
  Share as ShareIcon,
  DataUsage as DataUsageIcon,
  EventNote as EventNoteIcon,
  TrendingDown as TrendingDownIcon
} from '@mui/icons-material';

// APIサービスとカスタムフックをインポート
import { analysisApi } from '../../frontend/services/api';
import useApi from '../../frontend/hooks/useApi';

// 円グラフの色
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

// タブパネルのコンポーネント
function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`analysis-tabpanel-${index}`}
      aria-labelledby={`analysis-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ py: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const AnalysisDashboard = () => {
  const [tabValue, setTabValue] = useState(0);
  const [chartType, setChartType] = useState('bar');
  const [timeRange, setTimeRange] = useState('month');
  const [department, setDepartment] = useState('all');
  
  // APIから異常検出データを取得
  const { 
    data: anomalyData, 
    loading: anomalyLoading, 
    error: anomalyError,
    refetch: refetchAnomaly
  } = useApi(analysisApi.getAnomalyData, []);
  
  // APIからカテゴリデータを取得
  const { 
    data: categoryData, 
    loading: categoryLoading, 
    error: categoryError,
    refetch: refetchCategory
  } = useApi(analysisApi.getCategoryData, []);
  
  // APIからトレンドデータを取得
  const { 
    data: trendData, 
    loading: trendLoading, 
    error: trendError,
    refetch: refetchTrend
  } = useApi(analysisApi.getTrendData, []);
  
  // 異常検出データを取得
  const getAnomalyData = () => {
    if (!anomalyData || !anomalyData.anomalies) return [];
    return anomalyData.anomalies;
  };
  
  // カテゴリデータを取得
  const getCategoryData = () => {
    if (!categoryData || !categoryData.categories) return [];
    return categoryData.categories;
  };
  
  // トレンドデータを取得
  const getTrendData = () => {
    if (!trendData || !trendData.trends) return [];
    return trendData.trends;
  };
  
  // タブ変更ハンドラー
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };
  
  // チャートタイプ変更ハンドラー
  const handleChartTypeChange = (event, newValue) => {
    if (newValue !== null) {
      setChartType(newValue);
    }
  };
  
  // 期間変更ハンドラー
  const handleTimeRangeChange = (event) => {
    setTimeRange(event.target.value);
  };
  
  // 部門変更ハンドラー
  const handleDepartmentChange = (event) => {
    setDepartment(event.target.value);
  };
  
  // すべてのデータを更新
  const refreshAllData = () => {
    refetchAnomaly();
    refetchCategory();
    refetchTrend();
  };
  
  // 概要統計
  const renderSummaryStats = () => (
    <Grid container spacing={3} sx={{ mb: 4 }}>
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
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            分析済みドキュメント
          </Typography>
          <Typography variant="h3" component="div" sx={{ flexGrow: 1 }}>
            0
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <TrendingUpIcon fontSize="small" color="success" sx={{ mr: 1 }} />
            <Typography variant="body2" color="success.main">
              前月比 0%
            </Typography>
          </Box>
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
            borderLeft: '4px solid #4caf50'
          }}
        >
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            正常率
          </Typography>
          <Typography variant="h3" component="div" sx={{ flexGrow: 1 }}>
            0%
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <TrendingUpIcon fontSize="small" color="success" sx={{ mr: 1 }} />
            <Typography variant="body2" color="success.main">
              前月比 0%
            </Typography>
          </Box>
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
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            異常検出数
          </Typography>
          <Typography variant="h3" component="div" sx={{ flexGrow: 1 }}>
            0
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <TrendingDownIcon fontSize="small" color="success" sx={{ mr: 1 }} />
            <Typography variant="body2" color="success.main">
              前月比 0%
            </Typography>
          </Box>
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
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            平均処理時間
          </Typography>
          <Typography variant="h3" component="div" sx={{ flexGrow: 1 }}>
            0秒
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <TrendingUpIcon fontSize="small" color="success" sx={{ mr: 1 }} />
            <Typography variant="body2" color="success.main">
              前月比 0秒
            </Typography>
          </Box>
        </Paper>
      </Grid>
    </Grid>
  );
  
  // 異常分布チャート
  const renderAnomalyDistribution = () => (
    <Card elevation={2} sx={{ mb: 4 }}>
      <CardHeader 
        title="異常タイプ分布" 
        action={
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <ToggleButtonGroup
              value={chartType}
              exclusive
              onChange={handleChartTypeChange}
              size="small"
              sx={{ mr: 1 }}
            >
              <ToggleButton value="pie">
                <PieChartIcon fontSize="small" />
              </ToggleButton>
              <ToggleButton value="bar">
                <BarChartIcon fontSize="small" />
              </ToggleButton>
            </ToggleButtonGroup>
            <IconButton size="small" onClick={refreshAllData}>
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Box>
        }
      />
      <Divider />
      <CardContent>
        {anomalyLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 5 }}>
            <CircularProgress />
          </Box>
        ) : anomalyError ? (
          <Alert severity="error">
            データの読み込みに失敗しました: {anomalyError}
          </Alert>
        ) : getAnomalyData().length === 0 ? (
          <Alert severity="info">
            異常検出データはありません
          </Alert>
        ) : (
          <Box sx={{ height: 300 }}>
            <Alert severity="info">
              データはありますが、表示できるデータがありません
            </Alert>
          </Box>
        )}
      </CardContent>
    </Card>
  );
  
  // 月次推移チャート
  const renderMonthlyTrend = () => (
    <Card elevation={2} sx={{ mb: 4 }}>
      <CardHeader 
        title="検出トレンド" 
        action={
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <FormControl size="small" sx={{ width: 120, mr: 1 }}>
              <InputLabel>期間</InputLabel>
              <Select
                value={timeRange}
                label="期間"
                onChange={handleTimeRangeChange}
                size="small"
              >
                <MenuItem value="week">週間</MenuItem>
                <MenuItem value="month">月間</MenuItem>
                <MenuItem value="quarter">四半期</MenuItem>
                <MenuItem value="year">年間</MenuItem>
              </Select>
            </FormControl>
            <IconButton size="small" onClick={refreshAllData}>
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Box>
        }
      />
      <Divider />
      <CardContent>
        {trendLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 5 }}>
            <CircularProgress />
          </Box>
        ) : trendError ? (
          <Alert severity="error">
            データの読み込みに失敗しました: {trendError}
          </Alert>
        ) : getTrendData().length === 0 ? (
          <Alert severity="info">
            トレンドデータはありません
          </Alert>
        ) : (
          <Box sx={{ height: 300 }}>
            <Alert severity="info">
              データはありますが、表示できるデータがありません
            </Alert>
          </Box>
        )}
      </CardContent>
    </Card>
  );
  
  // 部門別分析
  const renderDepartmentAnalysis = () => (
    <Card elevation={2}>
      <CardHeader 
        title="部門別分析" 
        action={
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <FormControl sx={{ minWidth: 120 }} size="small">
              <InputLabel id="department-select-label">部門</InputLabel>
              <Select
                labelId="department-select-label"
                id="department-select"
                value={department}
                label="部門"
                onChange={handleDepartmentChange}
              >
                <MenuItem value="all">すべて</MenuItem>
                <MenuItem value="legal">法務部</MenuItem>
                <MenuItem value="finance">財務部</MenuItem>
                <MenuItem value="procurement">購買部</MenuItem>
                <MenuItem value="sales">営業部</MenuItem>
                <MenuItem value="hr">人事部</MenuItem>
              </Select>
            </FormControl>
            <Tooltip title="ダウンロード">
              <IconButton>
                <FileDownloadIcon />
              </IconButton>
            </Tooltip>
          </Box>
        }
      />
      <Divider />
      <CardContent>
        <Alert severity="info">
          部門別分析データはありません
        </Alert>
      </CardContent>
    </Card>
  );
  
  // リスク評価チャート
  const renderRiskAssessment = () => (
    <Card elevation={2}>
      <CardHeader 
        title="リスク評価" 
        action={
          <Button
            variant="outlined"
            startIcon={<FileDownloadIcon />}
            size="small"
          >
            レポート出力
          </Button>
        }
      />
      <Divider />
      <CardContent>
        <Alert severity="info">
          リスク評価データはありません
        </Alert>
      </CardContent>
    </Card>
  );
  
  // ドキュメントタイプ分析
  const renderDocumentTypeAnalysis = () => (
    <Card elevation={2}>
      <CardHeader 
        title="ドキュメントタイプ分析" 
        action={
          <Tooltip title="ダウンロード">
            <IconButton>
              <FileDownloadIcon />
            </IconButton>
          </Tooltip>
        }
      />
      <Divider />
      <CardContent>
        <Alert severity="info">
          ドキュメントタイプ分析データはありません
        </Alert>
      </CardContent>
    </Card>
  );
  
  // AI生成インサイト
  const renderAIInsights = () => (
    <Card elevation={2}>
      <CardHeader 
        title="AI生成インサイト" 
        action={
          <Button
            variant="outlined"
            startIcon={<SaveIcon />}
            size="small"
          >
            レポート保存
          </Button>
        }
      />
      <Divider />
      <CardContent>
        <TextField
          placeholder="インサイトを検索..."
          size="small"
          fullWidth
          sx={{ mb: 2 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
        
        <Alert severity="info">
          AIインサイトデータはありません
        </Alert>
      </CardContent>
    </Card>
  );
  
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        結果分析ダッシュボード
      </Typography>
      
      {/* 統計概要 */}
      {renderSummaryStats()}
      
      {/* タブ切り替え */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="analysis tabs">
          <Tab 
            icon={<DataUsageIcon />} 
            iconPosition="start" 
            label="異常検出分析" 
          />
          <Tab 
            icon={<EventNoteIcon />} 
            iconPosition="start" 
            label="ドキュメント分析" 
          />
          <Tab 
            icon={<TrendingUpIcon />} 
            iconPosition="start" 
            label="AI洞察" 
          />
        </Tabs>
      </Box>
      
      {/* タブパネル */}
      <TabPanel value={tabValue} index={0}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            {renderAnomalyDistribution()}
          </Grid>
          <Grid item xs={12} md={6}>
            {renderRiskAssessment()}
          </Grid>
          <Grid item xs={12}>
            {renderMonthlyTrend()}
          </Grid>
          <Grid item xs={12}>
            {renderDepartmentAnalysis()}
          </Grid>
        </Grid>
      </TabPanel>
      
      <TabPanel value={tabValue} index={1}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card elevation={2}>
              <CardHeader title="ドキュメントタイプ別の異常率" />
              <Divider />
              <CardContent>
                {categoryLoading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 5 }}>
                    <CircularProgress />
                  </Box>
                ) : categoryError ? (
                  <Alert severity="error">
                    データの読み込みに失敗しました: {categoryError}
                  </Alert>
                ) : getCategoryData().length === 0 ? (
                  <Alert severity="info">
                    カテゴリデータはありません
                  </Alert>
                ) : (
                  <Box sx={{ height: 300 }}>
                    <Alert severity="info">
                      データはありますが、表示できるデータがありません
                    </Alert>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            {renderDocumentTypeAnalysis()}
          </Grid>
          <Grid item xs={12}>
            <Card elevation={2}>
              <CardHeader title="処理パフォーマンス分析" />
              <Divider />
              <CardContent>
                <Alert severity="info">
                  処理パフォーマンスデータはありません
                </Alert>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>
      
      <TabPanel value={tabValue} index={2}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            {renderAIInsights()}
          </Grid>
        </Grid>
      </TabPanel>
      
      {/* アクションパネル */}
      <Paper
        elevation={2}
        sx={{
          position: 'sticky',
          bottom: 16,
          p: 2,
          mt: 3,
          display: 'flex',
          justifyContent: 'space-between',
          zIndex: 1
        }}
      >
        <Button
          variant="contained"
          startIcon={<FileDownloadIcon />}
        >
          分析レポート出力
        </Button>
        
        <Box>
          <Button
            variant="outlined"
            startIcon={<PrintIcon />}
            sx={{ mr: 1 }}
          >
            印刷
          </Button>
          <Button
            variant="outlined"
            startIcon={<ShareIcon />}
          >
            共有
          </Button>
        </Box>
      </Paper>
    </Box>
  );
};

export default AnalysisDashboard; 