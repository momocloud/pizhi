from __future__ import annotations

import json

from pizhi.adapters.base import PromptRequest
from pizhi.services.agent_task_package import render_opencode_task_package


def test_render_opencode_task_package_writes_expected_bridge_files(tmp_path):
    request = PromptRequest(
        command_name="write",
        prompt_text="# Write Request\n\nDraft the next chapter.\n",
        metadata={"chapter": 7},
        referenced_files=[".pizhi/chapters/ch007/outline.md"],
    )

    package = render_opencode_task_package(
        tmp_path,
        prompt_request=request,
        run_id="run-test-1234",
        target="ch007",
    )

    assert package.request_path.name == "agent_request.json"
    assert package.task_path.name == "agent_task.md"
    assert package.output_path.name == "agent_output.md"
    assert package.stdout_path.name == "agent_stdout.txt"
    assert package.stderr_path.name == "agent_stderr.txt"
    assert package.agent_path.name == "pizhi-step.md"
    assert package.agent_path.exists()
    assert package.task_path.exists()
    assert package.request_path.exists()

    request_payload = json.loads(package.request_path.read_text(encoding="utf-8"))
    assert request_payload["run_id"] == "run-test-1234"
    assert request_payload["target"] == "ch007"
    assert request_payload["command"] == "write"
    assert request_payload["output_file"] == "agent_output.md"

    task_text = package.task_path.read_text(encoding="utf-8")
    assert "agent_output.md" in task_text
    assert "# Write Request" in task_text

    agent_text = package.agent_path.read_text(encoding="utf-8")
    assert "agent_output.md" in agent_text
    assert "Do not modify project source-of-truth files" in agent_text


def test_render_opencode_task_package_adds_write_contract_guards(tmp_path):
    request = PromptRequest(
        command_name="write",
        prompt_text="# Chapter Write Request\n\nChapter: 7\n",
        metadata={"chapter": 7},
        referenced_files=[".pizhi/chapters/ch007/outline.md"],
    )

    package = render_opencode_task_package(
        tmp_path,
        prompt_request=request,
        run_id="run-test-5678",
        target="ch007",
    )

    task_text = package.task_path.read_text(encoding="utf-8")
    agent_text = package.agent_path.read_text(encoding="utf-8")

    assert "Start the candidate with YAML frontmatter delimited by `---`." in task_text
    assert "The candidate must include `## characters_snapshot` and `## relationships_snapshot`." in task_text
    assert "Do not add commentary before or after the candidate." in task_text
    assert "For `write`, preserve the exact chapter response contract from the prompt." in task_text
    assert "`timeline_events` must stay a YAML list of objects." in task_text
    assert "`foreshadowing` must stay a YAML object with `introduced`, `referenced`, and `resolved` lists." in task_text

    assert "If the task is a `write` step, keep the exact chapter response contract intact." in agent_text
    assert "Never replace the structured chapter response with free-form prose." in agent_text
    assert "Do not collapse `timeline_events` into prose bullets or `foreshadowing` into a flat list." in agent_text
    assert "If a YAML scalar contains `:` or quotes, render it as a single quoted scalar or block scalar so the frontmatter remains valid YAML." in task_text
    assert "If a YAML scalar contains `:` or quotes, render it as a single quoted scalar or block scalar so the frontmatter remains valid YAML." in agent_text
