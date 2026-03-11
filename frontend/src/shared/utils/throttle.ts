export function throttle<T extends (...args: any[]) => void>(fn: T, intervalMs: number): T {
  let last = 0;
  let timer: number | null = null;
  let pendingArgs: any[] | null = null;

  const wrapped = ((...args: any[]) => {
    const now = Date.now();
    const remaining = intervalMs - (now - last);

    if (remaining <= 0) {
      last = now;
      fn(...args);
      return;
    }

    pendingArgs = args;
    if (timer !== null) return;

    timer = window.setTimeout(() => {
      timer = null;
      if (!pendingArgs) return;
      last = Date.now();
      fn(...pendingArgs);
      pendingArgs = null;
    }, remaining);
  }) as T;

  return wrapped;
}
