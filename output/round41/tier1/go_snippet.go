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
