# Transformer Architecture Analysis

## Core Structural Patterns

### 1. Encoder-Decoder Stack

```
Input Tokens
     │
     ▼
[Embedding + Positional Encoding]
     │
     ▼
┌─────────────────────────┐  ×N
│  Multi-Head Self-Attn   │
│  Add & Norm             │
│  Feed-Forward (FFN)     │
│  Add & Norm             │
└─────────────────────────┘
     │ (encoder output K, V)
     ▼
┌─────────────────────────┐  ×N
│  Masked Self-Attn       │
│  Add & Norm             │
│  Cross-Attention        │  ← Q from decoder, K/V from encoder
│  Add & Norm             │
│  FFN                    │
│  Add & Norm             │
└─────────────────────────┘
     │
     ▼
Linear + Softmax → Output tokens
```

### 2. Scaled Dot-Product Attention

```
Attention(Q, K, V) = softmax( QKᵀ / √dₖ ) · V
```

The `√dₖ` scaling prevents vanishing gradients when `dₖ` is large — dot products grow in magnitude with dimension, pushing softmax into near-zero gradient regions.

### 3. Multi-Head Attention

```
MultiHead(Q,K,V) = Concat(head₁...headₕ) · Wᴼ
headᵢ = Attention(Q·Wᵢᴼ, K·Wᵢᴷ, V·Wᵢᵛ)
```

Projects into `h` lower-dimensional subspaces, each learning different relational patterns (syntactic, semantic, positional, etc.).

### 4. Residual Connections + Layer Norm

```
x ← LayerNorm(x + Sublayer(x))
```

Pre-norm variants (`LayerNorm(x) + Sublayer(LayerNorm(x))` in later work) proved more stable for deep stacks.

### 5. Sinusoidal Positional Encoding

```
PE(pos, 2i)   = sin(pos / 10000^(2i/dmodel))
PE(pos, 2i+1) = cos(pos / 10000^(2i/dmodel))
```

Injected at input — the architecture itself is otherwise **permutation-equivariant**.

---

## Structural Problems & Known Weaknesses

### Problem 1: Quadratic Complexity in Sequence Length
```
Attention cost: O(n² · d)
```
For sequence length `n`, the attention matrix is `n×n`. At `n=4096` that's 16M entries per head per layer. Memory and compute become prohibitive for long contexts.

**Downstream solutions:** Sparse attention (Longformer, BigBird), linear attention (Performer), sliding window attention, FlashAttention (IO-aware kernel).

---

### Problem 2: No Inductive Bias for Locality

Unlike CNNs (local receptive fields) or RNNs (recency bias), every token attends to every other token equally at initialization. This means:
- The model **must learn** from data that nearby tokens are typically more relevant.
- Sample efficiency suffers on small datasets.
- Positional encoding is a weak signal — it's added, not baked into the operation.

---

### Problem 3: Fixed-Length Positional Encoding / Poor Length Generalization

Sinusoidal PE degrades outside the training length distribution. The model doesn't generalize robustly to longer sequences at inference.

**Downstream solutions:** RoPE (Rotary Position Embedding), ALiBi (attention with linear biases), learned relative positions.

---

### Problem 4: FFN as a Static Key-Value Memory

The two-layer FFN:
```
FFN(x) = max(0, xW₁ + b₁)W₂ + b₂
```
was later analyzed (Geva et al., 2021) as a memory lookup mechanism. It is:
- **Static** — weights don't adapt at inference time.
- **Overparameterized** for small tasks.
- Comprises ~2/3 of parameter count in large models.

---

### Problem 5: Encoder-Decoder Coupling

The hard split (encoder produces full representation, decoder cross-attends) creates issues:
- Cross-attention adds another `O(n·m)` cost.
- Decoder must wait for the full encoder pass.
- **Decoder-only** (GPT lineage) and **encoder-only** (BERT lineage) architectures dropped this and proved more scalable for specific use cases.

---

### Problem 6: Autoregressive Decoding is Sequential

At inference, each output token requires a full forward pass. KV-caching mitigates this but:
- KV cache grows linearly with sequence length (memory wall).
- Cannot trivially parallelize across output positions.

---

### Problem 7: Layer Norm Placement (Post-Norm Instability)

The original paper uses **Post-LN** (`LayerNorm(x + F(x))`). This is known to:
- Require careful learning rate warmup.
- Cause gradient scale explosion in very deep networks without warmup.

Pre-LN (`x + F(LayerNorm(x))`) is more stable but shifts the residual stream's role.

---

### Problem 8: Attention Head Redundancy

Empirically (Michel et al., 2019), large fractions of attention heads can be pruned at inference with minimal performance loss. The original design provides no mechanism to suppress redundant heads during training.

---

## Summary Table

| Pattern | What it solves | Known weakness |
|---|---|---|
| Self-attention | Long-range dependencies | O(n²) cost |
| Multi-head | Diverse relational features | Head redundancy |
| Residual + LN | Deep network training | Post-LN instability |
| Sinusoidal PE | Order information | Poor length extrapolation |
| FFN | Capacity / "memory" | Static, large parameter share |
| Enc-Dec split | Seq2seq modeling | Coupling overhead |

---

The paper's fundamental insight — **replace recurrence entirely with attention** — was correct and has proven durable. The specific implementation choices (sinusoidal PE, post-norm, fixed FFN ratio, absolute positions) have largely been superseded in production systems, but the core attention mechanism remains the organizing principle of essentially all large-scale language models today.
