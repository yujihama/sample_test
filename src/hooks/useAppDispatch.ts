import { useDispatch } from 'react-redux';
import { AppDispatch } from '../store';

// 型付きディスパッチフック
export const useAppDispatch = () => useDispatch<AppDispatch>();

export default useAppDispatch; 