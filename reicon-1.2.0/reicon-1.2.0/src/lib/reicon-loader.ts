let ready: Promise<void> | null = null;

export function waitForReicon(timeoutMs = 5000): Promise<void> {
  if (!ready) {
    ready = new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Reicon failed to load')), timeoutMs);

      function check() {
        if ((window as any).Reicon) {
          clearTimeout(timer);
          resolve();
        } else {
          setTimeout(check, 50);
        }
      }
      check();
    });
  }
  return ready;
}
