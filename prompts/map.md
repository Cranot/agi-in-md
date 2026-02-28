# Substrate — Builder's Map

## What exists
| File | What it does | Status |
|------|-------------|--------|
| `model.py` | Pyramid transformer (~200 lines) | Built, untrained |
| `archetype.py` | Score codebase vs canonical shape | Working |
| `scaffold.py` | Fingerprint → code structure | Working |
| `canonical_shapes.py` | Domain shape database (30 repos) | Working |
| `language_design_insights.py` | Language feature → structure effects | Working |
| `structure_model.py` | Structure autoencoder | Built |
| `code_structure_predictor.py` | Code → structure prediction | Built |
| `cross_language_30.py` | 30-repo analysis pipeline | Working |
| `structures/all_fingerprints.json` | 30 fingerprints | Data |
| `pipelang/` | Language spec + examples | Spec only |

## Architecture quick ref
```
Embed → Bottom blocks (full res, local) → Compress (stride r) → Top blocks (compressed, global) → Decompress → Predict
```
Config: n_embd=192, 2+2 layers, ~1.9M params. Keeps RoPE, RMSNorm, zero-init, ReLU^2, QK norm. No bias.

## What needs doing (priority order)
1. **Train pyramid on Shakespeare** — smoke test, get first loss curve
2. **Flat 8-layer baseline** — same params, compare loss curves
3. **Ablate compress ratios** — r in {2, 4, 8}, measure impact
4. **3-level pyramid** — add middle compression stage
5. **Cross-attention decompression** — replace gather with learned injection
6. **Statistical rigor on 30-repo data** — error bars, significance tests
7. **PipeLang prototype** — minimal interpreter, validate structural guarantees

## Key insight for contributors
The project has two parallel threads:
- **Neural**: pyramid transformer (model.py) — needs training + baselines
- **Structural**: code fingerprinting (archetype.py + friends) — needs statistical validation

Both claim the same principle (structure converges to pyramids). Proving either one strengthens the other.