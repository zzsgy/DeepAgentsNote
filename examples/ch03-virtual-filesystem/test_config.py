"""配置与真实模型对象/Agent 构造的离线检查；不调用 invoke。"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend, StoreBackend
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from pydantic import SecretStr

from model_config import build_model


class ModelConfigurationTests(unittest.TestCase):
    def test_env_names_and_secret_type(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / ".env"
            fixture.write_text(
                "OPENAI_API_KEY=test-placeholder-not-a-real-key\n"
                "OPENAI_API_BASE=http://127.0.0.1:9/v1\n"
                "MODEL_NAME=deepseek-flash\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                model = build_model(fixture)
                self.assertEqual(model.model_name, "deepseek-flash")
                self.assertEqual(model.openai_api_base, "http://127.0.0.1:9/v1")
                self.assertIsInstance(model.openai_api_key, SecretStr)

    def test_wrong_base_variable_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / ".env"
            fixture.write_text(
                "OPENAI_API_KEY=test-placeholder-not-a-real-key\n"
                "OPENAI_API_URL=http://127.0.0.1:9/v1\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ValueError, "OPENAI_API_BASE"):
                    build_model(fixture)

    def test_four_agent_constructors_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "missing.env"
            fake_env = {
                "OPENAI_API_KEY": "test-placeholder-not-a-real-key",
                "OPENAI_API_BASE": "http://127.0.0.1:9/v1",
                "MODEL_NAME": "deepseek-flash",
            }
            with patch.dict(os.environ, fake_env, clear=True):
                model = build_model(fixture)
            store = InMemoryStore()
            backends = [
                StateBackend(),
                FilesystemBackend(root_dir=directory, virtual_mode=True),
                StoreBackend(namespace=lambda _: ("test-user",)),
                CompositeBackend(default=StateBackend(), routes={
                    "/memories/": StoreBackend(namespace=lambda _: ("test-user",)),
                }),
            ]
            for backend in backends:
                with self.subTest(backend=type(backend).__name__):
                    agent = create_deep_agent(
                        model=model, backend=backend,
                        store=store, checkpointer=InMemorySaver(),
                    )
                    self.assertTrue(callable(agent.invoke))
                    self.assertIn("__start__", agent.get_graph().nodes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
