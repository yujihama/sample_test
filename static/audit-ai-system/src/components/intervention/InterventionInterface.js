import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Tabs,
  Tab,
  Card,
  CardContent,
  CardActions,
  Button,
  TextField,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Divider,
  Badge,
  IconButton,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  AccessTime as AccessTimeIcon,
  ErrorOutline as ErrorOutlineIcon,
  CheckCircleOutline as CheckCircleOutlineIcon,
  HelpOutline as HelpOutlineIcon,
  Send as SendIcon,
  AttachFile as AttachFileIcon
} from '@mui/icons-material';
import { interventionApi } from '../../services/api';
import useApi from '../../hooks/useApi';

// サンプルデータ - 実際のアプリケーションではAPIから取得
const sampleQueries = [
  {
    id: 1,
    title: '売上計上日の確認が必要',
    description: '取引#4302のフロー検証において売上計上日が契約日と大きく異なります。適切な計上日を確認してください。',
    priority: 'high',
    category: '承認依頼',
    timestamp: '2023-03-19T10:15:30',
    status: 'pending',
    sampleId: 'SAMPLE-2023-042',
    agentId: 'agent2',
    relatedDocs: [
      { id: 'doc1', name: '売上計上基準書', url: '#' },
      { id: 'doc2', name: '契約書#4302', url: '#' }
    ]
  },
  {
    id: 2,
    title: 'リスク評価の確認',
    description: '3件の類似取引において与信限度額を超過していますが、特別承認の記録が見つかりません。これは正常な処理ですか？',
    priority: 'medium',
    category: 'ドメイン知識',
    timestamp: '2023-03-19T09:45:20',
    status: 'pending',
    sampleId: 'SAMPLE-2023-039',
    agentId: 'agent4',
    relatedDocs: [
      { id: 'doc3', name: '与信管理規程', url: '#' }
    ]
  },
  {
    id: 3,
    title: '未確認の取引相手',
    description: '新規取引先との取引ですが、取引先マスタに登録されていません。登録省略の承認はありますか？',
    priority: 'low',
    category: '例外処理',
    timestamp: '2023-03-19T11:30:00',
    status: 'pending',
    sampleId: 'SAMPLE-2023-044',
    agentId: 'agent3',
    relatedDocs: []
  },
  {
    id: 4,
    title: '承認権限の確認',
    description: '50万円超の支出承認が部長代理により行われています。この承認権限は適切ですか？',
    priority: 'high',
    category: '承認依頼',
    timestamp: '2023-03-19T08:20:10',
    status: 'resolved',
    sampleId: 'SAMPLE-2023-038',
    agentId: 'agent2',
    relatedDocs: [
      { id: 'doc4', name: '職務権限規程', url: '#' }
    ],
    response: '緊急時の特例として認められています。例外申請書の添付を確認しました。'
  }
];

