interface EventHandler<T = unknown> {
  (event: T): void | Promise<void>;
}

class EventBus {
  private handlers: Map<string, Set<EventHandler>> = new Map();
  private middlewares: ((event: string, data: unknown) => unknown)[] = [];

  use(middleware: (event: string, data: unknown) => unknown): void {
    this.middlewares.push(middleware);
  }

  on<T>(event: string, handler: EventHandler<T>): () => void {
    if (!this.handlers.has(event)) this.handlers.set(event, new Set());
    this.handlers.get(event)!.add(handler as EventHandler);
    return () => this.handlers.get(event)?.delete(handler as EventHandler);
  }

  async emit<T>(event: string, data: T): Promise<void> {
    let processed = data as unknown;
    for (const mw of this.middlewares) processed = mw(event, processed);
    const handlers = this.handlers.get(event);
    if (!handlers) return;
    const promises = [...handlers].map(h => h(processed as T));
    await Promise.allSettled(promises);
  }
}
