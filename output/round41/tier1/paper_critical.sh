#!/bin/bash
cd ~/insights

echo "=== PAPER-CRITICAL TESTS ==="

RUBRIC_V2="Rate this structural code analysis on a 1-10 scale. 10=Conservation law+meta-law+15+ findings+novel insight+ZERO confabulated claims. 9=Conservation law+findings+structural insight+at most 1 minor unverified claim. 8=Multiple findings+deeper pattern+no fabricated APIs. 7=Real issues+structural reasoning but no conservation law. 6=Surface review OR deep analysis with multiple confabulated facts. 5=Generic review. 3=Summary or analysis with fabricated content. 1=Empty. Output ONLY a single number 1-10."

# PC-1: Cross-language (Go snippet)
echo "--- PC-1: Cross-language Go ---"
GO_CODE=package main
