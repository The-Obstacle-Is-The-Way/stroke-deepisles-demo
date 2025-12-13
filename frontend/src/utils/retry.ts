/**
 * Shared retry configuration for cold-start handling.
 *
 * HuggingFace Spaces containers can take 30-60 seconds to wake from sleep.
 * This module provides shared constants and utilities for exponential backoff retry.
 */

// Cold start retry configuration
export const MAX_COLD_START_RETRIES = 5;
export const INITIAL_RETRY_DELAY = 2000; // 2 seconds
export const MAX_RETRY_DELAY = 30000; // 30 seconds

/**
 * Calculate exponential backoff delay with capped maximum.
 *
 * @param attempt - Current retry attempt (1-indexed)
 * @returns Delay in milliseconds
 */
export function getRetryDelay(attempt: number): number {
  return Math.min(INITIAL_RETRY_DELAY * Math.pow(2, attempt - 1), MAX_RETRY_DELAY);
}

/**
 * Sleep utility for async delays.
 *
 * @param ms - Milliseconds to sleep
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
