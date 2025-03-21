import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  CardHeader,
  Divider,
  Grid,
  Slider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  InputAdornment,
  IconButton,
  Chip,
  ToggleButtonGroup,
  ToggleButton,
  Alert,
  CircularProgress,
  Button
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import FilterListIcon from '@mui/icons-material/FilterList';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import { Refresh as RefreshIcon } from '@mui/icons-material';
import TimelineIcon from '@mui/icons-material/Timeline';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import * as d3 from 'd3';

// APIサービスとカスタムフックをインポート
import { agentApi } from '../../frontend/services/api';
import useApi from '../../frontend/hooks/useApi';

const AgentVisualizer = () => {
  // ビジュアライゼーションの種類（ネットワーク/タイムライン）
  const [viewType, setViewType] = useState('network');
  
  // ズームレベル
  const [zoomLevel, setZoomLevel] = useState(1);
  
  // 表示する時間範囲
  const [timeRange, setTimeRange] = useState([0, 24]);
  
  // フィルタリング設定
  const [selectedAgent, setSelectedAgent] = useState('all');
  const [filterText, setFilterText] = useState('');
  
  // D3用のDOM参照
  const svgRef = useRef(null);
  
  // APIからエージェント一覧を取得
  const { 
    data: agentsData, 
    loading: agentsLoading, 
    error: agentsError,
    refetch: refetchAgents
  } = useApi(() => agentApi.getAgents(), {
    dependencies: [],
    cacheResults: true,
    cacheTime: 5 * 60 * 1000, // 5分間キャッシュ
    retryCount: 1
  });
  
  // APIからメッセージフローを取得
  const { 
    data: messageFlowData, 
    loading: messageFlowLoading, 
    error: messageFlowError,
    refetch: refetchMessageFlow
  } = useApi(() => agentApi.getMessageFlow(), {
    dependencies: [],
    cacheResults: true,
    cacheTime: 5 * 60 * 1000, // 5分間キャッシュ
    retryCount: 1
  });
  
  // エージェントノードのデータを取得
  const getAgentNodes = () => {
    if (!agentsData?.success || !agentsData?.data?.agents) {
      return [];
    }
    return agentsData.data.agents;
  };
  
  // エージェント間のリンクデータを取得
  const getAgentLinks = () => {
    if (!messageFlowData?.success || !messageFlowData?.data?.links) {
      return [];
    }
    return messageFlowData.data.links;
  };

  // ノードデータを取得
  const getNodes = () => {
    if (!messageFlowData?.success || !messageFlowData?.data?.nodes) {
      return [];
    }
    return messageFlowData.data.nodes;
  };

  // 全データを再取得する関数
  const refreshAllData = () => {
    refetchAgents(true); // キャッシュを無視して強制リフレッシュ
    refetchMessageFlow(true);
  };

  // ズームインボタンのハンドラ
  const handleZoomIn = () => {
    setZoomLevel(prev => Math.min(prev + 0.2, 2));
  };
  
  // ズームアウトボタンのハンドラ
  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(prev - 0.2, 0.5));
  };
  
  // ビュータイプ変更ハンドラ
  const handleViewTypeChange = (event, newViewType) => {
    if (newViewType !== null) {
      setViewType(newViewType);
    }
  };
  
  // 時間範囲変更ハンドラ 
  const handleTimeRangeChange = (event, newValue) => {
    setTimeRange(newValue);
  };
  
  // エージェントフィルタリング変更ハンドラ
  const handleAgentChange = (event) => {
    setSelectedAgent(event.target.value);
  };
  
  // テキストフィルタリング変更ハンドラ
  const handleFilterTextChange = (event) => {
    setFilterText(event.target.value);
  };
  
  // D3によるビジュアライゼーション描画
  useEffect(() => {
    if (agentsLoading || messageFlowLoading) return;
    
    const agentNodes = getAgentNodes();
    const agentLinks = getAgentLinks();
    const nodes = getNodes();
    
    if (agentNodes.length === 0 || agentLinks.length === 0) return;

    // D3のコードはここに実装します
    // ここではビジュアライゼーションの枠組みだけを作成
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // D3による描画コードのプレースホルダ
    if (viewType === 'network') {
      // ネットワークビューを描画
      drawNetworkGraph(svg, nodes, agentLinks);
    } else {
      // タイムラインビューを描画
      drawTimelineView(svg, agentNodes);
    }
  }, [agentsLoading, messageFlowLoading, viewType, zoomLevel, timeRange, selectedAgent, filterText]);
  
  // ネットワークグラフの描画関数
  const drawNetworkGraph = (svg, nodes, links) => {
    // ネットワークグラフ描画のプレースホルダ
    const width = svg.node().getBoundingClientRect().width;
    const height = 500;
    
    // SVGサイズを設定
    svg.attr("viewBox", [0, 0, width, height]);
    
    // フィルタリング適用
    let filteredNodes = nodes;
    let filteredLinks = links;
    
    if (selectedAgent !== 'all') {
      filteredNodes = nodes.filter(node => node.id === selectedAgent);
      filteredLinks = links.filter(link => 
        link.source === selectedAgent || link.target === selectedAgent
      );
    }
    
    if (filterText) {
      const lowerFilterText = filterText.toLowerCase();
      filteredNodes = filteredNodes.filter(node => 
        node.id.toLowerCase().includes(lowerFilterText) || 
        node.label.toLowerCase().includes(lowerFilterText)
      );
      filteredLinks = filteredLinks.filter(link =>
        filteredNodes.some(node => node.id === link.source) && 
        filteredNodes.some(node => node.id === link.target)
      );
    }
    
    // ノードが空の場合は「データなし」メッセージを表示
    if (filteredNodes.length === 0) {
      svg.append("text")
        .attr("x", width / 2)
        .attr("y", height / 2)
        .attr("text-anchor", "middle")
        .text("フィルタリングに一致するエージェントがありません");
      return;
    }
    
    // テキスト表示（実際のD3グラフは追加実装が必要）
    svg.append("text")
      .attr("x", width / 2)
      .attr("y", height / 2)
      .attr("text-anchor", "middle")
      .text("ネットワークグラフ表示（データあり）");
  };
  
  // タイムラインビューの描画関数
  const drawTimelineView = (svg, agents) => {
    // タイムラインビュー描画のプレースホルダ
    const width = svg.node().getBoundingClientRect().width;
    const height = 500;
    
    // SVGサイズを設定
    svg.attr("viewBox", [0, 0, width, height]);
    
    // フィルタリング適用
    let filteredAgents = agents;
    
    if (selectedAgent !== 'all') {
      filteredAgents = agents.filter(agent => agent.id === selectedAgent);
    }
    
    if (filterText) {
      const lowerFilterText = filterText.toLowerCase();
      filteredAgents = filteredAgents.filter(agent => 
        agent.id.toLowerCase().includes(lowerFilterText) || 
        agent.type.toLowerCase().includes(lowerFilterText)
      );
    }
    
    // エージェントが空の場合は「データなし」メッセージを表示
    if (filteredAgents.length === 0) {
      svg.append("text")
        .attr("x", width / 2)
        .attr("y", height / 2)
        .attr("text-anchor", "middle")
        .text("フィルタリングに一致するエージェントがありません");
      return;
    }
    
    // テキスト表示（実際のD3グラフは追加実装が必要）
    svg.append("text")
      .attr("x", width / 2)
      .attr("y", height / 2)
      .attr("text-anchor", "middle")
      .text("タイムラインビュー表示（データあり）");
  };
  
  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        エージェントビジュアライザ
      </Typography>
      
      {/* コントロールパネル */}
      <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={8}>
            <Grid container spacing={2} alignItems="center">
              <Grid item>
                <ToggleButtonGroup
                  value={viewType}
                  exclusive
                  onChange={handleViewTypeChange}
                  size="small"
                >
                  <ToggleButton value="network">
                    <AccountTreeIcon sx={{ mr: 1 }} />
                    ネットワーク
                  </ToggleButton>
                  <ToggleButton value="timeline">
                    <TimelineIcon sx={{ mr: 1 }} />
                    タイムライン
                  </ToggleButton>
                </ToggleButtonGroup>
              </Grid>
              
              <Grid item>
                <IconButton onClick={handleZoomIn}>
                  <ZoomInIcon />
                </IconButton>
                <IconButton onClick={handleZoomOut}>
                  <ZoomOutIcon />
                </IconButton>
              </Grid>
              
              <Grid item>
                <FormControl variant="outlined" size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>エージェント</InputLabel>
                  <Select
                    value={selectedAgent}
                    onChange={handleAgentChange}
                    label="エージェント"
                  >
                    <MenuItem value="all">すべて</MenuItem>
                    {getAgentNodes().map((agent) => (
                      <MenuItem key={agent.id} value={agent.id}>{agent.type}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item>
                <TextField
                  size="small"
                  placeholder="フィルタ"
                  value={filterText}
                  onChange={handleFilterTextChange}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <FilterListIcon />
                      </InputAdornment>
                    ),
                  }}
                />
              </Grid>
            </Grid>
          </Grid>
          
          <Grid item xs={12} md={4} sx={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={refreshAllData}
              disabled={agentsLoading || messageFlowLoading}
            >
              更新
            </Button>
          </Grid>
          
          {viewType === 'timeline' && (
            <Grid item xs={12}>
              <Typography gutterBottom>時間範囲: {timeRange[0]}時間 - {timeRange[1]}時間</Typography>
              <Slider
                value={timeRange}
                onChange={handleTimeRangeChange}
                valueLabelDisplay="auto"
                min={0}
                max={24}
                marks={[
                  { value: 0, label: '0h' },
                  { value: 6, label: '6h' },
                  { value: 12, label: '12h' },
                  { value: 18, label: '18h' },
                  { value: 24, label: '24h' },
                ]}
              />
            </Grid>
          )}
        </Grid>
      </Paper>
      
      {/* ビジュアライゼーション表示エリア */}
      <Paper elevation={2} sx={{ p: 2, height: 520 }}>
        {agentsLoading || messageFlowLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <CircularProgress />
          </Box>
        ) : agentsError || messageFlowError ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <Alert severity="error" sx={{ maxWidth: 500 }}>
              {agentsError || messageFlowError}
            </Alert>
          </Box>
        ) : (
          <svg ref={svgRef} width="100%" height="500px"></svg>
        )}
      </Paper>
      
      {/* エージェント詳細 */}
      <Grid container spacing={3} sx={{ mt: 3 }}>
        <Grid item xs={12}>
          <Paper elevation={2} sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              エージェント詳細
            </Typography>
            <Divider sx={{ mb: 2 }} />
            
            {agentsLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
              </Box>
            ) : agentsError ? (
              <Alert severity="error">
                データの読み込みに失敗しました: {agentsError}
              </Alert>
            ) : (
              <Grid container spacing={2}>
                {getAgentNodes().map((agent) => (
                  <Grid item xs={12} sm={6} md={4} key={agent.id}>
                    <Card variant="outlined">
                      <CardContent>
                        <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <Typography variant="h6">{agent.type}</Typography>
                          <Chip 
                            label={agent.status} 
                            color={
                              agent.status === 'active' ? 'success' : 
                              agent.status === 'warning' ? 'warning' : 
                              'error'
                            }
                            size="small"
                          />
                        </Box>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          ID: {agent.id}
                        </Typography>
                        <Divider sx={{ my: 1 }} />
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="body2">
                            <strong>完了タスク:</strong> {agent.stats?.completed || 0}
                          </Typography>
                          <Typography variant="body2">
                            <strong>進行中タスク:</strong> {agent.stats?.inProgress || 0}
                          </Typography>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default AgentVisualizer; 