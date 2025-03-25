import { createTheme, ThemeOptions } from '@mui/material/styles';

// ライトモードのテーマ設定
export const lightTheme: ThemeOptions = {
  palette: {
    mode: 'light',
    primary: {
      main: '#2B3A67', // ダークブルー
      light: '#5D6B8D',
      dark: '#1A2546',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#4682B4', // スチールブルー
      light: '#6CA0C9',
      dark: '#306990',
      contrastText: '#FFFFFF',
    },
    error: {
      main: '#D32F2F',
    },
    warning: {
      main: '#F57C00',
    },
    info: {
      main: '#0288D1',
    },
    success: {
      main: '#388E3C',
    },
    background: {
      default: '#F5F7FA',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#333333',
      secondary: '#666666',
    },
  },
  typography: {
    fontFamily: '"Noto Sans JP", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 500,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 500,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 500,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 500,
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 500,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 500,
    },
    body1: {
      fontSize: '1rem',
    },
    body2: {
      fontSize: '0.875rem',
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
  },
};

// ダークモードのテーマ設定
export const darkTheme: ThemeOptions = {
  palette: {
    mode: 'dark',
    primary: {
      main: '#90CAF9', // ライトブルー
      light: '#B3E5FC',
      dark: '#64B5F6',
      contrastText: '#000000',
    },
    secondary: {
      main: '#81D4FA', // ライトブルー
      light: '#B3E5FC',
      dark: '#4FC3F7',
      contrastText: '#000000',
    },
    error: {
      main: '#F44336',
    },
    warning: {
      main: '#FF9800',
    },
    info: {
      main: '#29B6F6',
    },
    success: {
      main: '#66BB6A',
    },
    background: {
      default: '#121212',
      paper: '#1E1E1E',
    },
    text: {
      primary: '#FFFFFF',
      secondary: '#B0B0B0',
    },
  },
  typography: {
    fontFamily: '"Noto Sans JP", "Roboto", "Helvetica", "Arial", sans-serif',
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
  },
};

// テーマ生成関数
export const createAppTheme = (mode: 'light' | 'dark') => {
  return createTheme(mode === 'light' ? lightTheme : darkTheme);
};

export default createAppTheme; 