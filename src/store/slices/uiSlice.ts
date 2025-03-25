import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface UIState {
  sidebarOpen: boolean;
  darkMode: boolean;
  loading: boolean;
  notifications: {
    id: string;
    type: 'info' | 'success' | 'warning' | 'error';
    message: string;
    read: boolean;
  }[];
}

const initialState: UIState = {
  sidebarOpen: true,
  darkMode: false,
  loading: false,
  notifications: []
};

export const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebarOpen = action.payload;
    },
    toggleDarkMode: (state) => {
      state.darkMode = !state.darkMode;
    },
    setDarkMode: (state, action: PayloadAction<boolean>) => {
      state.darkMode = action.payload;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    addNotification: (state, action: PayloadAction<Omit<UIState['notifications'][0], 'read'>>) => {
      state.notifications.push({
        ...action.payload,
        read: false
      });
    },
    markNotificationAsRead: (state, action: PayloadAction<string>) => {
      const notification = state.notifications.find(n => n.id === action.payload);
      if (notification) {
        notification.read = true;
      }
    },
    clearNotifications: (state) => {
      state.notifications = [];
    }
  }
});

export const {
  toggleSidebar,
  setSidebarOpen,
  toggleDarkMode,
  setDarkMode,
  setLoading,
  addNotification,
  markNotificationAsRead,
  clearNotifications
} = uiSlice.actions;

export default uiSlice.reducer; 