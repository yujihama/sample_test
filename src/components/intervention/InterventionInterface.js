import React, { useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CardHeader,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Button,
  TextField,
  Paper,
  Chip,
  Tab,
  Tabs,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Avatar,
  Badge,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  QuestionAnswer as QuestionAnswerIcon,
  Send as SendIcon,
  AttachFile as AttachFileIcon,
  Assignment as AssignmentIcon,
  History as HistoryIcon,
  SearchOutlined as SearchOutlinedIcon,
  Reply as ReplyIcon,
  Close as CloseIcon,
  Save as SaveIcon,
  AssignmentTurnedIn as AssignmentTurnedInIcon,
  Book as BookIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';

// APIサービスとカスタムフックをインポート
import { interventionApi } from '../../frontend/services/api';
import useApi from '../../frontend/hooks/useApi';

// タブパネルのコンポーネント
function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`intervention-tabpanel-${index}`}
      aria-labelledby={`intervention-tab-${index}`}
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

const InterventionInterface = () => {
  // タブの状態
  const [tabValue, setTabValue] = useState(0);
  
  // 選択中の問い合わせ
  const [selectedInquiry, setSelectedInquiry] = useState(null);
  
  // 返信内容
  const [response, setResponse] = useState('');
  
  // テンプレートダイアログの状態
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false);
  
  // APIから介入リクエスト一覧を取得
  const { 
    data: queriesData, 
    loading: queriesLoading, 
    error: queriesError,
    refetch: refetchQueries
  } = useApi(() => interventionApi.getQueriesWithFilter('all'), {
    dependencies: []
  });
  
  // 介入リクエストデータを取得
  const getQueries = () => {
    if (!queriesData || !queriesData.queries) return [];
    return queriesData.queries;
  };
  
  // タブ変更ハンドラ
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };
  
  // 問い合わせ選択ハンドラ
  const handleInquirySelect = (inquiry) => {
    setSelectedInquiry(inquiry);
    setResponse('');
  };
  
  // テンプレートダイアログを開く
  const handleOpenTemplateDialog = () => {
    setTemplateDialogOpen(true);
  };
  
  // テンプレートダイアログを閉じる
  const handleCloseTemplateDialog = () => {
    setTemplateDialogOpen(false);
  };
  
  // テンプレート適用
  const applyTemplate = (template) => {
    setResponse(template);
    handleCloseTemplateDialog();
  };
  
  // 回答内容変更ハンドラ
  const handleResponseChange = (event) => {
    setResponse(event.target.value);
  };
  
  // 回答送信ハンドラ
  const handleSubmitResponse = () => {
    if (!selectedInquiry || !response.trim()) return;
    
    // APIを呼び出して回答を送信
    interventionApi.respondToQuery(selectedInquiry.id, {
      response: response.trim()
    }).then(() => {
      // 送信成功後の処理
      refetchQueries();
      setSelectedInquiry(null);
      setResponse('');
    });
  };
  
  // すべてのデータを更新
  const refreshData = () => {
    refetchQueries();
  };
  
  // 回答テンプレート（実際は外部から取得）
  const responseTemplates = [
    { 
      id: 1, 
      title: '承認',
      content: '承認します。処理を続行してください。' 
    },
    { 
      id: 2, 
      title: '条件付き承認',
      content: '条件付きで承認します。以下の点に注意して処理を続行してください：\n\n1. 承認者の記録を残すこと\n2. 例外処理として記録すること' 
    },
    { 
      id: 3, 
      title: '拒否',
      content: '拒否します。以下の理由により処理を中止してください：\n\n理由：' 
    },
    { 
      id: 4, 
      title: '追加情報リクエスト',
      content: '判断するためにさらに情報が必要です。以下の情報を提供してください：\n\n1. \n2. ' 
    }
  ];
  
  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" gutterBottom sx={{ flexGrow: 1 }}>
          人間介入インターフェース
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={refreshData}
          sx={{ ml: 2 }}
        >
          更新
        </Button>
      </Box>
      
      <Grid container spacing={3}>
        {/* 左サイドパネル：問い合わせ一覧 */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardHeader 
              title="問い合わせリスト" 
              action={
                <Badge badgeContent={getQueries().filter(q => q.status === 'pending').length} color="error">
                  <QuestionAnswerIcon />
                </Badge>
              }
            />
            <Divider />
            <CardContent sx={{ p: 0 }}>
              <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={tabValue} onChange={handleTabChange} variant="fullWidth">
                  <Tab label="保留中" id="intervention-tab-0" aria-controls="intervention-tabpanel-0" />
                  <Tab label="完了済" id="intervention-tab-1" aria-controls="intervention-tabpanel-1" />
                  <Tab label="すべて" id="intervention-tab-2" aria-controls="intervention-tabpanel-2" />
                </Tabs>
              </Box>

              {queriesLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
                  <CircularProgress />
                </Box>
              ) : queriesError ? (
                <Alert severity="error" sx={{ m: 2 }}>
                  データの読み込みに失敗しました: {queriesError}
                </Alert>
              ) : getQueries().length === 0 ? (
                <Alert severity="info" sx={{ m: 2 }}>
                  問い合わせはありません
                </Alert>
              ) : (
                <>
                  <TabPanel value={tabValue} index={0}>
                    <Alert severity="info" sx={{ mb: 2 }}>
                      データはありますが、表示するデータがありません
                    </Alert>
                  </TabPanel>
                  <TabPanel value={tabValue} index={1}>
                    <Alert severity="info" sx={{ mb: 2 }}>
                      データはありますが、表示するデータがありません
                    </Alert>
                  </TabPanel>
                  <TabPanel value={tabValue} index={2}>
                    <Alert severity="info" sx={{ mb: 2 }}>
                      データはありますが、表示するデータがありません
                    </Alert>
                  </TabPanel>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>
        
        {/* 右サイドパネル：詳細と返答 */}
        <Grid item xs={12} md={8}>
          {selectedInquiry ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Card>
                  <CardHeader 
                    title="問い合わせ詳細" 
                    action={
                      <IconButton onClick={() => setSelectedInquiry(null)}>
                        <CloseIcon />
                      </IconButton>
                    }
                  />
                  <Divider />
                  <CardContent>
                    <Typography variant="body1">
                      データはありますが、表示するデータがありません
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              
              <Grid item xs={12}>
                <Card>
                  <CardHeader title="回答" />
                  <Divider />
                  <CardContent>
                    <TextField
                      fullWidth
                      label="回答内容"
                      multiline
                      rows={6}
                      value={response}
                      onChange={handleResponseChange}
                      placeholder="エージェントへの回答を入力してください..."
                      variant="outlined"
                      sx={{ mb: 2 }}
                    />
                    
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Button 
                        variant="outlined" 
                        startIcon={<BookIcon />}
                        onClick={handleOpenTemplateDialog}
                      >
                        テンプレート
                      </Button>
                      <Button 
                        variant="contained" 
                        startIcon={<SendIcon />}
                        onClick={handleSubmitResponse}
                        disabled={!response.trim()}
                      >
                        送信
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          ) : (
            <Card>
              <CardHeader title="介入待ちタスク" />
              <Divider />
              <CardContent sx={{ p: 0 }}>
                {queriesLoading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
                    <CircularProgress />
                  </Box>
                ) : queriesError ? (
                  <Alert severity="error" sx={{ m: 2 }}>
                    データの読み込みに失敗しました: {queriesError}
                  </Alert>
                ) : getQueries().length === 0 ? (
                  <Box sx={{ p: 3, textAlign: 'center' }}>
                    <Typography variant="h6" color="textSecondary" gutterBottom>
                      介入待ちのタスクはありません
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      AIエージェントは現在すべてのタスクを自律的に処理しています。
                      介入が必要になった場合はここに表示されます。
                    </Typography>
                  </Box>
                ) : (
                  <Grid container spacing={3} sx={{ p: 3 }}>
                    <Alert severity="info" sx={{ width: '100%' }}>
                      データはありますが、表示するデータがありません
                    </Alert>
                  </Grid>
                )}
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
      
      {/* テンプレート選択ダイアログ */}
      <Dialog
        open={templateDialogOpen}
        onClose={handleCloseTemplateDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>回答テンプレートを選択</DialogTitle>
        <DialogContent>
          <List>
            {responseTemplates.map((template) => (
              <ListItem 
                button 
                key={template.id} 
                onClick={() => applyTemplate(template.content)}
              >
                <ListItemIcon>
                  <AssignmentIcon />
                </ListItemIcon>
                <ListItemText 
                  primary={template.title} 
                  secondary={template.content.substring(0, 50) + '...'}
                />
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseTemplateDialog}>キャンセル</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default InterventionInterface; 