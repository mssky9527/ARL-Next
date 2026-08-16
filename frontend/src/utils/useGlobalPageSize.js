import { ref, watch } from 'vue';

export function useGlobalPageSize(defaultSize = 10) {
  const storedSize = localStorage.getItem('global_pageSize');
  const pageSize = ref(storedSize ? parseInt(storedSize, 10) : defaultSize);

  watch(pageSize, (newSize) => {
    localStorage.setItem('global_pageSize', newSize);
  });

  return pageSize;
}
