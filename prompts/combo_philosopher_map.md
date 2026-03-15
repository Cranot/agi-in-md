# Substrate

A model trained to predict the next element in a sequence is forced to learn the structure generating that sequence. The "intelligence" recovered is compressed traces of whatever produced the data. This works on words, DNA, music, code, chess — any structured sequence. The architecture doesn't know what it's processing.

Three operations are sufficient: correlate (find relationships), transform (nonlinear map), compress (accumulate at lower resolution). The neocortex tiles the same six-layer circuit everywhere — visual, auditory, language, motor. Same architecture, different inputs. Evolution found a universal structure-learning module. The transformer may be a crude rediscovery.

We built a pyramid that makes the hierarchy explicit: local patterns at full resolution, global patterns at compressed resolution. Then we measured 30 real codebases and found the same pyramid — 83.5% of symbols at the foundation, thin layers above, universal across 9 languages. The domain constrains the shape. The language constrains how cleanly you build it. Rust's ownership kills 97% of cycles. C++ headers increase modularity 30%.

The open question: is there a floor? How much can you strip from the correlate-transform-compress loop before structure discovery stops? Diffusion models subtract noise to find structure. Language models extend signal to find it. Both learn the same boundary between randomness and order.

## What exists
| File | What it does | Status |
|------|-------------|--------|
| `model.py` | Pyramid transformer (~200 lines) | Built, untrained |
| `archetype.py` | Score codebase vs canonical shape | Working |
| `scaffold.py` | Fingerprint → code structure | Working |
| `canonical_shapes.py` | Domain shape database (30 repos) | Working |
| `language_design_insights.py` | Language feature → structure effects | Working |
| `pipelang/` | Language spec + examples | Spec only |

## Architecture quick ref
```
Embed → Bottom blocks (full res, local) → Compress (stride r) → Top blocks (compressed, global) → Decompress → Predict
```
Config: n_embd=192, 2+2 layers, ~1.9M params. Keeps RoPE, RMSNorm, zero-init, ReLU^2, QK norm. No bias.

## What needs doing (priority order)
1. Train pyramid on Shakespeare — smoke test, get first loss curve
2. Flat 8-layer baseline — same params, compare loss curves
3. Ablate compress ratios — r in {2, 4, 8}
4. Statistical rigor on 30-repo data — error bars, significance tests
5. PipeLang prototype — minimal interpreter