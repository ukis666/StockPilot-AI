from datetime import date

import click
import pytest

from commands import parse_day
from models import User


def test_cli_init_demo_train(app):
    runner = app.test_cli_runner()
    assert runner.invoke(args=["init-db"]).exit_code == 0
    result = runner.invoke(
        args=[
            "demo-data",
            "--username",
            "cli-demo",
            "--password",
            "cli-password",
            "--end-date",
            "2026-06-30",
            "--days",
            "45",
        ]
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(args=["train-models", "--username", "cli-demo", "--as-of", "2026-06-30"])
    assert result.exit_code == 0, result.output
    assert '"products_trained": 30' in result.output
    assert (
        runner.invoke(args=["train-models", "--username", "missing", "--as-of", "2026-06-30"]).exit_code != 0
    )
    assert (
        runner.invoke(
            args=[
                "demo-data",
                "--username",
                "cli-demo",
                "--password",
                "cli-password",
                "--end-date",
                "2026-06-30",
            ]
        ).exit_code
        != 0
    )
    assert User.query.count() == 1
    assert runner.invoke(args=["demo-data", "--password", "short", "--end-date", "2026-06-30"]).exit_code != 0


@pytest.mark.parametrize("value", ["invalid", "2999-01-01", str(date.today())])
def test_bad_date(value):
    with pytest.raises(click.BadParameter):
        parse_day(value)
