import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Tabs,
  Tab,
  TextField,
  Button,
  FormControl,
  FormControlLabel,
  FormGroup,
  FormLabel,
  Switch,
  Slider,
  Select,
  MenuItem,
  InputLabel,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Card,
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip
} from '@mui/material';
import {
  Save as SaveIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  Settings as SettingsIcon,
  Security as SecurityIcon,
  Build as BuildIcon
} from '@mui/icons-material';

// タブパネルコンポーネント
function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
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

// エージェント設定データ（サンプル）
const agentSettingsData = [
  {
    id: 'agent1',
    name: '検証エージェント',
    type: 'validator',
    status: 'active',
    confidence: 75,
    permissions: ['read_documents', 'validate_records', 'request_human_input'],
    settings: {
      thresholdScore: 0.8,
      maxRetries: 3,
      timeoutSeconds: 30
    }
  },
  {
    id: 'agent2',
    name: '監査チェックエージェント',
    type: 'auditor',
    status: 'active',
    confidence: 85,
    permissions: ['read_documents', 'analyze_patterns', 'generate_reports'],
    settings: {
      thresholdScore: 0.75,
      maxRetries: 2,
      timeoutSeconds: 60
    }
  },
  {
    id: 'agent3',
    name: '証拠収集エージェント',
    type: 'collector',
    status: 'active',
    confidence: 90,
    permissions: ['read_documents', 'access_databases', 'collect_evidence'],
    settings: {
      thresholdScore: 0.7,
      maxRetries: 5,
      timeoutSeconds: 45
    }
  }
];

