import { configureStore } from '@reduxjs/toolkit';
import uiReducer from './slices/uiSlice';

export const store = configureStore({
  reducer: {
    ui: uiReducer,
    // 他のリデューサーはここに追加していきます
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // 非シリアライズ可能な値を無視する設定（必要に応じて）
        ignoredActions: [],
        ignoredActionPaths: [],
        ignoredPaths: [],
      },
    }),
});

// RootState型とAppDispatch型を定義
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch; 