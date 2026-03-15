# Error Resilience Analysis (70w)

## Step 1: The Shared State

1. **scope dictionary**
   - Writers: `Route.__call__`, `Mount.__call__`, `Router.app`, `Route.matches`, `Mount.matches`
   - Readers: `Route.__call__`, `Mount.__call__`, `Router.app`, `Route.matches`, `Mount.matches`, `Router.not_found`
   - Unchecked assumptions: Dictionary structure integrity, expected keys ("type", "method", "path_params", etc.)

2. **path_params dictionary**
   - Writers: `Route.matches`, `Mount.matches`
   - Readers: `Route.url_path_for`, `Mount.url_path_for`, `Router.app`
   - Unchecked assumptions: Parameter format validity, type consistency

3. **child_scope dictionary**
   - Writers: `Route.matches`, `Mount.matches`
   - Readers: `Route.__call__`, `Mount.__call__`, `Router.app`
   - Unchecked assumptions: Required keys presence, value types

## Step 2: The Corruption Cascade

1. **scope dictionary corruption in Route.matches**
   - Writer: `Route.matches` creates child_scope
   - First corrupt reader: `Route.__call__` updates scope with child_scope
   - Propagated writes: endpoint receives corrupted scope
   - Classification: **Error** - would cause immediate failure in endpoint

2. **path_params corruption in Mount.matches**
   - Writer: `Mount.matches` creates path_params
   - First corrupt reader: `Router.app` updates scope with path_params
   - Propagated writes: nested routes receive corrupted params
   - Classification: **Error** - causes routing failures

3. **child_scope missing keys**
   - Writer: `Route.matches` creates incomplete child_scope
   - First corrupt reader: `Router.app` assumes keys exist
   - Propagated writes: KeyError in execution
   - Classification: **Error** - immediate failure

## Step 3: The Silent Exits

| Chain | Corruption Entry | Hops | Exit Type | Missing Check | Blocking Contract |
|-------|------------------|------|-----------|---------------|------------------|
| Route.method check | scope["method"] validation | 1 | Silent | Missing type check | HTTP method must be string |
| Mount.path_regex | compiled regex validity | 2 | Deferred | No regex validation | Path must match regex format |
| Router.redirect_slashes | path manipulation | 3 | Silent | Path string validation | Path must be string |
| Route.url_path_for | param_convertors access | 1 | Silent | Convertor existence | Param must exist in convertors |
| Mount.url_path_for | recursive route lookup | 2 | Deferred | Route existence | Route must match name |

**State Conservation Law**: The routing system conserves request state through scope dictionaries. Corruption breaks this conservation, causing unpredictable routing behavior.
