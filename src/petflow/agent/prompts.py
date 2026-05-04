from __future__ import annotations

from petflow.domain.entities import Node
from petflow.domain.enums import EdgeType
from petflow.domain.graph import GraphModel


class PromptBuilder:
    def build_graph_generation_prompt(self, user_goal: str) -> str:
        return (
            "请根据用户目标生成 PetFlow 任务图。"
            "只返回 JSON 对象，包含 nodes 和 edges。"
            "节点数量控制在 3 到 10 个，字段使用 id/type/title/description/priority/estimated_minutes/x/y。"
            "边只使用 source/target/type/label。\n"
            f"用户目标：{user_goal}"
        )

    def build_node_split_prompt(self, graph: GraphModel, node: Node) -> str:
        predecessors = graph.predecessors(node.id, [EdgeType.DEPENDENCY])
        successors = graph.successors(node.id, [EdgeType.DEPENDENCY])
        predecessor_titles = ", ".join(item.title for item in predecessors) or "无"
        successor_titles = ", ".join(item.title for item in successors) or "无"
        tags = ", ".join(node.tags) or "无"
        return (
            "请把指定节点拆分为 3 到 6 个可执行子任务。"
            "只返回 JSON 对象，包含 nodes 和 edges。"
            "子任务应可执行，估时合理，不要重复当前图中已有节点。\n"
            f"当前节点：{node.title}\n"
            f"描述：{node.description or '无'}\n"
            f"前置依赖：{predecessor_titles}\n"
            f"后续节点：{successor_titles}\n"
            f"预计耗时：{node.estimated_minutes} 分钟\n"
            f"标签：{tags}\n"
            f"图中节点数量：{len(graph.nodes)}"
        )

    def build_review_prompt(self, summary: str) -> str:
        return (
            "请根据任务完成情况生成简短复盘。"
            "只返回 JSON 对象，包含 summary 和 highlights。\n"
            f"摘要：{summary}"
        )
