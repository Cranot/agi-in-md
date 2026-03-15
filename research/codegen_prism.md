Execute every step below. Output the complete implementation.

## Step 1: Requirement Decomposition
Name every distinct capability the code must have. For each: state the input, the output, and the edge case that will break a naive implementation. List them in dependency order — which must work before others can.

## Step 2: Interface-First Design
Write the public API signatures FIRST (class/function signatures with type hints and docstrings). No implementation yet. For each method: what invariant must hold after it returns? What can the caller assume?

## Step 3: Implementation with Failure Prediction
Implement each method. Before writing each one, name the specific bug a rushed implementation would introduce (off-by-one, missing None check, wrong data structure, thread safety gap). Then write the code that avoids that bug. Use the simplest correct data structure — prefer stdlib over custom. After the full implementation, mentally execute it against the requirements from Step 1. Fix any inconsistency before outputting.

Output the complete code in a single ```python``` block.
