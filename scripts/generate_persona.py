"""
generate_persona.py — 使用元提示词生成新角色提示词并保存

用法:
    python scripts/generate_persona.py "DevOps工程师" --category tech
    python scripts/generate_persona.py "心理咨询师" --desc "专注认知行为疗法" --category medical
    python scripts/generate_persona.py "合同审查律师" --category legal --model gpt-4o-mini
"""

import argparse
import re
import sys
from pathlib import Path

from hexmind.models.prompt_asset import PromptAsset
from hexmind.prompt_library.loader import PromptLibraryLoader
from hexmind.prompt_library.normalizer import (
    extract_position,
    slugify_asset_name,
    summarize_prompt,
)

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
PERSONAS_DIR = ROOT / "personas"
META_PROMPT_PATH = PERSONAS_DIR / "meta-prompt.md"

VALID_CATEGORIES = ["tech", "business", "medical", "creative", "education", "legal", "general"]

# ---------------------------------------------------------------------------
# LLM 调用
# ---------------------------------------------------------------------------

def call_llm(system_prompt: str, user_prompt: str, model: str) -> str:
    """通过 litellm 调用 LLM，返回生成的文本。"""
    try:
        from litellm import completion
    except ImportError:
        sys.exit("错误: 请先安装 litellm  →  pip install litellm")

    response = completion(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=4096,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# 持久化
# ---------------------------------------------------------------------------

def save_prompt(title: str, content: str, category: str) -> Path:
    """保存生成结果到统一的 Prompt Library。"""
    position = extract_position(title, content)
    asset = PromptAsset(
        id=slugify_asset_name(title, fallback=slugify_asset_name(position, "generated-prompt")),
        name=title,
        position=position,
        domain=category,
        description=summarize_prompt(content, position),
        prompt=content,
        kind="template",
        prompt_mode="full",
        tags=[position, category],
        source="generated",
        source_title=title,
        source_path=str(META_PROMPT_PATH),
    )
    loader = PromptLibraryLoader(ROOT / "prompts" / "library")
    return loader.save(asset, overwrite=False)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="使用元提示词生成新角色提示词")
    parser.add_argument("role", help="角色名称，如 'DevOps工程师'")
    parser.add_argument("--desc", default="", help="角色的补充描述（可选）")
    parser.add_argument("--category", default="general", choices=VALID_CATEGORIES,
                        help="提示词分类 (default: general)")
    parser.add_argument("--model", default="gpt-4o-mini",
                        help="LLM 模型名称 (default: gpt-4o-mini)")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印生成结果，不保存文件")
    args = parser.parse_args()

    # 读取元提示词
    if not META_PROMPT_PATH.exists():
        sys.exit(f"错误: 找不到元提示词文件 {META_PROMPT_PATH}")
    meta_template = META_PROMPT_PATH.read_text(encoding="utf-8")

    # 构造实现目标：把用户的角色需求填入元提示词的 Objectives 区域
    objective = f"生成一个「{args.role}」的完整角色提示词。"
    if args.desc:
        objective += f"\n补充描述：{args.desc}"
    objective += "\n提示词需要覆盖该角色的专业能力、核心工作流程、输出格式，可直接用于 LLM 对话。"

    # 用实际目标替换元提示词模板中的占位示例
    system_prompt = re.sub(
        r"生成的提示词应能够：\n\{.*?\}",
        f"生成的提示词应能够：\n{{\n{objective}\n}}",
        meta_template,
        flags=re.DOTALL,
    )

    user_prompt = f"请为「{args.role}」生成完整的 RTF 框架角色提示词。"
    if args.desc:
        user_prompt += f"\n{args.desc}"

    print(f"🔄 正在生成「{args.role}」的角色提示词 (model={args.model}) ...")

    content = call_llm(system_prompt, user_prompt, args.model)

    print("\n" + "=" * 60)
    print(content)
    print("=" * 60)

    if args.dry_run:
        print("\n[dry-run] 未保存文件。")
        return

    title = args.role
    asset_path = save_prompt(title, content, args.category)
    print(f"\n✅ 已保存到:")
    print(f"   - {asset_path}")


if __name__ == "__main__":
    main()
