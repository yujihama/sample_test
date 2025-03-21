import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Button,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Card,
  CardContent,
  Divider,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  Search as SearchIcon,
  Add as AddIcon,
  CloudUpload as CloudUploadIcon,
  FilterList as FilterListIcon,
  Visibility as VisibilityIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Description as DescriptionIcon,
  Check as CheckIcon,
  Schedule as ScheduleIcon
} from '@mui/icons-material';
import { sampleApi } from '../../services/api';
import useApi from '../../hooks/useApi';

// タブパネルコンポーネント
function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`sample-tabpanel-${index}`}
      aria-labelledby={`sample-tab-${index}`}
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

const SampleManagement = () => {
  const [tabValue, setTabValue] = useState(0);
  const [searchValue, setSearchValue] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [openDialog, setOpenDialog] = useState(false);
  const [selectedSample, setSelectedSample] = useState(null);

  // サンプル一覧を取得
  const { 
    data: samplesData, 
    loading: samplesLoading, 
    error: samplesError,
    refetch: refetchSamples
  } = useApi(sampleApi.getSamples, []);

  // サンプルの詳細情報を取得（選択時）
  const { 
    data: sampleDetailData, 
    loading: sampleDetailLoading, 
    error: sampleDetailError,
    refetch: refetchSampleDetail
  } = useApi(
    () => selectedSample ? sampleApi.getSampleDetails(selectedSample.id) : null, 
    [selectedSample && selectedSample.id]
  );

  // タブ変更ハンドラ
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // 検索値変更ハンドラ
  const handleSearchChange = (event) => {
    setSearchValue(event.target.value);
  };

  // ステータスフィルター変更ハンドラ
  const handleStatusFilterChange = (event) => {
    setStatusFilter(event.target.value);
  };

  // タイプフィルター変更ハンドラ
  const handleTypeFilterChange = (event) => {
    setTypeFilter(event.target.value);
  };

  // サンプル選択ハンドラ
  const handleSampleSelect = (sample) => {
    setSelectedSample(sample);
    setOpenDialog(true);
  };

  // ダイアログを閉じるハンドラ
  const handleCloseDialog = () => {
    setOpenDialog(false);
  };

  // フィルタリングしたサンプルのリストを取得
  const getFilteredSamples = () => {
    if (!samplesData || !samplesData.samples) return [];
    
    return samplesData.samples.filter(sample => {
      // 検索フィルター
      const matchesSearch = searchValue === '' || 
        sample.name.toLowerCase().includes(searchValue.toLowerCase()) ||
        sample.id.toLowerCase().includes(searchValue.toLowerCase());
      
      // ステータスフィルター
      const matchesStatus = statusFilter === 'all' || sample.status === statusFilter;
      
      // タイプフィルター
      const matchesType = typeFilter === 'all' || sample.type === typeFilter;
      
      return matchesSearch && matchesStatus && matchesType;
    });
  };

  // ステータスに基づく色を返す
  const getStatusColor = (status) => {
    switch(status) {
      case 'completed': return '#4caf50';
      case 'processing': return '#2196f3';
      case 'pending': return '#ff9800';
      case 'queued': return '#9e9e9e';
      default: return '#757575';
    }
  };

  // ステータスに基づくアイコンを返す
  const getStatusIcon = (status) => {
    switch(status) {
      case 'completed': return <CheckIcon />;
      case 'processing': return <LinearProgress variant="determinate" value={50} sx={{ width: '100%' }} />;
      case 'pending': return <ScheduleIcon />;
      case 'queued': return <Schedule as ScheduleIcon color="disabled" />;
      default: return null;
    }
  };

  // 利用可能なサンプルタイプを取得
  const getSampleTypes = () => {
    if (!samplesData || !samplesData.samples) return [];
    
    // 重複を削除してユニークなタイプを取得
    const typeSet = new Set(samplesData.samples.map(sample => sample.type));
    return Array.from(typeSet);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        サンプル管理
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" paragraph>
        監査対象サンプルの登録、管理、状態確認を行います。
      </Typography>

      <Grid container spacing={3}>
        {/* フィルターとアクションボタン */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} sm={4}>
                <TextField
                  placeholder="サンプル名またはIDで検索..."
                  variant="outlined"
                  fullWidth
                  size="small"
                  value={searchValue}
                  onChange={handleSearchChange}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon />
                      </InputAdornment>
                    ),
                  }}
                />
              </Grid>
              <Grid item xs={6} sm={2}>
                <FormControl fullWidth size="small">
                  <InputLabel>ステータス</InputLabel>
                  <Select
                    value={statusFilter}
                    label="ステータス"
                    onChange={handleStatusFilterChange}
                  >
                    <MenuItem value="all">すべて</MenuItem>
                    <MenuItem value="completed">完了</MenuItem>
                    <MenuItem value="processing">処理中</MenuItem>
                    <MenuItem value="pending">保留中</MenuItem>
                    <MenuItem value="queued">キュー内</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={6} sm={2}>
                <FormControl fullWidth size="small">
                  <InputLabel>タイプ</InputLabel>
                  <Select
                    value={typeFilter}
                    label="タイプ"
                    onChange={handleTypeFilterChange}
                  >
                    <MenuItem value="all">すべて</MenuItem>
                    {getSampleTypes().map((type, index) => (
                      <MenuItem key={index} value={type}>{type}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm="auto" sx={{ ml: 'auto' }}>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                  >
                    新規登録
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<CloudUploadIcon />}
                  >
                    一括インポート
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* サンプル一覧 */}
        <Grid item xs={12}>
          <Paper>
            <Tabs
              value={tabValue}
              onChange={handleTabChange}
              indicatorColor="primary"
              textColor="primary"
              variant="scrollable"
              scrollButtons="auto"
              sx={{ borderBottom: 1, borderColor: 'divider' }}
            >
              <Tab label="すべてのサンプル" />
              <Tab label="売上取引" />
              <Tab label="購買取引" />
              <Tab label="経費精算" />
              <Tab label="固定資産" />
            </Tabs>

            <TabPanel value={tabValue} index={0}>
              {samplesLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                  <CircularProgress />
                </Box>
              ) : samplesError ? (
                <Alert severity="error">
                  サンプルデータの読み込み中にエラーが発生しました。
                </Alert>
              ) : getFilteredSamples().length === 0 ? (
                <Box sx={{ textAlign: 'center', p: 4 }}>
                  <Typography variant="h6" color="text.secondary">
                    表示するサンプルがありません
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    検索条件を変更するか、新しいサンプルを登録してください
                  </Typography>
                </Box>
              ) : (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>サンプルID</TableCell>
                        <TableCell>名称</TableCell>
                        <TableCell>タイプ</TableCell>
                        <TableCell>ステータス</TableCell>
                        <TableCell>進捗</TableCell>
                        <TableCell>更新日</TableCell>
                        <TableCell align="right">アクション</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {getFilteredSamples().map((sample) => (
                        <TableRow key={sample.id}>
                          <TableCell>{sample.id}</TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              <DescriptionIcon sx={{ mr: 1, color: 'text.secondary' }} />
                              <Typography variant="body2">
                                {sample.name}
                              </Typography>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Chip label={sample.type} size="small" />
                          </TableCell>
                          <TableCell>
                            <Chip 
                              label={
                                sample.status === 'completed' ? '完了' :
                                sample.status === 'processing' ? '処理中' :
                                sample.status === 'pending' ? '保留中' :
                                '待機中'
                              } 
                              size="small" 
                              sx={{ 
                                bgcolor: `${getStatusColor(sample.status)}20`,
                                color: getStatusColor(sample.status),
                                fontWeight: 'bold'
                              }} 
                            />
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', width: 100 }}>
                              <LinearProgress 
                                variant="determinate" 
                                value={sample.progress} 
                                sx={{ width: '100%', mr: 1 }} 
                              />
                              <Typography variant="caption">{sample.progress}%</Typography>
                            </Box>
                          </TableCell>
                          <TableCell>{sample.updatedAt}</TableCell>
                          <TableCell align="right">
                            <IconButton 
                              size="small" 
                              onClick={() => handleSampleSelect(sample)}
                            >
                              <VisibilityIcon fontSize="small" />
                            </IconButton>
                            <IconButton size="small">
                              <EditIcon fontSize="small" />
                            </IconButton>
                            <IconButton size="small" color="error">
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </TabPanel>

            <TabPanel value={tabValue} index={1}>
              <Typography variant="body2" color="text.secondary" align="center">
                売上取引の監査サンプルがここに表示されます
              </Typography>
            </TabPanel>

            <TabPanel value={tabValue} index={2}>
              <Typography variant="body2" color="text.secondary" align="center">
                購買取引の監査サンプルがここに表示されます
              </Typography>
            </TabPanel>

            <TabPanel value={tabValue} index={3}>
              <Typography variant="body2" color="text.secondary" align="center">
                経費精算の監査サンプルがここに表示されます
              </Typography>
            </TabPanel>

            <TabPanel value={tabValue} index={4}>
              <Typography variant="body2" color="text.secondary" align="center">
                固定資産の監査サンプルがここに表示されます
              </Typography>
            </TabPanel>
          </Paper>
        </Grid>
      </Grid>

      {/* サンプル詳細ダイアログ */}
      <Dialog
        open={openDialog}
        onClose={handleCloseDialog}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          サンプル詳細
        </DialogTitle>
        <DialogContent dividers>
          {sampleDetailLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : sampleDetailError ? (
            <Alert severity="error">
              サンプル詳細の読み込み中にエラーが発生しました。
            </Alert>
          ) : selectedSample ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6">{selectedSample.name}</Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                  <Chip 
                    label={selectedSample.id} 
                    size="small" 
                    sx={{ mr: 1 }} 
                  />
                  <Chip 
                    label={selectedSample.type} 
                    size="small" 
                    sx={{ mr: 1 }} 
                  />
                  <Chip 
                    label={
                      selectedSample.status === 'completed' ? '完了' :
                      selectedSample.status === 'processing' ? '処理中' :
                      selectedSample.status === 'pending' ? '保留中' :
                      '待機中'
                    } 
                    size="small" 
                    sx={{ 
                      bgcolor: `${getStatusColor(selectedSample.status)}20`,
                      color: getStatusColor(selectedSample.status),
                      fontWeight: 'bold'
                    }} 
                  />
                </Box>
              </Grid>

              <Grid item xs={12} sm={6}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="subtitle1" gutterBottom>
                      基本情報
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Grid container spacing={2}>
                      <Grid item xs={4}>
                        <Typography variant="body2" color="text.secondary">
                          登録日
                        </Typography>
                      </Grid>
                      <Grid item xs={8}>
                        <Typography variant="body2">
                          {selectedSample.createdAt}
                        </Typography>
                      </Grid>
                      <Grid item xs={4}>
                        <Typography variant="body2" color="text.secondary">
                          更新日
                        </Typography>
                      </Grid>
                      <Grid item xs={8}>
                        <Typography variant="body2">
                          {selectedSample.updatedAt}
                        </Typography>
                      </Grid>
                      <Grid item xs={4}>
                        <Typography variant="body2" color="text.secondary">
                          サンプルサイズ
                        </Typography>
                      </Grid>
                      <Grid item xs={8}>
                        <Typography variant="body2">
                          {selectedSample.size} 件
                        </Typography>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="subtitle1" gutterBottom>
                      進捗状況
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Box sx={{ mt: 2, mb: 1 }}>
                      <Typography variant="body2" gutterBottom>
                        処理進捗: {selectedSample.progress}%
                      </Typography>
                      <LinearProgress 
                        variant="determinate" 
                        value={selectedSample.progress} 
                        sx={{ mb: 2 }} 
                      />
                    </Box>
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="body2" gutterBottom>
                        ステータス
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Box sx={{ mr: 1, width: 16, height: 16, borderRadius: '50%', bgcolor: getStatusColor(selectedSample.status) }} />
                        <Typography variant="body2">
                          {selectedSample.status === 'completed' ? '完了' :
                           selectedSample.status === 'processing' ? '処理中' :
                           selectedSample.status === 'pending' ? '保留中' :
                           '待機中'}
                        </Typography>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="subtitle1" gutterBottom>
                      タグ
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {selectedSample.tags && selectedSample.tags.map((tag, index) => (
                        <Chip key={index} label={tag} size="small" variant="outlined" />
                      ))}
                      {(!selectedSample.tags || selectedSample.tags.length === 0) && (
                        <Typography variant="body2" color="text.secondary">
                          タグはありません
                        </Typography>
                      )}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>閉じる</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SampleManagement; 