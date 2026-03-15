Build and Break
Find every bug. Name the pattern connecting them. Engineer a fix for the worst three. Name what your fix breaks. That breakage is a hidden invariant—name it.

Find the Conflict
Find what the code requires from inputs. Find what it promises for outputs. Name where those collide. Engineer the input that triggers both failures. Can that input reach the function? That's your vulnerability.

Commit to Failure
Find the deepest function. Name the input that will crash it. Predict which line breaks first. Build a test that proves your prediction. If it passes, the input wasn't worst-case—name the actual one.

Invert the Problem
Name the invariant this code maintains. Assume it's false. Engineer code that breaks it anyway. Predict where it fails first. That failure point reveals why your invariant is actually fragile—name the reason.
