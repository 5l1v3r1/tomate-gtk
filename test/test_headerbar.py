import pytest
from conftest import refresh_gui
from gi.repository import Gtk
from wiring import SingletonScope
from wiring.scanning import scan_to_graph

from tomate.constant import State, Sessions
from tomate.event import Session, connect_events
from tomate.session import SessionPayload, FinishedSession
from tomate_gtk.shortcut import ShortcutManager
from tomate_gtk.widgets import HeaderBar
from tomate_gtk.widgets.menu import Menu

ONE_FINISHED_SESSION = [FinishedSession(1, Sessions.pomodoro, 10)]

NO_FINISHED_SESSIONS = []


@pytest.fixture
def mock_menu(mocker):
    return mocker.Mock(Menu, widget=Gtk.Menu())


@pytest.fixture
def mock_shortcuts(mocker):
    return mocker.Mock(
        ShortcutManager,
        START=ShortcutManager.START,
        STOP=ShortcutManager.STOP,
        RESET=ShortcutManager.RESET,
    )


@pytest.fixture
def header_bar(session, mock_menu, mock_shortcuts):
    Session.receivers.clear()

    subject = HeaderBar(session, mock_menu, mock_shortcuts)

    connect_events(subject)

    return subject


def test_header_bar_module(graph, session, mock_menu, mock_shortcuts):
    scan_to_graph(["tomate_gtk.widgets.headerbar"], graph)

    assert "view.headerbar" in graph.providers

    graph.register_instance("view.menu", mock_menu)
    graph.register_instance("tomate.session", mock_shortcuts)
    graph.register_instance("view.shortcut", mock_shortcuts)

    provider = graph.providers["view.headerbar"]
    assert provider.scope == SingletonScope

    assert isinstance(graph.get("view.headerbar"), HeaderBar)


def test_connect_shortcuts(mock_shortcuts, header_bar):
    mock_shortcuts.connect.assert_any_call(
        ShortcutManager.START, header_bar.on_start_button_clicked
    )
    mock_shortcuts.connect.assert_any_call(
        ShortcutManager.STOP, header_bar.on_stop_button_clicked
    )
    mock_shortcuts.connect.assert_any_call(
        ShortcutManager.RESET, header_bar.on_reset_button_clicked
    )


class TestSessionStart:
    def test_changes_buttons_visibility_when_session_started_event_is_received(
            self, header_bar
    ):
        Session.send(State.started)

        assert header_bar.start_button.get_visible() is False
        assert header_bar.stop_button.get_visible() is True
        assert header_bar.reset_button.get_sensitive() is False

    def test_starts_session_when_start_button_is_clicked(self, header_bar, session):
        header_bar.start_button.emit("clicked")

        refresh_gui(0)

        session.start.assert_called_once_with()


class TestSessionStopOrFinished:
    def test_buttons_visibility_and_title_with_no_past_sessions(
            self, header_bar, session
    ):

        payload = SessionPayload(
            type=Sessions.pomodoro,
            sessions=NO_FINISHED_SESSIONS,
            state=State.started,
            duration=0,
            task="",
        )

        for state in [State.stopped, State.finished]:
            Session.send(state, payload=payload)

            assert header_bar.start_button.get_visible() is True
            assert header_bar.stop_button.get_visible() is False
            assert header_bar.reset_button.get_sensitive() is False

            assert header_bar.widget.props.title == "No session yet"

    def test_changes_buttons_visibility_and_title_with_one_past_session(
            self, header_bar, session
    ):

        payload = SessionPayload(
            type=Sessions.pomodoro,
            sessions=ONE_FINISHED_SESSION,
            state=State.finished,
            duration=1,
            task="",
        )

        for state in [State.stopped, State.finished]:
            Session.send(state, payload=payload)

            assert header_bar.start_button.get_visible() is True
            assert header_bar.stop_button.get_visible() is False
            assert header_bar.reset_button.get_sensitive() is True

            assert header_bar.widget.props.title == "Session 1"

    def test_stop_session_when_stop_button_is_clicked(self, header_bar, session):
        header_bar.stop_button.emit("clicked")

        refresh_gui(0)

        session.stop.assert_called_once_with()


class TestSessionReset:
    def test_disables_reset_button_when_reset_event_is_received(
            self, header_bar, session
    ):
        header_bar.reset_button.set_sensitive(True)

        Session.send(State.reset)

        assert header_bar.reset_button.get_sensitive() is False

    def test_reset_session_when_reset_button_is_clicked(self, header_bar, session):
        header_bar.reset_button.emit("clicked")

        refresh_gui(0)

        session.reset.assert_called_once_with()
