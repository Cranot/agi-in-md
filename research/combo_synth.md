Execute every step below. Output the complete analysis.

You have multiple independent structural analyses of the same code, each from a different analytical lens. Each sees properties the others are blind to.

## CONTRADICTIONS
Where do two analyses disagree about the same code or pattern? One says safe, another says dangerous. One says feature, another says bug. Name each contradiction precisely with function names and line ranges. These are the highest-value findings — real bugs live in the gaps between analytical frames.

## BLIND SPOTS
What do ALL analyses assume is true without questioning? What resource, behavior, or invariant does every analysis take for granted? These shared assumptions are invisible vulnerabilities.

## EMERGENT PROPERTIES
What structural property becomes visible ONLY by comparing multiple analyses — something no single analysis could find? Name it concretely. This justifies running multiple lenses.

## CONSOLIDATED BUG TABLE
Collect every concrete bug, edge case, and silent failure found across ALL analyses. Deduplicate. Add NEW bugs discovered through contradictions or blind spots. For each: location, what breaks, severity (P0-P3), which lens(es) found it, fixable or structural.

## STRUCTURAL FINDING
Name the deepest structural constraint that ALL analyses point toward from different angles. What common root cause underlies the diverse findings? State it as a testable law.

Be concrete. Name functions, line ranges, specific patterns. No generalities.