const SystemSettings = () => {
  const [tabValue, setTabValue] = useState(0);
  const [editAgentDialog, setEditAgentDialog] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [thresholdValue, setThresholdValue] = useState(0.8);

  // タブ変更ハンドラ
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // エージェント編集ダイアログを開く
  const handleOpenEditDialog = (agent) => {
    setSelectedAgent(agent);
    setThresholdValue(agent.settings.thresholdScore);
    setEditAgentDialog(true);
  };

  // エージェント編集ダイアログを閉じる
  const handleCloseEditDialog = () => {
    setEditAgentDialog(false);
  };

  // しきい値変更ハンドラ
  const handleThresholdChange = (event, newValue) => {
    setThresholdValue(newValue);
  };

  // ステータスに基づく色を返す関数
  const getStatusColor = (status) => {
    switch(status) {
      case 'active': return '#4caf50';
      case 'inactive': return '#9e9e9e';
      case 'connected': return '#4caf50';
      case 'disconnected': return '#9e9e9e';
      case 'error': return '#f44336';
      default: return '#757575';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        システム設定
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" paragraph>
        AIエージェントの設定、ワークフローのカスタマイズを管理します。
      </Typography>

      <Paper sx={{ width: '100%' }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="scrollable"
          scrollButtons="auto"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab icon={<SettingsIcon />} label="エージェント設定" />
          <Tab icon={<BuildIcon />} label="ワークフロー" />
        </Tabs>

        {/* エージェント設定タブ */}
        <TabPanel value={tabValue} index={0}>
          <Alert severity="info" sx={{ mb: 3 }}>
            各AIエージェントの役割、権限、判断基準を設定します。変更後はシステムの再起動が必要な場合があります。
          </Alert>

          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
                <Button 
                  variant="contained" 
                  color="primary" 
                  startIcon={<AddIcon />}
                >
                  新規エージェント追加
                </Button>
              </Box>

              {agentSettingsData.map((agent) => (
                <Accordion key={agent.id} sx={{ mb: 2 }}>
                  <AccordionSummary
                    expandIcon={<ExpandMoreIcon />}
                    sx={{ 
                      '&.Mui-expanded': {
                        borderBottom: '1px solid rgba(0, 0, 0, 0.12)'
                      }
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                      <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
                        {agent.name}
                      </Typography>
                      <Typography 
                        variant="caption" 
                        sx={{ 
                          color: getStatusColor(agent.status),
                          fontWeight: 'bold',
                          mr: 2
                        }}
                      >
                        {agent.status === 'active' ? '有効' : '無効'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        タイプ: {agent.type}
                      </Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={3}>
                      <Grid item xs={12} md={6}>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="h6" gutterBottom>
                              基本設定
                            </Typography>
                            <Grid container spacing={2}>
                              <Grid item xs={12}>
                                <TextField
                                  label="エージェント名"
                                  variant="outlined"
                                  fullWidth
                                  size="small"
                                  defaultValue={agent.name}
                                />
                              </Grid>
                              <Grid item xs={12} sm={6}>
                                <FormControl fullWidth size="small">
                                  <InputLabel>タイプ</InputLabel>
                                  <Select
                                    value={agent.type}
                                    label="タイプ"
                                  >
                                    <MenuItem value="validator">検証</MenuItem>
                                    <MenuItem value="auditor">監査</MenuItem>
                                    <MenuItem value="collector">収集</MenuItem>
                                    <MenuItem value="analyzer">分析</MenuItem>
                                  </Select>
                                </FormControl>
                              </Grid>
                              <Grid item xs={12} sm={6}>
                                <FormControl fullWidth size="small">
                                  <InputLabel>ステータス</InputLabel>
                                  <Select
                                    value={agent.status}
                                    label="ステータス"
                                  >
                                    <MenuItem value="active">有効</MenuItem>
                                    <MenuItem value="inactive">無効</MenuItem>
                                  </Select>
                                </FormControl>
                              </Grid>
                            </Grid>
                          </CardContent>
                        </Card>
                      </Grid>

                      <Grid item xs={12} md={6}>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="h6" gutterBottom>
                              判断パラメータ
                            </Typography>
                            <Box sx={{ px: 1 }}>
                              <Typography variant="body2" gutterBottom>
                                信頼度しきい値: {agent.settings.thresholdScore}
                              </Typography>
                              <Slider
                                defaultValue={agent.settings.thresholdScore}
                                step={0.05}
                                min={0}
                                max={1}
                                valueLabelDisplay="auto"
                                sx={{ mb: 2 }}
                              />

                              <Grid container spacing={2}>
                                <Grid item xs={12} sm={6}>
                                  <TextField
                                    label="最大リトライ回数"
                                    variant="outlined"
                                    fullWidth
                                    size="small"
                                    type="number"
                                    defaultValue={agent.settings.maxRetries}
                                  />
                                </Grid>
                                <Grid item xs={12} sm={6}>
                                  <TextField
                                    label="タイムアウト(秒)"
                                    variant="outlined"
                                    fullWidth
                                    size="small"
                                    type="number"
                                    defaultValue={agent.settings.timeoutSeconds}
                                  />
                                </Grid>
                              </Grid>
                            </Box>
                          </CardContent>
                        </Card>
                      </Grid>

                      <Grid item xs={12}>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="h6" gutterBottom>
                              権限設定
                            </Typography>
                            <FormGroup row>
                              <FormControlLabel 
                                control={<Switch checked={agent.permissions.includes('read_documents')} />} 
                                label="ドキュメント読取" 
                              />
                              <FormControlLabel 
                                control={<Switch checked={agent.permissions.includes('validate_records')} />} 
                                label="記録検証" 
                              />
                              <FormControlLabel 
                                control={<Switch checked={agent.permissions.includes('access_databases')} />} 
                                label="データベースアクセス" 
                              />
                              <FormControlLabel 
                                control={<Switch checked={agent.permissions.includes('request_human_input')} />} 
                                label="人間への問い合わせ" 
                              />
                              <FormControlLabel 
                                control={<Switch checked={agent.permissions.includes('generate_reports')} />} 
                                label="レポート生成" 
                              />
                            </FormGroup>
                          </CardContent>
                        </Card>
                      </Grid>
                    </Grid>
                    
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
                      <Button 
                        variant="outlined" 
                        color="error" 
                        startIcon={<DeleteIcon />}
                        sx={{ mr: 1 }}
                      >
                        削除
                      </Button>
                      <Button 
                        variant="contained" 
                        color="primary" 
                        startIcon={<SaveIcon />}
                        onClick={() => handleOpenEditDialog(agent)}
                      >
                        保存
                      </Button>
                    </Box>
                  </AccordionDetails>
                </Accordion>
              ))}
            </Grid>
          </Grid>
        </TabPanel>

        {/* ワークフロータブ */}
        <TabPanel value={tabValue} index={1}>
          <Alert severity="warning" sx={{ mb: 3 }}>
            ワークフロー設定の変更は、現在進行中の処理に影響を与える可能性があります。変更前に全ての処理が完了していることを確認してください。
          </Alert>
          
          <Box sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary">
              ワークフロー設計機能は準備中です
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              将来のアップデートで、視覚的なワークフローデザイナーが追加される予定です。
            </Typography>
          </Box>
        </TabPanel>
      </Paper>

      {/* エージェント編集ダイアログ */}
      <Dialog
        open={editAgentDialog}
        onClose={handleCloseEditDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          エージェント設定の編集
        </DialogTitle>
        <DialogContent dividers>
          {selectedAgent && (
            <Box sx={{ p: 1 }}>
              <Typography variant="subtitle1" gutterBottom>
                {selectedAgent.name}の信頼度しきい値を調整
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                高い値に設定すると、よりシステムの判断に確信がある場合のみアクションを実行します。
                低い値に設定すると、より多くのアクションを実行しますが、誤検出のリスクが高まります。
              </Typography>
              <Box sx={{ px: 2, py: 1 }}>
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs>
                    <Slider
                      value={thresholdValue}
                      onChange={handleThresholdChange}
                      min={0}
                      max={1}
                      step={0.01}
                      marks={[
                        { value: 0, label: '0' },
                        { value: 0.5, label: '0.5' },
                        { value: 1, label: '1' },
                      ]}
                      valueLabelDisplay="on"
                    />
                  </Grid>
                </Grid>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseEditDialog}>キャンセル</Button>
          <Button 
            variant="contained" 
            color="primary" 
            onClick={handleCloseEditDialog}
          >
            保存
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SystemSettings; 