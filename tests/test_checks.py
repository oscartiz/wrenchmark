from wrenchmark.agent import Episode, ToolCall
from wrenchmark.tasks import Task, grade


def ep(calls=None, answer=""):
    return Episode(final_answer=answer, calls=calls or [])


def task_with(checks):
    return Task(id="t", tier=1, prompt="p", tools=["get_weather"],
                checks=checks, reference=[])


def test_tool_called_with_tolerant_args():
    episode = ep([ToolCall("get_weather", {"city": "Paris, France"}, "ok")])
    t = task_with([{"type": "tool_called", "tool": "get_weather",
                    "args_subset": {"city": "paris"}}])
    assert grade(t, episode).success


def test_tool_called_numeric_tolerance():
    episode = ep([ToolCall("convert_currency",
                           {"amount": 100.0, "from_currency": "EUR"}, "ok")])
    t = task_with([{"type": "tool_called", "tool": "convert_currency",
                    "args_subset": {"amount": 100}}])
    assert grade(t, episode).success


def test_tool_not_called_star():
    t = task_with([{"type": "tool_not_called", "tool": "*"}])
    assert grade(t, ep()).success
    assert not grade(t, ep([ToolCall("get_weather", {}, "ok")])).success


def test_final_answer_any_and_all():
    t_any = task_with([{"type": "final_answer_contains", "any": ["17", "warm"]}])
    assert grade(t_any, ep(answer="It is 17C")).success
    assert not grade(t_any, ep(answer="It is cold")).success
    t_all = task_with([{"type": "final_answer_contains", "all": ["17", "cloudy"]}])
    assert grade(t_all, ep(answer="17°C and cloudy")).success
    assert not grade(t_all, ep(answer="17°C and sunny")).success


def test_args_contains():
    episode = ep([ToolCall("send_message",
                           {"recipient": "Carol", "body": "Bring an umbrella!"}, "ok")])
    t = task_with([{"type": "tool_called", "tool": "send_message",
                    "args_contains": {"body": ["umbrella", "rain"]}}])
    assert grade(t, episode).success


def test_episode_error_fails():
    t = task_with([{"type": "final_answer_contains", "any": ["x"]}])
    bad = Episode(error="ConnectionError: boom")
    assert not grade(t, bad).success
