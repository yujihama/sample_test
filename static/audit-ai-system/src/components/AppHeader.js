import React from 'react';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  IconButton, 
  Badge,
  Box,
  Avatar
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import NotificationsIcon from '@mui/icons-material/Notifications';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import SettingsIcon from '@mui/icons-material/Settings';

const AppHeader = ({ toggleSidebar }) => {
  return (
    <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
      <Toolbar>
        <IconButton
          color="inherit"
          aria-label="open drawer"
          edge="start"
          onClick={toggleSidebar}
          sx={{ mr: 2 }}
        >
          <MenuIcon />
        </IconButton>
        <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
          内部監査AIエージェントシステム
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <IconButton color="inherit">
            <Badge badgeContent={4} color="error">
              <NotificationsIcon />
            </Badge>
          </IconButton>
          <IconButton color="inherit">
            <HelpOutlineIcon />
          </IconButton>
          <IconButton color="inherit">
            <SettingsIcon />
          </IconButton>
          <Avatar sx={{ ml: 2, bgcolor: 'secondary.main' }}>AI</Avatar>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default AppHeader; 