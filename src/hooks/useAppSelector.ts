import { useSelector, TypedUseSelectorHook } from 'react-redux';
import { RootState } from '../store';

// 型付きセレクターフック
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

export default useAppSelector; 