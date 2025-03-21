import React, { useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CardHeader,
  Divider,
  Button,
  TextField,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  IconButton,
  InputAdornment,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Tooltip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Stack,
  FormControl,
  InputLabel,
  Select,
  Tabs,
  Tab,
  Badge,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  Add as AddIcon,
  Search as SearchIcon,
  FilterList as FilterListIcon,
  CloudUpload as CloudUploadIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Visibility as VisibilityIcon,
  MoreVert as MoreVertIcon,
  ContentCopy as ContentCopyIcon,
  Download as DownloadIcon,
  Archive as ArchiveIcon,
  Description as DescriptionIcon,
  CheckCircle as CheckCircleIcon,
  ErrorOutline as ErrorOutlineIcon,
  ScheduleOutlined as ScheduleOutlinedIcon,
  Sort as SortIcon,
  FolderSpecial as FolderSpecialIcon,
  FolderOpen as FolderOpenIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';

// APIサービスとカスタムフックをインポート
import { sampleApi } from '../../frontend/services/api';
import useApi from '../../frontend/hooks/useApi';

// タブパネルのコンポーネント
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
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const SampleManagement = () => {
  // タブの状態
  const [tabValue, setTabValue] = useState(0);
  
  // ページネーション
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  
  // 検索/フィルター
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  
  // メニュー状態
  const [menuAnchorEl, setMenuAnchorEl] = useState(null);
  const [selectedDocument, setSelectedDocument] = useState(null);
  
  // ダイアログ状態
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  
  // APIからサンプルデータを取得
  const { 
    data: samplesData, 
    loading: samplesLoading, 
    error: samplesError,
    refetch: refetchSamples
  } = useApi(() => sampleApi.getSamples(), {
    dependencies: []
  });
  
  // サンプルデータを取得
  const getSamples = () => {
    if (!samplesData || !samplesData.samples) return [];
    return samplesData.samples;
  };
  
  // タブ変更ハンドラ
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };
  
  // ページ変更ハンドラ
  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };
  
  // 1ページあたりの行数変更ハンドラ
  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };
  
  // 検索テキスト変更ハンドラ
  const handleSearchChange = (event) => {
    setSearchText(event.target.value);
    setPage(0);
  };
  
  // ステータスフィルター変更ハンドラ
  const handleStatusFilterChange = (event) => {
    setStatusFilter(event.target.value);
    setPage(0);
  };
  
  // タイプフィルター変更ハンドラ
  const handleTypeFilterChange = (event) => {
    setTypeFilter(event.target.value);
    setPage(0);
  };
  
  // メニューを開く
  const handleMenuOpen = (event, document) => {
    setMenuAnchorEl(event.currentTarget);
    setSelectedDocument(document);
  };
  
  // メニューを閉じる
  const handleMenuClose = () => {
    setMenuAnchorEl(null);
  };
  
  // アップロードダイアログを開く
  const handleUploadDialogOpen = () => {
    setUploadDialogOpen(true);
  };
  
  // アップロードダイアログを閉じる
  const handleUploadDialogClose = () => {
    setUploadDialogOpen(false);
  };
  
  // 削除ダイアログを開く
  const handleDeleteDialogOpen = () => {
    handleMenuClose();
    setDeleteDialogOpen(true);
  };
  
  // 削除ダイアログを閉じる
  const handleDeleteDialogClose = () => {
    setDeleteDialogOpen(false);
  };
  
  // サンプルデータ更新
  const refreshData = () => {
    refetchSamples();
  };
  
  // ステータスに応じたスタイル
  const getStatusChip = (status) => {
    switch(status) {
      case 'completed':
        return <Chip icon={<CheckCircleIcon />} label="完了" color="success" size="small" />;
      case 'in_progress':
        return <Chip icon={<ScheduleOutlinedIcon />} label="処理中" color="primary" size="small" />;
      case 'pending':
        return <Chip icon={<ScheduleOutlinedIcon />} label="保留中" color="warning" size="small" />;
      case 'error':
        return <Chip icon={<ErrorOutlineIcon />} label="エラー" color="error" size="small" />;
      default:
        return <Chip label={status} size="small" />;
    }
  };
  
  // ドキュメントリスト表示
  const documentList = () => {
    const samples = getSamples();
    const filteredSamples = samples.filter(doc => {
      // 検索テキストフィルター
      const matchesSearch = searchText === '' || 
        doc.name.toLowerCase().includes(searchText.toLowerCase());
      
      // ステータスフィルター
      const matchesStatus = statusFilter === 'all' || 
        doc.status === statusFilter;
      
      // タイプフィルター
      const matchesType = typeFilter === 'all' || 
        doc.type === typeFilter;
      
      return matchesSearch && matchesStatus && matchesType;
    });
    
    // 空のテーブルを表示
    if (filteredSamples.length === 0) {
      return (
        <Alert severity="info" sx={{ my: 2 }}>
          サンプルデータはありません
        </Alert>
      );
    }
    
    // 表示用にページネーション
    const paginatedSamples = filteredSamples
      .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);
    
    return (
      <>
        <TableContainer component={Paper}>
          <Table sx={{ minWidth: 650 }}>
            <TableHead>
              <TableRow>
                <TableCell>名前</TableCell>
                <TableCell>タイプ</TableCell>
                <TableCell>ステータス</TableCell>
                <TableCell>タグ</TableCell>
                <TableCell>アップロード日</TableCell>
                <TableCell>サイズ</TableCell>
                <TableCell align="right">アクション</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedSamples.map((sample) => (
                <TableRow key={sample.id}>
                  <TableCell component="th" scope="row">
                    {sample.name}
                  </TableCell>
                  <TableCell>{sample.type}</TableCell>
                  <TableCell>{getStatusChip(sample.status)}</TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1}>
                      {sample.tags && sample.tags.map((tag, index) => (
                        <Chip 
                          key={index} 
                          label={tag} 
                          size="small" 
                          variant="outlined" 
                        />
                      ))}
                    </Stack>
                  </TableCell>
                  <TableCell>
                    {new Date(sample.uploadDate).toLocaleDateString()}
                  </TableCell>
                  <TableCell>{sample.size}</TableCell>
                  <TableCell align="right">
                    <Tooltip title="詳細を表示">
                      <IconButton size="small">
                        <VisibilityIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="編集">
                      <IconButton size="small">
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <IconButton
                      size="small"
                      onClick={(event) => handleMenuOpen(event, sample)}
                    >
                      <MoreVertIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[5, 10, 25]}
          component="div"
          count={filteredSamples.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </>
    );
  };
  
  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" gutterBottom sx={{ flexGrow: 1 }}>
          サンプル管理
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={refreshData}
          sx={{ ml: 2, mr: 2 }}
        >
          更新
        </Button>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleUploadDialogOpen}
        >
          サンプル追加
        </Button>
      </Box>
      
      {/* 検索・フィルター */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={4}>
            <TextField
              fullWidth
              placeholder="サンプルを検索..."
              value={searchText}
              onChange={handleSearchChange}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={3}>
            <FormControl fullWidth size="small">
              <InputLabel id="status-filter-label">ステータス</InputLabel>
              <Select
                labelId="status-filter-label"
                value={statusFilter}
                label="ステータス"
                onChange={handleStatusFilterChange}
              >
                <MenuItem value="all">すべて</MenuItem>
                <MenuItem value="completed">完了</MenuItem>
                <MenuItem value="in_progress">処理中</MenuItem>
                <MenuItem value="pending">保留中</MenuItem>
                <MenuItem value="error">エラー</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={3}>
            <FormControl fullWidth size="small">
              <InputLabel id="type-filter-label">タイプ</InputLabel>
              <Select
                labelId="type-filter-label"
                value={typeFilter}
                label="タイプ"
                onChange={handleTypeFilterChange}
              >
                <MenuItem value="all">すべて</MenuItem>
                <MenuItem value="契約書">契約書</MenuItem>
                <MenuItem value="請求書">請求書</MenuItem>
                <MenuItem value="監査レポート">監査レポート</MenuItem>
                <MenuItem value="財務報告">財務報告</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={2}>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                startIcon={<FilterListIcon />}
                size="small"
              >
                詳細フィルター
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Paper>
      
      {/* タブ */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="すべてのサンプル" id="sample-tab-0" />
          <Tab label="バッチ管理" id="sample-tab-1" />
          <Tab label="統計" id="sample-tab-2" />
        </Tabs>
      </Box>
      
      {/* メインコンテンツ */}
      {samplesLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
          <CircularProgress />
        </Box>
      ) : samplesError ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          データの読み込みに失敗しました: {samplesError}
        </Alert>
      ) : (
        <>
          <TabPanel value={tabValue} index={0}>
            {documentList()}
          </TabPanel>
          <TabPanel value={tabValue} index={1}>
            <Alert severity="info">
              バッチデータはありません
            </Alert>
          </TabPanel>
          <TabPanel value={tabValue} index={2}>
            <Alert severity="info">
              統計データはありません
            </Alert>
          </TabPanel>
        </>
      )}
      
      {/* メニュー */}
      <Menu
        anchorEl={menuAnchorEl}
        open={Boolean(menuAnchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleMenuClose}>
          <ListItemIcon>
            <DownloadIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>ダウンロード</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <ListItemIcon>
            <ContentCopyIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>複製</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <ListItemIcon>
            <ArchiveIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>アーカイブ</ListItemText>
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleDeleteDialogOpen}>
          <ListItemIcon>
            <DeleteIcon fontSize="small" color="error" />
          </ListItemIcon>
          <ListItemText sx={{ color: 'error.main' }}>削除</ListItemText>
        </MenuItem>
      </Menu>
      
      {/* アップロードダイアログ */}
      <Dialog
        open={uploadDialogOpen}
        onClose={handleUploadDialogClose}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>サンプルの追加</DialogTitle>
        <DialogContent>
          <Box sx={{ my: 2 }}>
            <Button
              component="label"
              variant="outlined"
              startIcon={<CloudUploadIcon />}
              sx={{ mb: 2, height: 100, width: '100%' }}
            >
              ファイルをアップロード
              <input
                type="file"
                hidden
                multiple
              />
            </Button>
            
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>サンプルタイプ</InputLabel>
              <Select
                label="サンプルタイプ"
                value="contract"
              >
                <MenuItem value="contract">契約書</MenuItem>
                <MenuItem value="invoice">請求書</MenuItem>
                <MenuItem value="report">監査レポート</MenuItem>
                <MenuItem value="financial">財務報告</MenuItem>
              </Select>
            </FormControl>
            
            <TextField
              fullWidth
              label="タグ (カンマ区切り)"
              placeholder="重要, 国内, 財務..."
              sx={{ mb: 2 }}
            />
            
            <TextField
              fullWidth
              label="説明"
              multiline
              rows={3}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleUploadDialogClose}>キャンセル</Button>
          <Button variant="contained" onClick={handleUploadDialogClose}>
            アップロード
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* 削除確認ダイアログ */}
      <Dialog
        open={deleteDialogOpen}
        onClose={handleDeleteDialogClose}
      >
        <DialogTitle>サンプルの削除</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {selectedDocument && (
              <>
                サンプル "{selectedDocument.name}" を削除しますか？この操作は元に戻せません。
              </>
            )}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteDialogClose}>キャンセル</Button>
          <Button variant="contained" color="error" onClick={handleDeleteDialogClose}>
            削除
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SampleManagement;