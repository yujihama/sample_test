import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardHeader,
  Divider,
  Grid,
  Button,
  TextField,
  FormControl,
  FormLabel,
  FormGroup,
  FormControlLabel,
  Select,
  MenuItem,
  InputLabel,
  Switch,
  Slider,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Alert,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Paper,
  Tooltip,
  Snackbar,
  CircularProgress,
  TableContainer,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell
} from '@mui/material';
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  ExpandMore as ExpandMoreIcon,
  Build as BuildIcon,
  Security as SecurityIcon,
  Storage as StorageIcon,
  Language as LanguageIcon,
  Notifications as NotificationsIcon,
  PersonAdd as PersonAddIcon,
  Tune as TuneIcon,
  CloudUpload as CloudUploadIcon,
  Help as HelpIcon,
  VpnKey as VpnKeyIcon,
  Settings as SettingsIcon,
  Link as LinkIcon,
  Check as CheckIcon,
  Warning as WarningIcon,
  Api as ApiIcon,
  Code as CodeIcon,
  AccountTree as AccountTreeIcon,
  DeveloperBoard as DeveloperBoardIcon,
  Person as PersonIcon,
  BugReport as BugReportIcon,
  Backup as BackupIcon,
  History as HistoryIcon,
  Sync as SyncIcon,
  Close as CloseIcon
} from '@mui/icons-material';

