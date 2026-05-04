from __future__ import annotations

from petflow.domain.entities import Node
from petflow.domain.graph import GraphModel


class PromptBuilder:
    def build_graph_generation_prompt(self, user_goal: str) -> str:
        return (
            "请根据用户目标生成 PetFlow 任务图。"
            "只返回 JSON 对象，包含 nodes 和 edges。\n"
            f"用户目标：{user_goal}"
        )

    def build_node_split_prompt(self, graph: GraphModel, node: Node) -> str:
        return (
            "请把指定节点拆分为 3 到 6 个可执行子任务。"
            "只返回 JSON 对象，包含 nodes 和 edges。\n"
            f"当前节点：{node.title}\n"
            f"图中节点数量：{len(graph.nodes)}"
        )

    def build_review_prompt(self, summary: str) -> str:
        return (
            "请根据任务完成情况生成简短复盘。"
            "只返回 JSON 对象，包含 summary 和 highlights。\n"
            f"摘要：{summary}"
        )
