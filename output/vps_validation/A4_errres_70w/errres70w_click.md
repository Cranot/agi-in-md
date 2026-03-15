## Step 1: The Shared State
Mutable state shared across functions:

1. `ctx.params` (Dictionary)
   - Writers: `Parameter.handle_parse_result`, `Context.lookup_default`
   - Readers: `Command.invoke`, `Group.invoke`, `Context.forward`
   - Unchecked assumption: Parameters are processed before invocation

2. `ctx.args` (List)
   - Writers: `Command.parse_args`, `Group.parse_args`, `Group.invoke`
   - Readers: `Group.resolve_command`, `Command.invoke`
   - Unchecked assumption: Arguments list remains consistent during processing

3. `ctx.invoked_subcommand` (String/None)
   - Writers: `Group.invoke`
   - Readers: `Context.lookup_default`, `Command.invoke`
   - Unchecked assumption: Subcommand name is valid when set

4. `ctx._protected_args` (List)
   - Writers: `Group.parse_args`, `Group.invoke`
   - Readers: `Group.invoke`
   - Unchecked assumption: Protected args are only modified in specific contexts

5. `ctx.resilient_parsing` (Boolean)
   - Writers: `Context.__init__`
   - Readers: `Command.parse_args`, `Group.parse_args`, `Group.resolve_command`
   - Unchecked assumption: Parsing mode is consistent across all operations

## Step 2: The Corruption Cascade
Critical failure points and error propagation:

1. Parameter processing failure in `Parameter.handle_parse_result`
   - Error: Type conversion failure or missing required parameter
   - Silent exit: Propagates as `MissingParameter` exception
   - Chain: `handle_parse_result` → `process_value` → `type_cast_value`

2. Command resolution failure in `Group.resolve_command`
   - Error: Unknown command name
   - Silent exit: Returns `None` if `ctx.resilient_parsing=True`
   - Chain: `resolve_command` → `get_command` → `fail` (if not resilient)

3. Context creation failure in `Group.invoke`
   - Error: Invalid subcommand context
   - Silent exit: Returns `None` if `ctx.resilient_parsing=True`
   - Chain: `invoke` → `resolve_command` → `make_context`

4. Parameter source resolution failure in `Parameter.consume_value`
   - Error: No valid source found for parameter
   - Silent exit: Uses default value (may be UNSET)
   - Chain: `consume_value` → `value_from_envvar` → `get_default`

## Step 3: The Silent Exits
Silent failure points and blocking contracts:

| Chain | Corruption Entry | Hops | Exit Type | Missing Check | Blocking Contract |
|-------|-----------------|------|-----------|----------------|------------------|
| Parameter processing | `type_cast_value` failure | 1 | Silent | Type conversion validation | Input must match parameter type |
| Command resolution | `get_command` returns None | 1 | Deferred | Command existence check | Valid command name required |
| Context creation | `make_context` fails | 2 | Silent | Context validation | Parent context must be valid |
| Parameter sourcing | All sources fail | 2 | Silent | Parameter source validation | Parameter must have at least one source |
| Group invoke | No protected args | 1 | Silent | Command presence check | Command must be provided when required |
| Result processing | `_process_result` fails | 1 | Deferred | Result callback validation | Result must be processable by callback |

State conservation law: The framework maintains consistency by ensuring either:
1. All operations complete successfully with updated state
2. Operations fail with exceptions that clean up state
3. In resilient mode, operations silently skip problematic elements while preserving valid state
