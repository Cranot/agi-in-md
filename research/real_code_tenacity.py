# From: https://github.com/jd/tenacity/blob/main/tenacity/__init__.py
# License: Apache 2.0 (c) Julien Danjou. Used as analysis test target.
# Tenacity retry library: Strategy composition, action chains, state tracking
# Stripped docstrings for brevity. Full file is ~550 lines.

import contextvars, dataclasses, functools, sys, threading, time
from abc import ABC, abstractmethod
from concurrent import futures

_iter_state_var = contextvars.ContextVar('iter_state', default=None)

@dataclasses.dataclass(slots=True)
class IterState:
    actions: list = dataclasses.field(default_factory=list)
    retry_run_result: bool = False
    stop_run_result: bool = False
    is_explicit_retry: bool = False

    def reset(self):
        self.actions = []
        self.retry_run_result = False
        self.stop_run_result = False
        self.is_explicit_retry = False


class RetrySignal(Exception):
    """Control signal for explicit retry, not a real exception."""
    pass

NO_RESULT = object()

class DoAttempt:
    pass

class DoSleep(float):
    pass


class RetryAction:
    REPR_FIELDS = ("sleep",)
    NAME = "retry"

    def __init__(self, sleep):
        self.sleep = float(sleep)


_unset = object()

def _first_set(first, second):
    return second if first is _unset else first


class RetryError(Exception):
    def __init__(self, last_attempt):
        self.last_attempt = last_attempt
        super().__init__(last_attempt)

    def reraise(self):
        if self.last_attempt.failed:
            raise self.last_attempt.result()
        raise self


class AttemptManager:
    def __init__(self, retry_state):
        self.retry_state = retry_state
        self._result_set = False

    def __enter__(self):
        pass

    def set_result(self, value):
        self.retry_state.set_result(value)
        self._result_set = True

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None and exc_value is not None:
            self.retry_state.set_exception((exc_type, exc_value, traceback))
            return True
        if not self._result_set:
            self.retry_state.set_result(None)
        return None


class BaseRetrying(ABC):
    def __init__(self, sleep=time.sleep, stop=stop_never, wait=wait_none(),
                 retry=retry_if_exception_type(), before=before_nothing,
                 after=after_nothing, before_sleep=None, reraise=False,
                 retry_error_cls=RetryError, retry_error_callback=None,
                 name=None, enabled=True):
        self.sleep = sleep
        self.stop = stop
        self.wait = wait
        self.retry = retry
        self.before = before
        self.after = after
        self.before_sleep = before_sleep
        self.reraise = reraise
        self._local = threading.local()
        self.retry_error_cls = retry_error_cls
        self.retry_error_callback = retry_error_callback
        self._name = name
        self.enabled = enabled

    def copy(self, sleep=_unset, stop=_unset, wait=_unset, retry=_unset,
             before=_unset, after=_unset, before_sleep=_unset, reraise=_unset,
             retry_error_cls=_unset, retry_error_callback=_unset,
             name=_unset, enabled=_unset):
        return self.__class__(
            sleep=_first_set(sleep, self.sleep),
            stop=_first_set(stop, self.stop),
            wait=_first_set(wait, self.wait),
            retry=_first_set(retry, self.retry),
            before=_first_set(before, self.before),
            after=_first_set(after, self.after),
            before_sleep=_first_set(before_sleep, self.before_sleep),
            reraise=_first_set(reraise, self.reraise),
            retry_error_cls=_first_set(retry_error_cls, self.retry_error_cls),
            retry_error_callback=_first_set(retry_error_callback, self.retry_error_callback),
            name=_first_set(name, self._name),
            enabled=_first_set(enabled, self.enabled),
        )

    @property
    def statistics(self):
        if not hasattr(self._local, "statistics"):
            self._local.statistics = {}
        if len(self._local.statistics) > 100:
            self._local.statistics.clear()
        return self._local.statistics

    @property
    def iter_state(self):
        state = _iter_state_var.get()
        if state is None:
            state = IterState()
            _iter_state_var.set(state)
        return state

    def wraps(self, f):
        @functools.wraps(f, functools.WRAPPER_ASSIGNMENTS + ("__defaults__", "__kwdefaults__"))
        def wrapped_f(*args, **kw):
            if not self.enabled:
                return f(*args, **kw)
            copy = self.copy()
            wrapped_f.statistics = copy.statistics
            return copy(f, *args, **kw)

        def retry_with(*args, **kwargs):
            return self.copy(*args, **kwargs).wraps(f)

        wrapped_f.retry = self
        wrapped_f.retry_with = retry_with
        wrapped_f.statistics = {}
        return wrapped_f

    def begin(self):
        self.statistics.clear()
        self.statistics["start_time"] = time.monotonic()
        self.statistics["attempt_number"] = 1
        self.statistics["idle_for"] = 0
        self.statistics["delay_since_first_attempt"] = 0

    def _add_action_func(self, fn):
        self.iter_state.actions.append(fn)

    def _run_retry(self, retry_state):
        self.iter_state.retry_run_result = self.retry(retry_state)

    def _run_wait(self, retry_state):
        if self.wait:
            sleep = self.wait(retry_state)
        else:
            sleep = 0.0
        retry_state.upcoming_sleep = sleep

    def _run_stop(self, retry_state):
        self.statistics["delay_since_first_attempt"] = retry_state.seconds_since_start
        self.iter_state.stop_run_result = self.stop(retry_state)

    def iter(self, retry_state):
        self._begin_iter(retry_state)
        result = None
        for action in list(self.iter_state.actions):
            result = action(retry_state)
        return result

    def _begin_iter(self, retry_state):
        self.iter_state.reset()
        fut = retry_state.outcome
        if fut is None:
            if self.before is not None:
                self._add_action_func(self.before)
            self._add_action_func(lambda rs: DoAttempt())
            return
        self.iter_state.is_explicit_retry = fut.failed and isinstance(fut.exception(), RetrySignal)
        if not self.iter_state.is_explicit_retry:
            self._add_action_func(self._run_retry)
        self._add_action_func(self._post_retry_check_actions)

    def _post_retry_check_actions(self, retry_state):
        if not (self.iter_state.is_explicit_retry or self.iter_state.retry_run_result):
            self._add_action_func(lambda rs: rs.outcome.result())
            return
        if self.after is not None:
            self._add_action_func(self.after)
        self._add_action_func(self._run_wait)
        self._add_action_func(self._run_stop)
        self._add_action_func(self._post_stop_check_actions)

    def _post_stop_check_actions(self, retry_state):
        if self.iter_state.stop_run_result:
            if self.retry_error_callback:
                self._add_action_func(self.retry_error_callback)
                return

            def exc_check(rs):
                fut = rs.outcome
                retry_exc = self.retry_error_cls(fut)
                if self.reraise:
                    retry_exc.reraise()
                raise retry_exc from fut.exception()

            self._add_action_func(exc_check)
            return

        def next_action(rs):
            sleep = rs.upcoming_sleep
            rs.next_action = RetryAction(sleep)
            rs.idle_for += sleep
            self.statistics["idle_for"] += sleep
            self.statistics["attempt_number"] += 1

        self._add_action_func(next_action)
        if self.before_sleep is not None:
            self._add_action_func(self.before_sleep)
        self._add_action_func(lambda rs: DoSleep(rs.upcoming_sleep))

    def __iter__(self):
        self.begin()
        retry_state = RetryCallState(self, fn=None, args=(), kwargs={})
        while True:
            do = self.iter(retry_state=retry_state)
            if isinstance(do, DoAttempt):
                yield AttemptManager(retry_state=retry_state)
            elif isinstance(do, DoSleep):
                retry_state.prepare_for_next_attempt()
                self.sleep(do)
            else:
                break

    @abstractmethod
    def __call__(self, fn, *args, **kwargs):
        pass


