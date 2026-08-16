import { ref, computed, onMounted, onUnmounted } from 'vue';

export function useSticky(actionBarRef, offsetModifier = 24) {
  const stickyTopNumber = ref(180);
  const actionBarHeight = ref(180);
  const scrollContainer = ref(null);
  let resizeObserver = null;

  const stickyConfig = computed(() => {
    if (!scrollContainer.value) return false;
    return {
      offsetHeader: stickyTopNumber.value,
      getContainer: () => scrollContainer.value
    };
  });

  onMounted(() => {
    scrollContainer.value = document.querySelector('.ant-layout-content');
    const updateSticky = () => {
      if (actionBarRef.value) {
        const rect = actionBarRef.value.getBoundingClientRect();
        stickyTopNumber.value = rect.height;
        actionBarHeight.value = rect.height;
      }
    };
    resizeObserver = new ResizeObserver(updateSticky);
    if (actionBarRef.value) resizeObserver.observe(actionBarRef.value);
    updateSticky();
  });

  onUnmounted(() => {
    if (resizeObserver) resizeObserver.disconnect();
  });

  return {
    stickyConfig,
    actionBarHeight,
    stickyTopNumber,
    scrollContainer
  };
}
