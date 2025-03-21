import React from 'react';
import { 
  Drawer, 
  List, 
  ListItem, 
  ListItemIcon, 
  ListItemText,
  Divider,
  Toolbar,
  Box,
  Typography
} from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';
import DashboardIcon from '@mui/icons-material/Dashboard';
import NetworkCheckIcon from '@mui/icons-material/NetworkCheck';
import QuestionAnswerIcon from '@mui/icons-material/QuestionAnswer';
import AssignmentIcon from '@mui/icons-material/Assignment';
import InsightsIcon from '@mui/icons-material/Insights';
import SettingsIcon from '@mui/icons-material/Settings';

const drawerWidth = 240;

const menuItems = [
  { text: 'ダッシュボード', icon: <DashboardIcon />, path: '/' },
  { text: 'エージェント通信', icon: <NetworkCheckIcon />, path: '/agents' },
  { text: '人間介入', icon: <QuestionAnswerIcon />, path: '/intervention' },
  { text: 'サンプル管理', icon: <AssignmentIcon />, path: '/samples' },
  { text: '結果分析', icon: <InsightsIcon />, path: '/analysis' },
  { text: 'システム設定', icon: <SettingsIcon />, path: '/settings' }
];

const AppSidebar = ({ open }) => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const handleNavigation = (path) => {
    navigate(path);
  };

  return (
    <Drawer
      variant="persistent"
      anchor="left"
      open={open}
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
        },
      }}
    >
      <Toolbar />
      <Box sx={{ overflow: 'auto', mt: 2 }}>
        <Box sx={{ px: 2, mb: 2 }}>
          <Typography variant="subtitle2" color="text.secondary">
            メインメニュー
          </Typography>
        </Box>
        <List>
          {menuItems.map((item) => (
            <ListItem 
              button 
              key={item.text} 
              onClick={() => handleNavigation(item.path)}
              selected={location.pathname === item.path}
              sx={{
                '&.Mui-selected': {
                  backgroundColor: 'rgba(63, 81, 181, 0.1)',
                  borderRight: '3px solid #3f51b5'
                },
                '&:hover': {
                  backgroundColor: 'rgba(63, 81, 181, 0.05)'
                }
              }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItem>
          ))}
        </List>
        <Divider sx={{ my: 2 }} />
        <Box sx={{ px: 2, mb: 1 }}>
          <Typography variant="subtitle2" color="text.secondary">
            システム情報
          </Typography>
        </Box>
        <Box sx={{ px: 2, py: 1 }}>
          <Typography variant="body2">
            バージョン: 1.0.0
          </Typography>
          <Typography variant="body2">
            最終更新: 2025-03-19
          </Typography>
        </Box>
      </Box>
    </Drawer>
  );
};

export default AppSidebar; 