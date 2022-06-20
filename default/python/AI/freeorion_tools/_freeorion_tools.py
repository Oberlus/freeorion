# This Python file uses the following encoding: utf-8
import freeOrionAIInterface as fo
import inspect
import pprint
import re
import traceback
from collections.abc import Mapping
from functools import wraps
from logging import ERROR, Handler, debug, error, getLogger, warning

import AIDependencies
from common.configure_logging import FOLogFormatter
from freeorion_tools.caching import cache_for_current_turn, cache_for_session

# color wrappers for chat:
RED = "<rgba 255 0 0 255>%s</rgba>"
WHITE = "<rgba 255 255 255 255>%s</rgba>"


def dict_from_map(thismap):
    """Convert C++ map to python dict."""
    return {el.key(): el.data() for el in thismap}


def dict_from_map_recursive(thismap):
    retval = {}
    try:
        for el in thismap:
            retval[el.key()] = dict_from_map_recursive(el.data())
        return retval
    except Exception:
        return dict_from_map(thismap)


def get_ai_tag_grade(tag_list, tag_type):
    """
    Accepts a list of string tags and a tag_type (like 'WEAPONS').
    Checks for the first tag in the list (if any), for tag_type "TYPE",
    having the structure X_TYPE
    and then returns 'X'
    X is most commonly (but not necessarily) one of [NO, VERY_BAD, BAD, AVERAGE, GOOD, GREAT, ULTIMATE]
    If no matching tags, returns empty string (which for most types should be considered equivalent to AVERAGE)
    """
    for tag in [tag_ for tag_ in tag_list if tag_.count("_") > 0]:
        parts = tag.split("_", 1)
        if parts[1].startswith("BAD_"):
            parts = [parts[0] + "_BAD", parts[1][4:]]
        if parts[1] == tag_type.upper():
            return parts[0]
    return ""


def tech_is_complete(tech):
    """
    Return if tech is complete.
    """
    return fo.getEmpire().techResearched(tech)


def policy_is_adopted(policy):
    """
    Return if policy is currently adopted.
    """
    return fo.getEmpire().policyAdopted(policy)


def ppstring(foo):
    """
    Returns a string version of lists, dicts, sets, such that entries with special characters will be
    printed in legible string format rather than as hex escape characters, i.e.,
    ['Asimov α'] rather than ['Asimov \xce\xb1']."""

    if isinstance(foo, list):
        return "[" + ",".join(map(ppstring, foo)) + "]"
    elif isinstance(foo, dict):
        return "{" + ",".join([ppstring(k) + ":" + ppstring(v) for k, v in foo.items()]) + "}"
    elif isinstance(foo, tuple):
        return "(" + ",".join(map(ppstring, foo)) + ")"
    elif isinstance(foo, set) or isinstance(foo, frozenset):
        return "{" + ",".join(map(ppstring, foo)) + "}"
    elif isinstance(foo, str):
        return "'" + foo + "'"
    else:
        return str(foo)


class ConsoleLogHandler(Handler):
    """A log handler to send errors to the console."""

    def emit(self, record):
        """Emit a record.

        If a formatter is specified, it is used to format the record and then sent to human players."""
        try:
            human_ids = [x for x in fo.allPlayerIDs() if fo.playerIsHost(x)]
            if not human_ids:
                return
            msg = self.format(record)

            for human_id in human_ids:
                fo.sendChatMessage(human_id, msg)
        except (KeyboardInterrupt, SystemExit):
            raise
        # Hide errors from within the ConsoleLogHandler
        except:  # noqa: E722
            self.handleError(record)


# Create the log handler, format it and attach it to the root logger
console_handler = ConsoleLogHandler()

console_handler.setFormatter(
    FOLogFormatter(
        RED % ("%s : %%(filename)s:%%(funcName)s():%%(lineno)d  - %%(message)s" % fo.userString("AI_ERROR_MSG"))
    )
)

console_handler.setLevel(ERROR)

getLogger().addHandler(console_handler)


def remove_tags(message):
    """Remove tags described in Font.h from message."""
    expr = r"</?(i|u|(rgba ([0-1]\.)?\d+ ([0-1]\.)?\d+ ([0-1]\.)?\d+ ([0-1]\.)?\d+)|rgba|left|center|right|pre)>"
    return re.sub(expr, "", message)


