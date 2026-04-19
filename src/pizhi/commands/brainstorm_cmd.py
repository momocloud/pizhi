from __future__ import annotations

import argparse
from pathlib import Path

from pizhi.services.brainstorm_service import BrainstormService
from pizhi.services.provider_execution import execute_prompt_request


def run_brainstorm(args: argparse.Namespace) -> int:
    service = BrainstormService(Path.cwd())
    response_file = Path(args.response_file) if args.response_file else None
    if args.execute:
        request = service.build_prompt_request()
        prompt_artifact = service.prepare_prompt(request)
        execution = execute_prompt_request(service.project_root, request, target="project")
        print(f"Prepared prompt packet: {prompt_artifact.prompt_path.name}")
        print(f"Run ID: {execution.run_id}")
        return 0

    result = service.run(response_file=response_file)
    print(f"Prepared prompt packet: {result.prompt_artifact.prompt_path.name}")
    return 0
