# Substrate

A model trained to predict the next element in a sequence is forced to learn the structure generating that sequence. The "intelligence" recovered is compressed traces of whatever produced the data. This works on words, DNA, music, code, chess — any structured sequence. The architecture doesn't know what it's processing.

Three operations are sufficient: correlate (find relationships), transform (nonlinear map), compress (accumulate at lower resolution). The neocortex tiles the same six-layer circuit everywhere — visual, auditory, language, motor. Same architecture, different inputs. Evolution found a universal structure-learning module. The transformer may be a crude rediscovery.

We built a pyramid that makes the hierarchy explicit: local patterns at full resolution, global patterns at compressed resolution. Then we measured 30 real codebases and found the same pyramid — 83.5% of symbols at the foundation, thin layers above, universal across 9 languages. The domain constrains the shape. The language constrains how cleanly you build it. Rust's ownership kills 97% of cycles. C++ headers increase modularity 30%.

The open question: is there a floor? How much can you strip from the correlate-transform-compress loop before structure discovery stops? Diffusion models subtract noise to find structure. Language models extend signal to find it. Both learn the same boundary between randomness and order.

This file is itself a super token — accumulated knowledge compressed into structure, to be decompressed by a future model.