class Retrying(BaseRetrying):
    def __call__(self, fn, *args, **kwargs):
        _iter_state_var.set(IterState())
        self.begin()
        retry_state = RetryCallState(retry_object=self, fn=fn, args=args, kwargs=kwargs)
        while True:
            do = self.iter(retry_state=retry_state)
            if isinstance(do, DoAttempt):
                try:
                    result = fn(*args, **kwargs)
                except BaseException:
                    retry_state.set_exception(sys.exc_info())
                else:
                    retry_state.set_result(result)
            elif isinstance(do, DoSleep):
                retry_state.prepare_for_next_attempt()
                self.sleep(do)
            else:
                return do


class Future(futures.Future):
    def __init__(self, attempt_number):
        super().__init__()
        self.attempt_number = attempt_number

    @property
    def failed(self):
        return self.exception() is not None

    @classmethod
    def construct(cls, attempt_number, value, has_exception):
        fut = cls(attempt_number)
        if has_exception:
            fut.set_exception(value)
        else:
            fut.set_result(value)
        return fut


class RetryCallState:
    def __init__(self, retry_object, fn, args, kwargs):
        self.start_time = time.monotonic()
        self.retry_object = retry_object
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.attempt_number = 1
        self.outcome = None
        self.outcome_timestamp = None
        self.idle_for = 0.0
        self.next_action = None
        self.upcoming_sleep = 0.0

    @property
    def seconds_since_start(self):
        if self.outcome_timestamp is None:
            return None
        return self.outcome_timestamp - self.start_time

    def prepare_for_next_attempt(self):
        self.outcome = None
        self.outcome_timestamp = None
        self.attempt_number += 1
        self.next_action = None

    def set_result(self, val):
        ts = time.monotonic()
        fut = Future(self.attempt_number)
        fut.set_result(val)
        self.outcome, self.outcome_timestamp = fut, ts

    def set_exception(self, exc_info):
        ts = time.monotonic()
        fut = Future(self.attempt_number)
        fut.set_exception(exc_info[1])
        self.outcome, self.outcome_timestamp = fut, ts


def retry(*dargs, **dkw):
    if len(dargs) == 1 and callable(dargs[0]):
        return retry()(dargs[0])

    def wrap(f):
        r = Retrying(*dargs, **dkw)
        return r.wraps(f)

    return wrap