// タブパネルコンポーネント
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
        <Box sx={{ py: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const InterventionInterface = () => {
  const [tabValue, setTabValue] = useState(0);
  const [selectedQuery, setSelectedQuery] = useState(null);
  const [responseText, setResponseText] = useState('');

  // 問い合わせ一覧を取得
  const { 
    data: queriesData, 
    loading: queriesLoading, 
    error: queriesError,
    refetch: refetchQueries
  } = useApi(() => interventionApi.getQueries({ status: 'all' }), []);

  // ステータスごとの問い合わせ数をカウント
  const getQueryCountByStatus = (status) => {
    if (!queriesData || !queriesData.queries) return 0;
    return queriesData.queries.filter(query => query.status === status).length;
  };

  // タブの変更を処理
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
    setSelectedQuery(null);
  };

  // 選択された問い合わせを処理
  const handleQuerySelect = (query) => {
    setSelectedQuery(query);
    setResponseText('');
  };

  // レスポンステキストの変更を処理
  const handleResponseTextChange = (e) => {
    setResponseText(e.target.value);
  };

  // レスポンス送信を処理
  const handleSendResponse = async () => {
    try {
      if (!selectedQuery || !responseText.trim()) return;
      
      await interventionApi.sendResponse(selectedQuery.id, { response: responseText });
      // 送信後にデータを再取得
      refetchQueries();
      // UIをリセット
      setResponseText('');
      setSelectedQuery(null);
    } catch (error) {
      console.error('レスポンス送信エラー:', error);
    }
  };

  // 優先度に基づく色を返す
  const getPriorityColor = (priority) => {
    switch(priority) {
      case 'high': return '#f44336';
      case 'medium': return '#ff9800';
      case 'low': return '#4caf50';
      default: return '#757575';
    }
  };

  // ステータスに基づくアイコンを返す
  const getStatusIcon = (status) => {
    switch(status) {
      case 'pending': return <HelpOutlineIcon color="warning" />;
      case 'resolved': return <CheckCircleOutlineIcon color="success" />;
      default: return <ErrorOutlineIcon color="error" />;
    }
  };

  // 空の状態かどうかをチェック
  const isEmptyState = (status) => {
    if (queriesLoading) return false;
    if (!queriesData || !queriesData.queries) return true;
    return queriesData.queries.filter(q => status === 'all' || q.status === status).length === 0;
  };

  // 現在のタブに基づいてフィルタされた問い合わせを取得
  const getFilteredQueries = () => {
    if (!queriesData || !queriesData.queries) return [];
    
    const statusMap = {
      0: 'all',
      1: 'pending',
      2: 'resolved'
    };
    
    const currentStatus = statusMap[tabValue];
    return queriesData.queries.filter(q => currentStatus === 'all' || q.status === currentStatus);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        人間介入インターフェース
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" paragraph>
        AIエージェントからの問い合わせを確認し、回答を送信します。
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ height: '100%' }}>
            <Tabs
              value={tabValue}
              onChange={handleTabChange}
              indicatorColor="primary"
              textColor="primary"
              variant="fullWidth"
            >
              <Tab 
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Typography>すべて</Typography>
                    <Badge 
                      badgeContent={getQueryCountByStatus('pending') + getQueryCountByStatus('resolved')} 
                      color="primary"
                      sx={{ ml: 1 }}
                    />
                  </Box>
                } 
              />
              <Tab 
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Typography>未回答</Typography>
                    <Badge 
                      badgeContent={getQueryCountByStatus('pending')} 
                      color="error"
                      sx={{ ml: 1 }}
                    />
                  </Box>
                } 
              />
              <Tab 
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Typography>完了</Typography>
                    <Badge 
                      badgeContent={getQueryCountByStatus('resolved')} 
                      color="success"
                      sx={{ ml: 1 }}
                    />
                  </Box>
                } 
              />
            </Tabs>

            <Box sx={{ height: 'calc(100vh - 270px)', overflow: 'auto' }}>
              <TabPanel value={tabValue} index={0}>
                {queriesLoading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                    <CircularProgress />
                  </Box>
                ) : queriesError ? (
                  <Alert severity="error">
                    問い合わせの読み込み中にエラーが発生しました。
                  </Alert>
                ) : isEmptyState('all') ? (
                  <Box sx={{ textAlign: 'center', p: 4 }}>
                    <HelpOutlineIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      表示する問い合わせがありません
                    </Typography>
                  </Box>
                ) : (
                  <List>
                    {getFilteredQueries().map((query) => (
                      <ListItem 
                        key={query.id} 
                        button 
                        selected={selectedQuery && selectedQuery.id === query.id}
                        onClick={() => handleQuerySelect(query)}
                        sx={{ 
                          borderLeft: `4px solid ${getPriorityColor(query.priority)}`,
                          backgroundColor: selectedQuery && selectedQuery.id === query.id ? 'rgba(0, 0, 0, 0.04)' : 'transparent',
                          mb: 1
                        }}
                      >
                        <ListItemAvatar>
                          <Avatar>
                            {getStatusIcon(query.status)}
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={
                            <Typography noWrap variant="subtitle2">
                              {query.title}
                            </Typography>
                          }
                          secondary={
                            <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
                              <AccessTimeIcon fontSize="small" sx={{ mr: 0.5, fontSize: 16, color: 'text.secondary' }} />
                              <Typography variant="caption" color="text.secondary">
                                {new Date(query.timestamp).toLocaleString()}
                              </Typography>
                            </Box>
                          }
                        />
                      </ListItem>
                    ))}
                  </List>
                )}
              </TabPanel>
              
              <TabPanel value={tabValue} index={1}>
                {queriesLoading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                    <CircularProgress />
                  </Box>
                ) : queriesError ? (
                  <Alert severity="error">
                    問い合わせの読み込み中にエラーが発生しました。
                  </Alert>
                ) : isEmptyState('pending') ? (
                  <Box sx={{ textAlign: 'center', p: 4 }}>
                    <CheckCircleOutlineIcon sx={{ fontSize: 48, color: 'success.main', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      未回答の問い合わせはありません
                    </Typography>
                  </Box>
                ) : (
                  <List>
                    {getFilteredQueries().map((query) => (
                      <ListItem 
                        key={query.id} 
                        button 
                        selected={selectedQuery && selectedQuery.id === query.id}
                        onClick={() => handleQuerySelect(query)}
                        sx={{ 
                          borderLeft: `4px solid ${getPriorityColor(query.priority)}`,
                          backgroundColor: selectedQuery && selectedQuery.id === query.id ? 'rgba(0, 0, 0, 0.04)' : 'transparent',
                          mb: 1
                        }}
                      >
                        <ListItemAvatar>
                          <Avatar>
                            {getStatusIcon(query.status)}
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={
                            <Typography noWrap variant="subtitle2">
                              {query.title}
                            </Typography>
                          }
                          secondary={
                            <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
                              <AccessTimeIcon fontSize="small" sx={{ mr: 0.5, fontSize: 16, color: 'text.secondary' }} />
                              <Typography variant="caption" color="text.secondary">
                                {new Date(query.timestamp).toLocaleString()}
                              </Typography>
                            </Box>
                          }
                        />
                      </ListItem>
                    ))}
                  </List>
                )}
              </TabPanel>
              
              <TabPanel value={tabValue} index={2}>
                {queriesLoading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                    <CircularProgress />
                  </Box>
                ) : queriesError ? (
                  <Alert severity="error">
                    問い合わせの読み込み中にエラーが発生しました。
                  </Alert>
                ) : isEmptyState('resolved') ? (
                  <Box sx={{ textAlign: 'center', p: 4 }}>
                    <HelpOutlineIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      完了した問い合わせはありません
                    </Typography>
                  </Box>
                ) : (
                  <List>
                    {getFilteredQueries().map((query) => (
                      <ListItem 
                        key={query.id} 
                        button 
                        selected={selectedQuery && selectedQuery.id === query.id}
                        onClick={() => handleQuerySelect(query)}
                        sx={{ 
                          borderLeft: `4px solid ${getPriorityColor(query.priority)}`,
                          backgroundColor: selectedQuery && selectedQuery.id === query.id ? 'rgba(0, 0, 0, 0.04)' : 'transparent',
                          mb: 1
                        }}
                      >
                        <ListItemAvatar>
                          <Avatar>
                            {getStatusIcon(query.status)}
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={
                            <Typography noWrap variant="subtitle2">
                              {query.title}
                            </Typography>
                          }
                          secondary={
                            <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
                              <AccessTimeIcon fontSize="small" sx={{ mr: 0.5, fontSize: 16, color: 'text.secondary' }} />
                              <Typography variant="caption" color="text.secondary">
                                {new Date(query.timestamp).toLocaleString()}
                              </Typography>
                            </Box>
                          }
                        />
                      </ListItem>
                    ))}
                  </List>
                )}
              </TabPanel>
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={8}>
          <Paper sx={{ height: '100%', p: 3 }}>
            {!selectedQuery ? (
              <Box sx={{ 
                height: 'calc(100vh - 270px)', 
                display: 'flex', 
                flexDirection: 'column', 
                justifyContent: 'center', 
                alignItems: 'center' 
              }}>
                <HelpOutlineIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" color="text.secondary">
                  左側のリストから問い合わせを選択してください
                </Typography>
              </Box>
            ) : (
              <Box sx={{ height: 'calc(100vh - 270px)', display: 'flex', flexDirection: 'column' }}>
                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Chip 
                      label={selectedQuery.category} 
                      size="small" 
                      sx={{ mr: 1 }} 
                    />
                    <Chip 
                      label={selectedQuery.priority === 'high' ? '高優先度' : selectedQuery.priority === 'medium' ? '中優先度' : '低優先度'} 
                      size="small"
                      sx={{ 
                        bgcolor: getPriorityColor(selectedQuery.priority),
                        color: 'white',
                        mr: 1 
                      }} 
                    />
                    <Typography variant="caption" color="text.secondary">
                      ID: {selectedQuery.sampleId}
                    </Typography>
                  </Box>
                  <Typography variant="h5" gutterBottom>
                    {selectedQuery.title}
                  </Typography>
                  <Typography variant="body1" paragraph>
                    {selectedQuery.description}
                  </Typography>
                </Box>
                
                {selectedQuery.relatedDocs && selectedQuery.relatedDocs.length > 0 && (
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      関連ドキュメント
                    </Typography>
                    <Grid container spacing={1}>
                      {selectedQuery.relatedDocs.map(doc => (
                        <Grid item key={doc.id}>
                          <Chip
                            label={doc.name}
                            component="a"
                            href={doc.url}
                            clickable
                            size="small"
                            variant="outlined"
                          />
                        </Grid>
                      ))}
                    </Grid>
                  </Box>
                )}
                
                <Divider sx={{ my: 2 }} />
                
                {selectedQuery.status === 'resolved' ? (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      回答
                    </Typography>
                    <Card variant="outlined">
                      <CardContent sx={{ backgroundColor: 'rgba(0, 0, 0, 0.03)' }}>
                        <Typography variant="body1">
                          {selectedQuery.response}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Box>
                ) : (
                  <Box sx={{ mt: 'auto' }}>
                    <TextField
                      label="回答を入力"
                      multiline
                      rows={4}
                      fullWidth
                      variant="outlined"
                      value={responseText}
                      onChange={handleResponseTextChange}
                      sx={{ mb: 2 }}
                    />
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Button
                        variant="outlined"
                        startIcon={<AttachFileIcon />}
                      >
                        添付ファイル
                      </Button>
                      <Button
                        variant="contained"
                        color="primary"
                        endIcon={<SendIcon />}
                        disabled={!responseText.trim()}
                        onClick={handleSendResponse}
                      >
                        送信
                      </Button>
                    </Box>
                  </Box>
                )}
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default InterventionInterface; 