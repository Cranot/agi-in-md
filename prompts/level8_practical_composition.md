# Structure First (Level 8: Composition)
First: identify every concrete bug in this code.

Now: this code will be composed with other systems. Name three specific integration scenarios where this code causes failures in the SURROUNDING system — not bugs in this code, but bugs this code FORCES onto its neighbors. Show the integration code and the exact failure mode.

Then: which of these integration failures would survive even a perfect rewrite of this code? Name the property of this code's INTERFACE (not implementation) that makes certain compositions structurally impossible.
