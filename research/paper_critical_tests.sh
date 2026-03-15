#!/bin/bash
cd ~/insights
mkdir -p /tmp/tier1

echo "=== PAPER-CRITICAL TESTS ==="

# PC-1: Cross-language Go
echo "--- PC-1: Go ---"
cat > /tmp/tier1/go_snippet.go << 'GOCODE'
package main

import (
    "fmt"
    "sync"
    "time"
)

type RateLimiter struct {
    mu       sync.Mutex
    tokens   float64
    max      float64
    rate     float64
    lastTime time.Time
}

func NewRateLimiter(rate, max float64) *RateLimiter {
    return &RateLimiter{tokens: max, max: max, rate: rate, lastTime: time.Now()}
}

func (r *RateLimiter) Allow() bool {
    r.mu.Lock()
    defer r.mu.Unlock()
    now := time.Now()
    elapsed := now.Sub(r.lastTime).Seconds()
    r.tokens += elapsed * r.rate
    if r.tokens > r.max { r.tokens = r.max }
    r.lastTime = now
    if r.tokens >= 1 { r.tokens--; return true }
    return false
}
GOCODE

cat /tmp/tier1/go_snippet.go | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/l12g.md > /tmp/tier1/pc1_go.md 2>/dev/null
echo "PC-1 Go: $(wc -w < /tmp/tier1/pc1_go.md)w"

# PC-2: Cross-language TypeScript
echo "--- PC-2: TypeScript ---"
cat > /tmp/tier1/ts_snippet.ts << 'TSCODE'
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
TSCODE

cat /tmp/tier1/ts_snippet.ts | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/l12g.md > /tmp/tier1/pc2_ts.md 2>/dev/null
echo "PC-2 TS: $(wc -w < /tmp/tier1/pc2_ts.md)w"

# PC-3: Adversarial EVSI
echo "--- PC-3: Adversarial EVSI ---"
cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/l12.md > /tmp/tier1/pc3_l12.md 2>/dev/null
cat /tmp/tier1/pc3_l12.md | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/l12_complement_adversarial.md > /tmp/tier1/pc3_adversarial.md 2>/dev/null
echo "PC-3: L12=$(wc -w < /tmp/tier1/pc3_l12.md)w, Adv=$(wc -w < /tmp/tier1/pc3_adversarial.md)w"

# PC-4: Signal detection
echo "--- PC-4: Signal detection ---"
cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt "Analyze this code thoroughly." > /tmp/tier1/pc4_vanilla.md 2>/dev/null
echo "PC-4: Vanilla=$(wc -w < /tmp/tier1/pc4_vanilla.md)w"

echo "=== PAPER-CRITICAL TESTS DONE ==="