def chat_human(message, send_to_logs=True):
    """
    Send chat message to human and print it to log.
    Log message cleared form tags.
    """
    human_id = [x for x in fo.allPlayerIDs() if fo.playerIsHost(x)][0]
    message = str(message)
    fo.sendChatMessage(human_id, message)
    if send_to_logs:
        debug("Chat Message to human: %s", remove_tags(message))


def dict_to_tuple(dic):
    return tuple(dic.items())


def tuple_to_dict(tup):
    try:
        return dict(tup)
    except TypeError:
        try:
            return {k: v for k, v in [tup]}
        except:  # noqa: E722
            error("Can't convert tuple_list to dict: %s", tup)
            return {}


@cache_for_current_turn
def get_partial_visibility_turn(obj_id: int) -> int:
    """Return the last turn an object had at least partial visibility.

    :return: Last turn an object had at least partial visibility, -9999 if never
    """
    visibility_turns_map = fo.getUniverse().getVisibilityTurnsMap(obj_id, fo.empireID())
    return visibility_turns_map.get(fo.visibility.partial, -9999)


class ReadOnlyDict(Mapping):
    """A dict that offers only read access.

    Note that if the values of the ReadOnlyDict are mutable,
    then those objects may actually be changed.

    It is strongly advised to store only immutable objects.
    A slight protection is offered by checking for hashability of the values.

     Example usage:
     my_dict = ReadOnlyDict({1:2, 3:4})
     print my_dict[1]
     for k in my_dict:
         print my_dict.get(k, -1)
     for k in my_dict.keys():
         print my_dict[k]
     for k, v in my_dict.iteritems():
         print k, v
     my_dict[5] = 4  # throws TypeError
     del my_dict[1]  # throws TypeError

     Implementation note:

    The checks that values are hashable is the main difference from the built-in types.MappingProxyType.
    MappingProxyType has slightly different signature and cannot be inherited.
    """

    def __init__(self, *args, **kwargs):
        self._data = dict(*args, **kwargs)
        for k, v in self._data.items():
            try:
                hash(v)
            except TypeError:
                error("Tried to store a non-hashable value in ReadOnlyDict")
                raise

    def __getitem__(self, item):
        return self._data[item]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __str__(self):
        return str(self._data)


def dump_universe():
    """Dump the universe but not more than once per turn."""
    cur_turn = fo.currentTurn()

    if not hasattr(dump_universe, "last_dump") or dump_universe.last_dump < cur_turn:
        dump_universe.last_dump = cur_turn
        fo.getUniverse().dump()  # goes to debug logger


class LogLevelSwitcher:
    """A context manager class which controls the log level within its scope.

    Example usage:
    logging.getLogger().setLevel(logging.INFO)

    debug("Some message")  # not printed because of log level
    with LogLevelSwitcher(logging.DEBUG):
        debug("foo")  # printed because we set to DEBUG level

    debug("baz")  # not printed, we are back to INFO level
    """

    def __init__(self, log_level):
        self.target_log_level = log_level
        self.old_log_level = 0

    def __enter__(self):
        self.old_log_level = getLogger().level
        getLogger().setLevel(self.target_log_level)

    def __exit__(self, exc_type, exc_val, exc_tb):
        getLogger().setLevel(self.old_log_level)


