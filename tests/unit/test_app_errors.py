import io
import sys

import pytest

from app import main


class TestAppErrors:
    def test_unknown_board_token_prints_friendly_error(self, monkeypatch, capsys):
        script = "Board:\nwK XX .\nCommands:\nprint board\n"
        monkeypatch.setattr(sys, 'stdin', io.StringIO(script))
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert 'Traceback' not in captured.err
        assert "ERROR: Unknown board token 'XX' in row 1" in captured.err

    def test_invalid_command_prints_friendly_error(self, monkeypatch, capsys):
        script = "Board:\nwK . .\nCommands:\nclick 100\n"
        monkeypatch.setattr(sys, 'stdin', io.StringIO(script))
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert 'Traceback' not in captured.err
        assert 'ERROR: Invalid command' in captured.err
        assert 'click requires exactly 2 coordinates' in captured.err

    def test_row_width_mismatch_prints_friendly_error(self, monkeypatch, capsys):
        script = "Board:\nwK . .\n. wP\nCommands:\n"
        monkeypatch.setattr(sys, 'stdin', io.StringIO(script))
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert 'Traceback' not in captured.err
        assert 'ERROR: Row 2 has 2 cells, expected 3' in captured.err
