import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  Grid, 
  Card, 
  CardContent,
  Slider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Divider,
  Alert,
  CircularProgress
} from '@mui/material';
import ForceGraph2D from 'react-force-graph-2d';
import { agentApi } from '../../services/api';
import useApi from '../../hooks/useApi';

const AgentVisualizer = () => {
  const [timeRange, setTimeRange] = useState([0, 100]);
  const [selectedAgent, setSelectedAgent] = useState('all');

  // APIからエージェント一覧データを取得
  const { 
    data: agentData, 
    loading: agentLoading, 
    error: agentError,
    refetch: refetchAgents
  } = useApi(agentApi.getAgents, []);

  // APIからエージェント間のメッセージフローを取得
  const { 
    data: flowData, 
    loading: flowLoading, 
    error: flowError,
    refetch: refetchFlow
  } = useApi(agentApi.getMessageFlow, []);

  // タイムスライダー変更ハンドラ
  const handleTimeRangeChange = (event, newValue) => {
    setTimeRange(newValue);
    // 実際のアプリケーションでは、ここでグラフデータをフィルタリングします
  };

  // エージェント選択ハンドラ
  const handleAgentChange = (event) => {
    setSelectedAgent(event.target.value);
    // 実際のアプリケーションでは、ここでグラフデータをフィルタリングします
  };

  // メッセージステータスに基づく色を返す関数
  const getStatusColor = (status) => {
    switch(status) {
      case 'success': return '#4caf50';
      case 'warning': return '#ff9800';
      case 'danger': return '#f44336';
      case 'info': return '#2196f3';
      default: return '#757575';
    }
  };

  // グラフデータを準備
  const graphData = flowData && flowData.success === true ? {
    nodes: flowData.data.nodes || [],
    links: flowData.data.links || []
  } : flowData && {
    nodes: flowData.nodes || [],
    links: flowData.links || []
  };

  // メッセージデータを準備
  const messages = flowData && flowData.success === true && flowData.data.messages ? 
    flowData.data.messages : 
    (flowData && flowData.messages ? flowData.messages : []);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        エージェント通信ビジュアライザー
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" paragraph>
        AIエージェント間の通信フローをリアルタイムで可視化します。
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper 
            sx={{ 
              p: 2, 
              height: 600, 
              display: 'flex', 
              flexDirection: 'column'
            }}
          >
            <Typography variant="h6" gutterBottom>
              エージェントネットワーク
            </Typography>
            <Box sx={{ flex: 1, border: '1px solid #eee', borderRadius: 1 }}>
              {flowLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                  <CircularProgress />
                </Box>
              ) : flowError ? (
                <Alert severity="error">
                  データの読み込み中にエラーが発生しました。
                </Alert>
              ) : graphData && (
                <ForceGraph2D
                  graphData={graphData}
                  nodeLabel="name"
                  nodeAutoColorBy="group"
                  linkDirectionalArrowLength={3}
                  linkDirectionalArrowRelPos={1}
                  linkWidth={1}
                  linkColor={() => "#999"}
                  nodeCanvasObject={(node, ctx, globalScale) => {
                    const label = node.name;
                    const fontSize = 12/globalScale;
                    ctx.font = `${fontSize}px Sans-Serif`;
                    const textWidth = ctx.measureText(label).width;
                    const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2);
                    
                    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
                    ctx.fillRect(
                      node.x - bckgDimensions[0] / 2,
                      node.y - bckgDimensions[1] / 2,
                      bckgDimensions[0],
                      bckgDimensions[1]
                    );
                    
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillStyle = '#333';
                    ctx.fillText(label, node.x, node.y);
                    
                    node.__bckgDimensions = bckgDimensions;
                  }}
                />
              )}
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: 600, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <Typography variant="h6" gutterBottom>
              メッセージトレース
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Grid container spacing={2} alignItems="center">
                <Grid item xs={8}>
                  <Typography variant="body2" gutterBottom>
                    タイム範囲:
                  </Typography>
                  <Slider
                    value={timeRange}
                    onChange={handleTimeRangeChange}
                    valueLabelDisplay="auto"
                  />
                </Grid>
                <Grid item xs={4}>
                  <FormControl fullWidth size="small">
                    <InputLabel>エージェント</InputLabel>
                    <Select
                      value={selectedAgent}
                      label="エージェント"
                      onChange={handleAgentChange}
                    >
                      <MenuItem value="all">すべて</MenuItem>
                      {agentData && agentData.agents && agentData.agents.map(agent => (
                        <MenuItem key={agent.id} value={agent.id}>{agent.name}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>
            </Box>
            <Divider />
            <Box sx={{ flex: 1, overflow: 'auto', mt: 2 }}>
              {flowLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', pt: 4 }}>
                  <CircularProgress />
                </Box>
              ) : flowError ? (
                <Alert severity="error">
                  メッセージデータの読み込み中にエラーが発生しました。
                </Alert>
              ) : messages.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', pt: 4 }}>
                  表示するメッセージがありません
                </Typography>
              ) : (
                messages.map(message => (
                  <Card key={message.id} variant="outlined" sx={{ mb: 2 }}>
                    <CardContent sx={{ pb: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          {message.timestamp}
                        </Typography>
                        <Chip 
                          label={message.status} 
                          size="small" 
                          sx={{ 
                            backgroundColor: `${getStatusColor(message.status)}20`,
                            color: getStatusColor(message.status),
                            fontWeight: 'bold'
                          }}
                        />
                      </Box>
                      <Typography variant="subtitle2" gutterBottom>
                        {message.from} → {message.to}
                      </Typography>
                      <Typography variant="body2">
                        {message.content}
                      </Typography>
                    </CardContent>
                  </Card>
                ))
              )}
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default AgentVisualizer; 