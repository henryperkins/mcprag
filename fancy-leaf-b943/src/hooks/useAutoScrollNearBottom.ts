import { useEffect, useRef, useCallback } from 'react';
import type { RefObject } from 'react';

/**
 * Hook that provides auto-scroll functionality only when near bottom
 * @param ref - The scrollable element ref
 * @param deps - Dependencies that trigger scroll check
 * @param threshold - Distance from bottom in pixels to trigger auto-scroll (default 40)
 * @returns Object with methods and state for auto-scroll control
 */
export function useAutoScrollNearBottom<T extends HTMLElement = HTMLElement>(
  ref: RefObject<T | null>,
  deps: React.DependencyList,
  threshold: number = 40
) {
  const isNearBottomRef = useRef(true);
  const userHasScrolledRef = useRef(false);

  // Check if user is near bottom
  const checkIfNearBottom = useCallback(() => {
    if (!ref.current) return true;
    
    const { scrollTop, scrollHeight, clientHeight } = ref.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    
    return distanceFromBottom <= threshold;
  }, [ref, threshold]);

  // Scroll to bottom if conditions are met
  const scrollToBottom = useCallback(() => {
    if (!ref.current) return;
    
    // Only scroll if user is near bottom or hasn't manually scrolled
    if (isNearBottomRef.current && !userHasScrolledRef.current) {
      requestAnimationFrame(() => {
        if (ref.current) {
          ref.current.scrollTop = ref.current.scrollHeight;
        }
      });
    }
  }, [ref]);

  // Handle user scroll to detect manual scrolling
  const handleScroll = useCallback(() => {
    if (!ref.current) return;
    
    const wasNearBottom = isNearBottomRef.current;
    isNearBottomRef.current = checkIfNearBottom();
    
    // If user scrolled up from near bottom, mark as user-initiated
    if (wasNearBottom && !isNearBottomRef.current) {
      userHasScrolledRef.current = true;
    }
    // If user scrolled back to bottom, reset the flag
    else if (!wasNearBottom && isNearBottomRef.current) {
      userHasScrolledRef.current = false;
    }
  }, [checkIfNearBottom, ref]);

  // Set up scroll listener
  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    element.addEventListener('scroll', handleScroll, { passive: true });
    
    // Initial check
    isNearBottomRef.current = checkIfNearBottom();
    
    return () => {
      element.removeEventListener('scroll', handleScroll);
    };
  }, [ref, handleScroll, checkIfNearBottom]);

  // Auto-scroll when dependencies change
  useEffect(() => {
    scrollToBottom();
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  // Manual scroll to bottom (e.g., for a button)
  const forceScrollToBottom = useCallback(() => {
    if (!ref.current) return;
    
    userHasScrolledRef.current = false;
    isNearBottomRef.current = true;
    ref.current.scrollTop = ref.current.scrollHeight;
  }, [ref]);

  return {
    scrollToBottom,
    forceScrollToBottom,
    isNearBottom: isNearBottomRef.current,
    userHasScrolled: userHasScrolledRef.current,
  };
}