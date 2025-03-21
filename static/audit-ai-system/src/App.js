import React, { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { 
  CssBaseline, 
  ThemeProvider, 
  createTheme,
  Box
} from '@mui/material';
import MainDashboard from './components/dashboard/MainDashboard';
import AgentVisualizer from './components/agents/AgentVisualizer';
import InterventionInterface from './components/intervention/InterventionInterface';
import SampleManagement from './components/samples/SampleManagement';
import AnalysisDashboard from './components/analysis/AnalysisDashboard';
import SystemSettings from './components/settings/SystemSettings';
import AppHeader from './components/AppHeader';
import AppSidebar from './components/AppSidebar';

// アプリケーションのテーマ設定
const theme = createTheme({
  palette: {
    primary: {
      main: '#3f51b5',
    },
    secondary: {
      main: '#f50057',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: [
      'Roboto',
      'Helvetica',
      'Arial',
      'sans-serif'
    ].join(','),
  },
});

const App = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', height: '100vh' }}>
        <AppHeader toggleSidebar={toggleSidebar} />
        <AppSidebar open={sidebarOpen} />
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: 3,
            mt: 8,
            ml: sidebarOpen ? '240px' : 0,
            transition: 'margin 0.2s',
            overflow: 'auto'
          }}
        >
          <Routes>
            <Route path="/" element={<MainDashboard />} />
            <Route path="/agents" element={<AgentVisualizer />} />
            <Route path="/intervention" element={<InterventionInterface />} />
            <Route path="/samples" element={<SampleManagement />} />
            <Route path="/analysis" element={<AnalysisDashboard />} />
            <Route path="/settings" element={<SystemSettings />} />
          </Routes>
        </Box>
      </Box>
    </ThemeProvider>
  );
};

export default App; 