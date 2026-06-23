import { useOutletContext } from 'react-router-dom';
import type { Centre } from '@/lib/types';

export function useCentreOutlet(): { centre: Centre } {
  return useOutletContext<{ centre: Centre }>();
}
