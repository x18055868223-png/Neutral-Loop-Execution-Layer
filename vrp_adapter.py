# -*- coding: utf-8 -*-
"""Local VRP snapshot loader used by regression tests.

The handoff repo is intentionally standalone, so tests compare the execution
VRP gate against the two bundled snapshot files instead of reaching back into
the larger integration workspace.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


VRP_SRC = Path(__file__).resolve().parent / "vrp_snapshot" / "src"


def _load_vrp_modules():
    model_path = VRP_SRC / "vrp_model.py"
    policy_path = VRP_SRC / "vrp_policy.py"

    model_spec = importlib.util.spec_from_file_location("handoff_vrp_model_snapshot", model_path)
    if model_spec is None or model_spec.loader is None:
        raise ImportError("Cannot load bundled VRP model snapshot")
    model = importlib.util.module_from_spec(model_spec)
    sys.modules[model_spec.name] = model
    model_spec.loader.exec_module(model)

    old_vrp_model = sys.modules.get("vrp_model")
    sys.modules["vrp_model"] = model
    try:
        policy_spec = importlib.util.spec_from_file_location("handoff_vrp_policy_snapshot", policy_path)
        if policy_spec is None or policy_spec.loader is None:
            raise ImportError("Cannot load bundled VRP policy snapshot")
        policy = importlib.util.module_from_spec(policy_spec)
        sys.modules[policy_spec.name] = policy
        policy_spec.loader.exec_module(policy)
    finally:
        if old_vrp_model is None:
            sys.modules.pop("vrp_model", None)
        else:
            sys.modules["vrp_model"] = old_vrp_model

    return model, policy
