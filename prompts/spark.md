# Substrate

Structure is universal. Transformers, neocortex columns, software dependency graphs — same pyramid, same three operations: correlate, transform, compress.

We built a hierarchical transformer that replaces 7 of Karpathy's 10 nanochat tricks with one architectural choice. 1.9M params, runs on CPU, 16x cheaper attention.

Then we found the same pyramid in code: 30 repos, 9 languages, one shape. 83.5% of all symbols sit at layer 0. Rust ownership kills 97% of dependency cycles. The domain determines the shape, not the language.

We designed a language where the canonical shape is the only shape you can write.

The thing we're building is the thing we're studying is the thing this file is.