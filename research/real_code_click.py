# From: https://github.com/pallets/click/blob/main/src/click/core.py
# License: BSD 3-Clause (c) Pallets. Used as analysis test target.
# Click CLI framework: Context inheritance, Command dispatch, Group chaining, Parameter resolution
# Stripped docstrings for brevity. Full file is 3418 lines.

import collections.abc as cabc
import enum, errno, inspect, os, sys
from collections import abc
from contextlib import ExitStack
from functools import update_wrapper
from gettext import gettext as _, ngettext


class ParameterSource(enum.Enum):
    COMMANDLINE = "commandline"
    ENVIRONMENT = "environment"
    DEFAULT = "default"
    DEFAULT_MAP = "default_map"
    PROMPT = "prompt"


class Context:
    formatter_class = HelpFormatter

    def __init__(self, command, parent=None, info_name=None, obj=None,
                 auto_envvar_prefix=None, default_map=None, terminal_width=None,
                 max_content_width=None, resilient_parsing=False, allow_extra_args=None,
                 allow_interspersed_args=None, ignore_unknown_options=None,
                 help_option_names=None, token_normalize_func=None, color=None,
                 show_default=None):
        self.parent = parent
        self.command = command
        self.info_name = info_name
        self.params = {}
        self.args = []
        self._protected_args = []
        self._opt_prefixes = set(parent._opt_prefixes) if parent else set()

        if obj is None and parent is not None:
            obj = parent.obj
        self.obj = obj
        self._meta = parent._meta.copy() if parent and hasattr(parent, '_meta') else {}

        if (default_map is None and info_name is not None
                and parent is not None and parent.default_map is not None):
            default_map = parent.default_map.get(info_name)
        self.default_map = default_map

        self.invoked_subcommand = None

        if terminal_width is None and parent is not None:
            terminal_width = parent.terminal_width
        self.terminal_width = terminal_width

        if max_content_width is None and parent is not None:
            max_content_width = parent.max_content_width
        self.max_content_width = max_content_width

        if allow_extra_args is None:
            allow_extra_args = command.allow_extra_args
        self.allow_extra_args = allow_extra_args

        if allow_interspersed_args is None:
            allow_interspersed_args = command.allow_interspersed_args
        self.allow_interspersed_args = allow_interspersed_args

        if ignore_unknown_options is None:
            ignore_unknown_options = command.ignore_unknown_options
        self.ignore_unknown_options = ignore_unknown_options

        if help_option_names is None:
            if parent is not None:
                help_option_names = parent.help_option_names
            else:
                help_option_names = ["--help"]
        self.help_option_names = help_option_names

        if token_normalize_func is None and parent is not None:
            token_normalize_func = parent.token_normalize_func
        self.token_normalize_func = token_normalize_func

        self.resilient_parsing = resilient_parsing
        if auto_envvar_prefix is None:
            if parent is not None and parent.auto_envvar_prefix is not None and self.info_name is not None:
                auto_envvar_prefix = (parent.auto_envvar_prefix + "_" + self.info_name.upper().replace("-", "_"))
        self.auto_envvar_prefix = auto_envvar_prefix

        if color is None and parent is not None:
            color = parent.color
        self.color = color

        if show_default is None and parent is not None:
            show_default = parent.show_default
        self.show_default = show_default

        self._close_callbacks = []
        self._exit_stack = ExitStack()
        self._depth = parent._depth + 1 if parent is not None else 0
        self._context_entered = False

    def invoke(self, callback, *args, **kwargs):
        with augment_usage_errors(self):
            if self._context_entered:
                return callback(*args, **kwargs)
            self._context_entered = True
            try:
                with self:
                    return callback(*args, **kwargs)
            finally:
                self._context_entered = False

    def forward(self, cmd, *args, **kwargs):
        return self.invoke(cmd, self, *args, **self.params, **kwargs)

    def lookup_default(self, name, call=True):
        if self.default_map is not None:
            value = self.default_map.get(name, UNSET)
            if call and callable(value):
                value = value()
            return value
        return UNSET

    def scope(self, cleanup=True):
        return _ContextScope(self, cleanup)


