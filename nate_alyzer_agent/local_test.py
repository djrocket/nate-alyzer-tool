#!/usr/bin/env python
"""
local_test.py

Usage examples:
  # Test a deployed Agent Engine
  python nate_alyzer_agent/local_test.py --engine projects/XXX/locations/us-central1/reasoningEngines/NNN \
      --prompt "Say hello and list your available tools."

  # Run an end-to-end tool prompt against the engine
  python nate_alyzer_agent/local_test.py --engine projects/XXX/locations/us-central1/reasoningEngines/NNN --e2e

  # Optional: test locally using the class in deploy_final.py
  python nate_alyzer_agent/local_test.py --local --prompt "Say hello"
"""

import argparse
import json
import pprint
from typing import Optional

import vertexai
from vertexai import agent_engines


def test_remote(engine_resource: str, project: str, location: str, prompt: str, e2e: bool) -> None:
    print("--- Initializing Vertex AI ---")
    vertexai.init(project=project, location=location)
    print(f"--- Getting Agent Engine: {engine_resource} ---")
    agent = agent_engines.get(engine_resource)

    print(f"\n--- Query (sanity): {prompt} ---")
    resp = agent.query(prompt=prompt)
    pprint.pprint(resp)

    if e2e:
        e2e_prompt = (
            "Retrieve transcript for video_id=aVXtoWm1DEM, analyze it, and save it to the anthology."
        )
        print(f"\n--- Query (e2e): {e2e_prompt} ---")
        resp2 = agent.query(prompt=e2e_prompt)
        pprint.pprint(resp2)


def test_local(prompt: str) -> None:
    print("--- Local test using deploy_final.NateAlyzer ---")
    # Import from the same package directory as this script
    from deploy_final import NateAlyzer

    agent = NateAlyzer()
    agent.set_up()

    print(f"\n--- Query (local): {prompt} ---")
    out = agent.query(prompt=prompt)
    print("\n--- Local result ---")
    pprint.pprint(out)


def main():
    parser = argparse.ArgumentParser(description="Test Vertex AI Agent Engine or local agent")
    parser.add_argument("--engine", type=str, help="Full resource path of the Agent Engine")
    parser.add_argument("--project", type=str, default="nate-digital-twin", help="GCP project ID")
    parser.add_argument("--location", type=str, default="us-central1", help="GCP location")
    parser.add_argument("--prompt", type=str, default="Say hello and list your available tools.", help="Prompt to send")
    parser.add_argument("--e2e", action="store_true", help="Run an additional end-to-end tool prompt")
    parser.add_argument("--local", action="store_true", help="Run against local class instead of remote engine")
    args = parser.parse_args()

    if args.local:
        test_local(args.prompt)
    elif args.engine:
        test_remote(args.engine, args.project, args.location, args.prompt, args.e2e)
    else:
        parser.error("Provide --engine for remote test or --local for local test.")


if __name__ == "__main__":
    main()
