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


def test_rows_from_real_agent_list():
    from pathlib import Path
    from report import rows_from_agent_list
    text = (Path(__file__).parent / "fixtures" / "agent-list.json").read_text()
    rows = rows_from_agent_list(text, ts=10.0)
    assert {(x.pane, x.state) for x in rows} == {("w1:p1", "working"), ("w1:p2", "blocked")}
    assert all(x.ts == 10.0 and x.message is None for x in rows)


def test_changes_emit_only_changed_panes_and_gone():
    from report import changes
    prev = {"w1:p1": "working", "w1:p2": "blocked"}
    cur = {"w1:p1": "blocked", "w1:p3": "idle"}
    out = changes(prev, cur, ts=5.0)
    assert sorted((x.pane, x.state) for x in out) == [("w1:p1", "blocked"), ("w1:p2", "gone"), ("w1:p3", "idle")]


def test_non_claude_blocked_is_not_false_blocked():
    rows = [Row(ts=500, pane="w1:p9", state="blocked", agent="codex")]
    assert match_waits([w(enter=100, leave=110)], rows + [r(100.5, "blocked"), r(111, "idle")], STEP)["_all"].false_blocked == 0


def test_codex_rows_do_not_make_a_claude_wait_seen():
    rows = [Row(ts=101, pane="w1:p3", state="blocked", agent="codex")]
    assert match_waits([w(enter=100, leave=110)], rows, STEP)["tool"].missed == 1


def test_unknown_rows_are_counted():
    rows = [r(10, "unknown"), r(20, "idle"), r(30, "unknown")]
    assert match_waits([], rows, STEP)["_all"].unknown == 2


def test_wait_without_monitor_coverage_is_no_data_not_missed():
    hb = [Row(ts=t, pane="_heartbeat", state="ok", agent="_monitor") for t in (0, 30, 60)]
    c = match_waits([w(enter=40, leave=50), w(enter=500, leave=510)], hb, STEP, hb_s=30)
    assert c["tool"].missed == 1 and c["tool"].no_data == 1


def test_poll_once_bad_output_keeps_prev_and_returns_an_error():
    from report import poll_once
    prev = {"w1:p1": "working"}
    new_prev, rows, err = poll_once(0, '{"oops": 1}', prev, now=5.0)
    assert new_prev == prev and rows == [] and err
    new_prev, rows, err = poll_once(1, "", prev, now=6.0)
    assert new_prev == prev and rows == [] and err


def test_orca_waits_are_counted_per_ask_type():
    from report import orca_counts
    log = "\n".join([
        "100\ts1\tenter\ttool\torca-a-b",
        "110\ts1\tleave\ttool\torca-a-b",
        "200\ts1\tenter\tprose\torca-a-b",
        "260\ts1\tleave\tprose\torca-a-b",
        "300\ts2\tenter\tpermission\therdr-w1-p1",
    ])
    assert orca_counts(log, end=1000) == {"tool": 1, "prose": 1}


def test_since_drops_waits_before_the_trial_start():
    log = "100\ts1\tenter\ttool\therdr-w1-p1\n110\ts1\tleave\ttool\therdr-w1-p1\n500\ts1\tenter\ttool\therdr-w1-p1"
    assert [x.enter for x in parse_check_log(log, end=600, since=200)] == [500]
