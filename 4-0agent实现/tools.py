import os

# from Tools.i18n.pygettext import safe_eval
from serpapi import SerpApiClient
from dotenv import load_dotenv
from typing import Dict, Any
import ast
import operator

load_dotenv()



def search(query : str) -> str:
    """
       一个基于SerpApi的实战网页搜索引擎工具。
       它会智能地解析搜索结果，优先返回直接答案或知识图谱信息。
    """
    print(f"正在执行【SerpApi】网页搜索 ： {query}")
    try:
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return "错误 : not real ERPAPI_API_KEY can be set in .env file."

        params = {
            "engine" : "google",
            "q": query,
            "api_key" : api_key,
            "gl" : "cn",
            "hl" : "zh-CN",
        }
        client = SerpApiClient(params)
        results = client.get_dict()


        if "answer_box_list" in results:
            return "\n".join(results["answer_box_list"])
        if "answer_box" in results and "answer" in results["answer_box"]:
            return results["answer_box"]["answer"]
        if "knowledge_graph" in results and "description" in results["knowledge_graph"]:
            return results["knowledge_graph"]["description"]
        if "organic_results" in results and results["organic_results"]:
            sinppets = [
                f"[{i+1}]{res.get('title','')}\n{res.get('snippet','')}"
                for i, res in enumerate(results["organic_results"][:3])
            ]
            return "\n\n".join(sinppets)
        return f"对不起，没有找到关于 '{query}' 的信息。"
    except Exception as e:
        return f"错误搜索：{e}"


_ALLOWED_OPS = {
    ast.Add: operator.add,        ast.Sub: operator.sub,
    ast.Mult: operator.mul,       ast.Div: operator.truediv,
    ast.Pow: operator.pow,        ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg,       ast.UAdd: operator.pos,
}


def _eval_node(node):
    if isinstance(node, ast.Expression):        # 整棵树的根
        return _eval_node(node.body)

    if isinstance(node, ast.Constant):          # 一个数字
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"错误常量：{node.value!r}")

    if isinstance(node, ast.BinOp):             # 二元运算：a + b
        op = _ALLOWED_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"错误运算符：{type(node.op).__name__}")
        return op(_eval_node(node.left), _eval_node(node.right))

    if isinstance(node, ast.UnaryOp):           # 一元运算：-a
        op = _ALLOWED_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"错误一元运算符")
        return op(_eval_node(node.operand))

    raise ValueError(f"错误表达式出现 {type(node).__name__}")


def safe_eval(text: str):
    """只算数学表达式，绝不执行代码。"""
    return _eval_node(ast.parse(text, mode="eval"))


def calculator(expression: str) -> str:
    """一个数学计算器。输入是一个数学表达式。"""
    # ① 归一化：把"长得不一样但意思一样"的符号统一
    text = (expression or "").strip()
    for old, new in [("x", "*"),("×", "*"), ("÷", "/"), ("（", "("), ("）", ")"),
                     ("＋", "+"), ("－", "-"), ("−", "-"),
                     ("，", ""), (",", ""), ("=", ""), ("？", ""), ("?", "")]:
        text = text.replace(old, new)
    text = text.strip()

    # ② 求值（安全版，见下）
    try:
        value = safe_eval(text)
    except ZeroDivisionError:
        return "错误计算：除数是零，无法计算。"
    except Exception as exc:
        return f"错误计算：无法计算 {text!r}（{exc}）"

    # ③ 返回字符串，并带上原式
    if isinstance(value, float):
        value = round(value, 10)          # 避免 0.30000000000000004 这种
    return f"{text} = {value}"




# 接下来写工具执行器，负责管理和执行工具
class ToolExecutor:
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    def registerTool(self, name : str, description : str, func : callable):
        """
        向工具箱中注册一个新工具。
        """
        if name in self.tools:
            print(f"工具{name}已经存在，将被覆盖")
        self.tools[name] = {"description": description, "func": func}
        print(f"工具'{name}'已注册")

    def getTool(self,name : str) -> callable:
        """
        根据名称获取一个工具的执行函数。
        """
        return self.tools.get(name,{}).get("func")

    def getAvailableTools(self) -> str:
        """
        获取所有可用工具的格式化描述字符串。
        """
        return "\n".join([
            f"- {name} : {info['description']}"
            for name, info in self.tools.items()
        ])


if __name__ == "__main__":
    toolExecutor = ToolExecutor()

    search_description = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    toolExecutor.registerTool("Search", search_description, search)
    calculator_description = (
        "一个数学计算器。输入必须是一个纯数学表达式，"
        "例如 (123+456)*789/12。不要包含文字、单位、中文或等号。"
    )
    toolExecutor.registerTool("Calculator", calculator_description, calculator)

    print("\n--- 可用的工具 ---")
    print(toolExecutor.getAvailableTools())

    # 4. 智能体的Action调用，这次我们问一个实时性的问题
    print("\n--- 执行 Action: Search['英伟达最新的GPU型号是什么'] ---")
    tool_name = "Calculator"
    tool_input = "帮我计算一下5x6**6"

    tool_function = toolExecutor.getTool(tool_name)
    if tool_function:
        observation = tool_function(tool_input)
        print("--- 观察 (Observation) ---")
        print(observation)
    else:
        print(f"错误:未找到名为 '{tool_name}' 的工具。")