// APIサービスとカスタムフックをインポート
import { settingsApi } from '../../frontend/services/api.js';
import useApi from '../../frontend/hooks/useApi';

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
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const SystemSettings = () => {
  const [tabValue, setTabValue] = useState(0);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [editAgentDialogOpen, setEditAgentDialogOpen] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  
  // APIからデータを取得
  const { 
    data: agentSettingsData, 
    loading: agentSettingsLoading 
  } = useApi(() => settingsApi.getAgentSettings(), {
    dependencies: []
  });
  
  const { 
    data: workflowSettingsData, 
    loading: workflowSettingsLoading 
  } = useApi(() => settingsApi.getWorkflowSettings(), {
    dependencies: []
  });
  
  const { 
    data: systemInfoData, 
    loading: systemInfoLoading 
  } = useApi(() => settingsApi.getSystemInfo(), {
    dependencies: []
  });
  
  // タブ変更ハンドラー
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };
  
  // エージェント選択ハンドラー
  const handleAgentSelect = (agent) => {
    setSelectedAgent(agent);
    setEditAgentDialogOpen(true);
  };
  
  // ダイアログを閉じるハンドラー
  const handleCloseDialog = () => {
    setEditAgentDialogOpen(false);
  };
  
  // 設定保存ハンドラー
  const handleSaveSettings = async () => {
    setSnackbarMessage('設定が正常に保存されました');
    setSnackbarOpen(true);
  };
  
  // スナックバーを閉じるハンドラー
  const handleCloseSnackbar = () => {
    setSnackbarOpen(false);
  };
  
  // エージェント設定コンポーネント
  const renderAgentSettings = () => (
    <Card elevation={2}>
      <CardHeader 
        title="エージェント設定" 
        action={
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            size="small"
          >
            新規エージェント
          </Button>
        }
      />
      <Divider />
      <CardContent>
        {agentSettingsLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <CircularProgress />
          </Box>
        ) : agentSettingsData?.success && agentSettingsData?.data?.agents && agentSettingsData.data.agents.length > 0 ? (
          <List>
            {agentSettingsData.data.agents.map((agent) => (
              <React.Fragment key={agent.id}>
                <ListItem
                  secondaryAction={
                    <Box>
                      <IconButton 
                        edge="end" 
                        aria-label="edit"
                        onClick={() => handleAgentSelect(agent)}
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton edge="end" aria-label="delete">
                        <DeleteIcon />
                      </IconButton>
                    </Box>
                  }
                >
                  <ListItemIcon>
                    <PersonIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        {agent.name}
                        <Chip 
                          size="small" 
                          label={agent.status === 'active' ? '有効' : '無効'} 
                          color={agent.status === 'active' ? 'success' : 'default'}
                          sx={{ ml: 1 }}
                        />
                      </Box>
                    }
                    secondary={`役割: ${agent.role} | バージョン: ${agent.version} | 最終更新: ${new Date(agent.lastModified).toLocaleDateString()}`}
                  />
                </ListItem>
                <Divider variant="inset" component="li" />
              </React.Fragment>
            ))}
          </List>
        ) : (
          <Alert severity="info">
            エージェント設定データはありません。
          </Alert>
        )}
      </CardContent>
    </Card>
  );
  
  // ワークフロー設定コンポーネント
  const renderWorkflowSettings = () => (
    <Card elevation={2}>
      <CardHeader 
        title="ワークフロー設定" 
        action={
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            size="small"
          >
            新規ワークフロー
          </Button>
        }
      />
      <Divider />
      <CardContent>
        {workflowSettingsLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <CircularProgress />
          </Box>
        ) : workflowSettingsData?.success && workflowSettingsData?.data?.workflows && workflowSettingsData.data.workflows.length > 0 ? (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>名前</TableCell>
                  <TableCell>ステータス</TableCell>
                  <TableCell>エージェント数</TableCell>
                  <TableCell>ステップ数</TableCell>
                  <TableCell>最終更新</TableCell>
                  <TableCell>アクション</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {workflowSettingsData.data.workflows.map((workflow) => (
                  <TableRow key={workflow.id}>
                    <TableCell>{workflow.name}</TableCell>
                    <TableCell>{workflow.status === 'active' ? '有効' : '無効'}</TableCell>
                    <TableCell>{workflow.agents.length}</TableCell>
                    <TableCell>{workflow.steps}</TableCell>
                    <TableCell>{new Date(workflow.lastModified).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <IconButton
                          edge="end"
                          aria-label="edit"
                          onClick={() => handleAgentSelect(workflow)}
                        >
                          <EditIcon />
                        </IconButton>
                        <IconButton
                          edge="end"
                          aria-label="delete"
                          color="error"
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Alert severity="info">
            ワークフロー設定データはありません。
          </Alert>
        )}
      </CardContent>
    </Card>
  );
  
  // システム情報コンポーネント
  const renderSystemInfo = () => (
    <Card elevation={2}>
      <CardHeader title="システム情報" />
      <Divider />
      <CardContent>
        {systemInfoLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <CircularProgress />
          </Box>
        ) : systemInfoData?.success && systemInfoData?.data?.systemInfo ? (
          <List>
            <ListItem>
              <ListItemIcon>
                <ApiIcon />
              </ListItemIcon>
              <ListItemText 
                primary="システム名"
                secondary={systemInfoData.data.systemInfo.name}
              />
            </ListItem>
            <ListItem>
              <ListItemIcon>
                <CodeIcon />
              </ListItemIcon>
              <ListItemText 
                primary="バージョン"
                secondary={systemInfoData.data.systemInfo.version}
              />
            </ListItem>
            <ListItem>
              <ListItemIcon>
                <BuildIcon />
              </ListItemIcon>
              <ListItemText 
                primary="環境"
                secondary={systemInfoData.data.systemInfo.environment}
              />
            </ListItem>
            <ListItem>
              <ListItemIcon>
                <StorageIcon />
              </ListItemIcon>
              <ListItemText 
                primary="データベース"
                secondary={systemInfoData.data.systemInfo.database}
              />
            </ListItem>
            <ListItem>
              <ListItemIcon>
                <DeveloperBoardIcon />
              </ListItemIcon>
              <ListItemText 
                primary="サーバーOS"
                secondary={systemInfoData.data.systemInfo.serverOS}
              />
            </ListItem>
            <ListItem>
              <ListItemIcon>
                <SyncIcon />
              </ListItemIcon>
              <ListItemText 
                primary="ステータス"
                secondary={
                  <Chip 
                    label={systemInfoData.data.systemInfo.status === 'running' ? '稼働中' : '停止中'} 
                    color={systemInfoData.data.systemInfo.status === 'running' ? 'success' : 'error'}
                    size="small"
                  />
                }
              />
            </ListItem>
            <ListItem>
              <ListItemIcon>
                <HistoryIcon />
              </ListItemIcon>
              <ListItemText 
                primary="最終更新"
                secondary={new Date(systemInfoData.data.systemInfo.lastUpdated).toLocaleString()}
              />
            </ListItem>
          </List>
        ) : (
          <Alert severity="info">
            システム情報を読み込めませんでした。
          </Alert>
        )}
      </CardContent>
    </Card>
  );

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" gutterBottom sx={{ flexGrow: 1 }}>
          システム設定
        </Typography>
        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={handleSaveSettings}
        >
          設定を保存
        </Button>
      </Box>
      
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="エージェント" icon={<PersonIcon />} id="settings-tab-0" />
          <Tab label="ワークフロー" icon={<SyncIcon />} id="settings-tab-1" />
          <Tab label="システム情報" icon={<StorageIcon />} id="settings-tab-2" />
        </Tabs>
      </Box>
      
      <TabPanel value={tabValue} index={0}>
        {renderAgentSettings()}
      </TabPanel>
      <TabPanel value={tabValue} index={1}>
        {renderWorkflowSettings()}
      </TabPanel>
      <TabPanel value={tabValue} index={2}>
        {renderSystemInfo()}
      </TabPanel>
      
      {/* 保存完了通知 */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        message={snackbarMessage}
        action={
          <IconButton
            size="small"
            color="inherit"
            onClick={handleCloseSnackbar}
          >
            <CloseIcon />
          </IconButton>
        }
      />
      
      {/* エージェント編集ダイアログ */}
      {selectedAgent && (
        <Dialog open={editAgentDialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
          <DialogTitle>
            エージェント編集: {selectedAgent.name}
          </DialogTitle>
          <DialogContent dividers>
            {/* エージェント編集フォーム */}
            {/* ... */}
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseDialog}>キャンセル</Button>
            <Button variant="contained" color="primary">保存</Button>
          </DialogActions>
        </Dialog>
      )}
    </Box>
  );
};

export default SystemSettings; 