class Command:
    context_class = Context
    allow_extra_args = False
    allow_interspersed_args = True
    ignore_unknown_options = False

    def __init__(self, name, context_settings=None, callback=None, params=None,
                 help=None, epilog=None, short_help=None, options_metavar="[OPTIONS]",
                 add_help_option=True, no_args_is_help=False, hidden=False, deprecated=False):
        self.name = name
        if context_settings is None:
            context_settings = {}
        self.context_settings = context_settings
        self.callback = callback
        self.params = params or []
        self.help = help
        self.epilog = epilog
        self.options_metavar = options_metavar
        self.short_help = short_help
        self.add_help_option = add_help_option
        self._help_option = None
        self.no_args_is_help = no_args_is_help
        self.hidden = hidden
        self.deprecated = deprecated

    def make_context(self, info_name, args, parent=None, **extra):
        for key, value in self.context_settings.items():
            if key not in extra:
                extra[key] = value
        ctx = self.context_class(self, info_name=info_name, parent=parent, **extra)
        with ctx.scope(cleanup=False):
            self.parse_args(ctx, args)
        return ctx

    def parse_args(self, ctx, args):
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            raise NoArgsIsHelpError(ctx)
        parser = self.make_parser(ctx)
        opts, args, param_order = parser.parse_args(args=args)
        for param in iter_params_for_processing(param_order, self.get_params(ctx)):
            _, args = param.handle_parse_result(ctx, opts, args)
        for name, value in ctx.params.items():
            if value is UNSET:
                ctx.params[name] = None
        if args and not ctx.allow_extra_args and not ctx.resilient_parsing:
            ctx.fail(ngettext(
                "Got unexpected extra argument ({args})",
                "Got unexpected extra arguments ({args})",
                len(args),
            ).format(args=" ".join(map(str, args))))
        ctx.args = args
        ctx._opt_prefixes.update(parser._opt_prefixes)
        return args

    def invoke(self, ctx):
        if self.deprecated:
            extra_message = f" {self.deprecated}" if isinstance(self.deprecated, str) else ""
            message = _("DeprecationWarning: The command {name!r} is deprecated.{extra_message}").format(
                name=self.name, extra_message=extra_message)
            echo(style(message, fg="red"), err=True)
        if self.callback is not None:
            return ctx.invoke(self.callback, **ctx.params)

    def main(self, args=None, prog_name=None, complete_var=None,
             standalone_mode=True, windows_expand_args=True, **extra):
        if args is None:
            args = sys.argv[1:]
            if os.name == "nt" and windows_expand_args:
                args = _expand_args(args)
        else:
            args = list(args)
        if prog_name is None:
            prog_name = _detect_program_name()
        self._main_shell_completion(extra, prog_name, complete_var)
        try:
            try:
                with self.make_context(prog_name, args, **extra) as ctx:
                    rv = self.invoke(ctx)
                    if not standalone_mode:
                        return rv
                    ctx.exit()
            except (EOFError, KeyboardInterrupt) as e:
                echo(file=sys.stderr)
                raise Abort() from e
            except ClickException as e:
                if not standalone_mode:
                    raise
                e.show()
                sys.exit(e.exit_code)
            except OSError as e:
                if e.errno == errno.EPIPE:
                    sys.stdout = PacifyFlushWrapper(sys.stdout)
                    sys.stderr = PacifyFlushWrapper(sys.stderr)
                    sys.exit(1)
                else:
                    raise
        except Exit as e:
            if standalone_mode:
                sys.exit(e.exit_code)
            else:
                return e.exit_code
        except Abort:
            if not standalone_mode:
                raise
            echo(_("Aborted!"), file=sys.stderr)
            sys.exit(1)

    def __call__(self, *args, **kwargs):
        return self.main(*args, **kwargs)


