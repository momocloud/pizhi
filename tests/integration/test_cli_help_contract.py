from pizhi.cli import build_parser


def test_cli_help_mentions_delivery_relevant_subcommands():
    parser = build_parser()
    help_text = " ".join(parser.format_help().split())

    assert "provider" in help_text
    assert "apply" in help_text
    assert "continue" in help_text
    assert "review" in help_text
    assert "run structural and optional AI consistency review" in help_text
    assert "compile manuscript output by volume, chapter, or chapter range" in help_text
