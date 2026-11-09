"""Association rules of the cockpit-trial monitor (plan 2026-11-09, Task 4)."""
from report import Row, Wait, match_waits, parse_check_log

STEP = 1.0  # 1 s polling


def w(key="herdr-w1-p3", ask="tool", enter=100.0, leave=110.0):
    return Wait(key=key, ask=ask, enter=enter, leave=leave)


def r(ts, state, pane="w1:p3", message=None):
    return Row(ts=ts, pane=pane, state=state, message=message)


def test_seen_missed_per_ask_type():
    waits = [w(ask="tool", enter=100, leave=110), w(ask="permission", enter=200, leave=210),
             w(ask="prose", enter=300, leave=310)]
    rows = [r(100.5, "blocked"), r(111, "working"), r(201, "blocked"), r(211, "working"),
            r(305, "idle")]
    c = match_waits(waits, rows, STEP)
    assert (c["tool"].seen, c["permission"].seen, c["prose"].seen) == (1, 1, 0)
    assert c["prose"].missed == 1 and c["tool"].missed == 0


def test_blocked_before_window_and_still_blocked_is_seen():
    c = match_waits([w(enter=100, leave=110)], [r(50, "blocked")], STEP)
    assert c["tool"].seen == 1


def test_false_blocked():
    c = match_waits([w(enter=100, leave=110)], [r(100.2, "blocked"), r(111, "idle"), r(500, "blocked")], STEP)
    assert c["_all"].false_blocked == 1


def test_too_short_not_missed():
    c = match_waits([w(enter=100, leave=101.5)], [], STEP)
    assert c["tool"].too_short == 1 and c["tool"].missed == 0 and c["tool"].waits == 1


def test_events_mode_has_no_too_short():
    c = match_waits([w(enter=100, leave=100.5)], [], 0.0)
    assert c["tool"].too_short == 0 and c["tool"].missed == 1


def test_text_shown_needs_a_message_on_the_blocked_row():
    c = match_waits([w(enter=100, leave=110), w(enter=200, leave=210)],
                    [r(100.5, "blocked", message="Which parser?"), r(111, "idle"), r(201, "blocked")], STEP)
    assert c["tool"].text_shown == 1 and c["tool"].seen == 2


def test_join_uses_sanitized_pane_id():
    waits = [w(key="herdr-w1-p3")]
    assert match_waits(waits, [r(101, "blocked", pane="w1:p31")], STEP)["tool"].seen == 0
    assert match_waits(waits, [r(101, "blocked", pane="w1:p3")], STEP)["tool"].seen == 1


def test_enter_without_leave_closes_at_next_enter_and_tmux_keys_are_skipped():
    log = "\n".join([
        "100\ts1\tenter\ttool\therdr-w1-p3",
        "200\ts1\tenter\tprose\therdr-w1-p3",
        "210\ts1\tleave\tprose\therdr-w1-p3",
        "300\ts2\tenter\ttool\t42",           # tmux pane: not part of the Herdr trial
        "400\ts3\tenter\tpermission",         # old 4-column line: skipped
    ])
    waits = parse_check_log(log, end=1000)
    assert [(x.ask, x.enter, x.leave) for x in waits] == [("tool", 100, 200), ("prose", 200, 210)]


def test_open_wait_at_end_of_log_ends_at_end():
    waits = parse_check_log("100\ts1\tenter\ttool\therdr-w1-p3", end=150)
    assert waits[0].leave == 150