class Group(Command):
    allow_extra_args = True
    allow_interspersed_args = False
    command_class = None
    group_class = None

    def __init__(self, name=None, commands=None, invoke_without_command=False,
                 no_args_is_help=None, subcommand_metavar=None, chain=False,
                 result_callback=None, **kwargs):
        super().__init__(name, **kwargs)
        if commands is None:
            commands = {}
        elif isinstance(commands, abc.Sequence):
            commands = {c.name: c for c in commands if c.name is not None}
        self.commands = commands
        if no_args_is_help is None:
            no_args_is_help = not invoke_without_command
        self.no_args_is_help = no_args_is_help
        self.invoke_without_command = invoke_without_command
        if subcommand_metavar is None:
            if chain:
                subcommand_metavar = "COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]..."
            else:
                subcommand_metavar = "COMMAND [ARGS]..."
        self.subcommand_metavar = subcommand_metavar
        self.chain = chain
        self._result_callback = result_callback

    def add_command(self, cmd, name=None):
        name = name or cmd.name
        if name is None:
            raise TypeError("Command has no name.")
        _check_nested_chain(self, name, cmd, register=True)
        self.commands[name] = cmd

    def get_command(self, ctx, cmd_name):
        return self.commands.get(cmd_name)

    def list_commands(self, ctx):
        return sorted(self.commands)

    def parse_args(self, ctx, args):
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            raise NoArgsIsHelpError(ctx)
        rest = super().parse_args(ctx, args)
        if self.chain:
            ctx._protected_args = rest
            ctx.args = []
        elif rest:
            ctx._protected_args, ctx.args = rest[:1], rest[1:]
        return ctx.args

    def invoke(self, ctx):
        def _process_result(value):
            if self._result_callback is not None:
                value = ctx.invoke(self._result_callback, value, **ctx.params)
            return value

        if not ctx._protected_args:
            if self.invoke_without_command:
                with ctx:
                    rv = super().invoke(ctx)
                    return _process_result([] if self.chain else rv)
            ctx.fail(_("Missing command."))

        args = [*ctx._protected_args, *ctx.args]
        ctx.args = []
        ctx._protected_args = []

        if not self.chain:
            with ctx:
                cmd_name, cmd, args = self.resolve_command(ctx, args)
                if cmd is None and ctx.resilient_parsing:
                    return None
                assert cmd is not None
                ctx.invoked_subcommand = cmd_name
                super().invoke(ctx)
                sub_ctx = cmd.make_context(cmd_name, args, parent=ctx)
                with sub_ctx:
                    return _process_result(sub_ctx.command.invoke(sub_ctx))

        with ctx:
            ctx.invoked_subcommand = "*" if args else None
            super().invoke(ctx)
            contexts = []
            while args:
                cmd_name, cmd, args = self.resolve_command(ctx, args)
                if cmd is None and ctx.resilient_parsing:
                    break
                assert cmd is not None
                sub_ctx = cmd.make_context(cmd_name, args, parent=ctx,
                                           allow_extra_args=True,
                                           allow_interspersed_args=False)
                contexts.append(sub_ctx)
                args, sub_ctx.args = sub_ctx.args, []
            rv = []
            for sub_ctx in contexts:
                with sub_ctx:
                    rv.append(sub_ctx.command.invoke(sub_ctx))
            return _process_result(rv)

    def resolve_command(self, ctx, args):
        cmd_name = make_str(args[0])
        original_cmd_name = cmd_name
        cmd = self.get_command(ctx, cmd_name)
        if cmd is None and ctx.token_normalize_func is not None:
            cmd_name = ctx.token_normalize_func(cmd_name)
            cmd = self.get_command(ctx, cmd_name)
        if cmd is None and not ctx.resilient_parsing:
            if _split_opt(cmd_name)[0]:
                self.parse_args(ctx, args)
            ctx.fail(_("No such command {name!r}.").format(name=original_cmd_name))
        return cmd_name if cmd else None, cmd, args[1:]


class Parameter:
    param_type_name = "parameter"

    def __init__(self, param_decls=None, type=None, required=False, default=UNSET,
                 callback=None, nargs=None, multiple=False, metavar=None,
                 expose_value=True, is_eager=False, envvar=None,
                 shell_complete=None, deprecated=False):
        self.name, self.opts, self.secondary_opts = self._parse_decls(param_decls or (), expose_value)
        self.type = convert_type(type, default)
        if nargs is None:
            if self.type.is_composite:
                nargs = self.type.arity
            else:
                nargs = 1
        self.required = required
        self.callback = callback
        self.nargs = nargs
        self.multiple = multiple
        self.expose_value = expose_value
        self.default = default
        self.is_eager = is_eager
        self.metavar = metavar
        self.envvar = envvar
        self._custom_shell_complete = shell_complete
        self.deprecated = deprecated

    def consume_value(self, ctx, opts):
        value = opts.get(self.name, UNSET)
        source = ParameterSource.COMMANDLINE if value is not UNSET else ParameterSource.DEFAULT
        if value is UNSET:
            envvar_value = self.value_from_envvar(ctx)
            if envvar_value is not None:
                value = envvar_value
                source = ParameterSource.ENVIRONMENT
        if value is UNSET:
            default_map_value = ctx.lookup_default(self.name)
            if default_map_value is not UNSET:
                value = default_map_value
                source = ParameterSource.DEFAULT_MAP
        if value is UNSET:
            default_value = self.get_default(ctx)
            if default_value is not UNSET:
                value = default_value
                source = ParameterSource.DEFAULT
        return value, source

    def type_cast_value(self, ctx, value):
        if value is None:
            if self.multiple or self.nargs == -1:
                return ()
            else:
                return value
        def check_iter(value):
            try:
                return _check_iter(value)
            except TypeError:
                if self.nargs != 1:
                    return (value,)
                raise
        value = self.type.convert(value, self, ctx)
        return check_iter(value)

    def process_value(self, ctx, value):
        value = self.type_cast_value(ctx, value)
        if self.required and self.value_is_missing(value):
            raise MissingParameter(ctx=ctx, param=self)
        if self.callback is not None and not ctx.resilient_parsing:
            value = ctx.invoke(self.callback, ctx=ctx, param=self, value=value)
        return value

    def handle_parse_result(self, ctx, opts, args):
        with augment_usage_errors(ctx, param=self):
            value, source = self.consume_value(ctx, opts)
            value = self.process_value(ctx, value)
        if self.expose_value:
            ctx.params[self.name] = value
        if source is not None:
            ctx.set_parameter_source(self.name, source)
        return value, args