def with_log_level(log_level):
    """A decorator to set a specific logging level for the function call.

    This decorator is useful to selectively activate debugging for a specific function
    while the rest of the code base only logs at a higher level.

    If functions are called within the decorated function, then those will be
    executed with the same logging level. However, if those functions use this
    decorator as well, then that logging level will be respected for its scope.

    Example usage:
    @log_with_specific_log_level(logging.DEBUG)
    def foo():
        debug("debug stuff")
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with LogLevelSwitcher(log_level):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def assertion_fails(cond: bool, msg: str = "") -> bool:
    """
    Check if condition fails and if so, log a traceback but raise no Exception.

    Return False is condition True and True if condition is False.

    This is a useful functions for generic sanity checks and may be used to
    replace manual error logging with more context provided by the traceback.
    """
    if cond:
        return False

    if msg:
        header = "AI raised a warning: %s. See more detailed description in logs." % msg
    else:
        header = "AI raised a warning. See more detailed description in logs."

    warning("\n===")
    error(header)
    stack = traceback.extract_stack()[:-1]  # do not log this function
    warning("Stack trace (most recent call last): %s", "".join(traceback.format_list(stack)))
    frame = inspect.currentframe().f_back
    local_vars = pprint.pformat(frame.f_locals)
    warning("Locals inside the {}\n{}".format(frame.f_code.co_name, local_vars))
    warning("===\n")
    return True


@cache_for_session
def get_species_tag_grade(species_name: str, tag_type: AIDependencies.Tags) -> str:
    """Determine grade string ("NO", "BAD", "GOOD", etc.), if any, for given tag and species."""
    if not species_name:
        return ""
    species = fo.getSpecies(species_name)
    if assertion_fails(species is not None):
        return ""

    return get_ai_tag_grade(species.tags, tag_type)


@cache_for_session
def get_species_tag_value(species_name: str, tag_type: AIDependencies.Tags) -> float:
    """Get a numeric value for a skill-like (GOOD, BAD...) Tag."""
    grade = get_species_tag_grade(species_name, tag_type)
    if tag_type == AIDependencies.Tags.INDUSTRY:
        return AIDependencies.SPECIES_INDUSTRY_MODIFIER.get(grade, 1.0)
    if tag_type == AIDependencies.Tags.RESEARCH:
        return AIDependencies.SPECIES_RESEARCH_MODIFIER.get(grade, 1.0)
    if tag_type == AIDependencies.Tags.INFLUENCE:
        return AIDependencies.SPECIES_INFLUENCE_MODIFIER.get(grade, 1.0)
    if tag_type == AIDependencies.Tags.POPULATION:
        return AIDependencies.SPECIES_POPULATION_MODIFIER.get(grade, 1.0)
    if tag_type == AIDependencies.Tags.SUPPLY:
        return AIDependencies.SPECIES_SUPPLY_MODIFIER.get(grade, 1.0)
    if tag_type == AIDependencies.Tags.STABILITY:
        return AIDependencies.SPECIES_STABILITY_MODIFIER.get(grade, 0.0)
    if tag_type == AIDependencies.Tags.FUEL:
        return AIDependencies.SPECIES_FUEL_MODIFIER.get(grade, 0.0)
    if tag_type == AIDependencies.Tags.ATTACKTROOPS:
        return AIDependencies.SPECIES_TROOP_MODIFIER.get(grade, 1.0)
    if tag_type == AIDependencies.Tags.STEALTH:
        return AIDependencies.STEALTH_STRENGTHS_BY_SPECIES_TAG.get(grade, 0.0)


@cache_for_session
def get_ship_part(part_name: str):
    """Return the shipPart object (fo.getShipPart(part_name)) of the given part_name.

    As the function in late game may be called some thousand times, the results are cached.
    """
    if not part_name:
        return None

    part_type = fo.getShipPart(part_name)
    if not part_type:
        warning("Could not find part %s" % part_name)

    return part_type


def get_named_int(name: str) -> int:
    """
    Returns a NamedReal from FOCS.
    If the value does not exist, reports an error and returns 1.
    Note that we do not raise and exception so that the AI can continue, as good as it can, with outdated information.
    This is also why we return 1, returning 0 could cause followup errors if the value is used as divisor.
    """
    value = fo.getNamedValue(name)
    if value is None:
        error(f"Requested NamedInt {name}, which doesn't exist!")
        value = 1
    elif not isinstance(value, int):
        error(f"Requested value {name} of type int got {type(value)}!")
        value = 1
    return value


def get_named_real(name: str) -> float:
    """
    Returns a NamedReal from FOCS.
    If the value does not exist, reports an error and returns 1.0.
    Note that we do not raise and exception so that the AI can continue, as good as it can, with outdated information.
    This is also why we return 1, returning 0 could cause followup errors if the value is used as divisor.
    """
    value = fo.getNamedValue(name)
    if value is None:
        error(f"Requested NamedReal {name}, which doesn't exist!")
        value = 1.0
    elif not isinstance(value, float):
        error(f"Requested value {name} of type float got {type(value)}!")
        value = 1.0
    return value
