import { useEffect, useRef, useState } from "react";

/**
 * ref로 연결된 DOM 요소의 현재 콘텐츠 너비를 반환.
 * ResizeObserver로 크기 변화를 감지하며, SSR 환경에서는 null을 반환.
 */
export function useContainerWidth<T extends HTMLElement>(): [React.RefObject<T>, number | null] {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState<number | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    setWidth(el.getBoundingClientRect().width);

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setWidth(entry.contentRect.width);
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return [ref, width];
}
