"""Prompt normalization helpers shared by scripts and loaders."""

from __future__ import annotations

import hashlib
import re

from hexmind.models.hat import HAT_CONSTRAINTS, HatColor
from hexmind.models.persona import Persona
from hexmind.models.prompt_asset import PromptAsset

_ROLE_KEYWORDS = (
    "工程师",
    "顾问",
    "导师",
    "老师",
    "教练",
    "专家",
    "分析师",
    "经理",
    "总监",
    "架构师",
    "研究员",
    "医生",
    "中医",
    "客服",
    "销售",
    "设计师",
    "写作大师",
    "大师",
    "创作者",
    "伙伴",
    "炼金术师",
    "管理员",
    "负责人",
    "助教",
    "助手",
    "架构师",
    "Master",
    "Engineer",
    "Consultant",
    "Coach",
    "Teacher",
    "Analyst",
    "Manager",
    "Architect",
    "Assistant",
    "Researcher",
    "Writer",
)

_GENERIC_TITLE_PATTERNS = (
    r"^$",
    r"^-->$",
    r"^创建日期",
    r"^Role$",
    r"^YAML$",
    r"^TypeScript$",
    r"^Bash$",
    r"^\|",
    r"^<!--",
    r"^描述[:：]",
    r"^prompt\s*:",
)

_GENERIC_POSITIONS = {
    "人",
    "prompt",
    "role",
    "角色",
    "专业角色",
    "assistant",
}

_HAT_DETECTION_PATTERNS: dict[HatColor, tuple[str, ...]] = {
    HatColor.WHITE: (
        r"\bwhite hat\b",
        r"白帽",
        r"\bW\d+\s*[:：]",
        r"只陈述事实",
        r"facts and data",
    ),
    HatColor.RED: (
        r"\bred hat\b",
        r"红帽",
        r"直觉",
        r"情感反应",
    ),
    HatColor.BLACK: (
        r"\bblack hat\b",
        r"黑帽",
        r"\bB\d+\s*[:：]",
        r"风险分析",
        r"最坏情况",
        r"引用 W 编号",
    ),
    HatColor.YELLOW: (
        r"\byellow hat\b",
        r"黄帽",
        r"\bY\d+\s*[:：]",
        r"收益分析",
        r"价值分析",
        r"最佳情况",
        r"机会分析",
    ),
    HatColor.GREEN: (
        r"\bgreen hat\b",
        r"绿帽",
        r"\bG\d+\s*[:：]",
        r"创意方案",
        r"替代方案",
        r"行动方案",
        r"引用 B 编号",
    ),
}

_ALL_HATS = [hat for hat in HatColor]


def clean_prompt_text(text: str) -> str:
    """Normalize raw prompt text for storage and parsing."""
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n")
    return text.strip()


def clean_inline_text(text: str) -> str:
    """Strip markdown-like markers from single-line labels."""
    text = clean_prompt_text(text)
    text = re.sub(r"`+", "", text)
    text = re.sub(r"^[#>*\-\s]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" |:：-*")


def slugify_asset_name(text: str, fallback: str = "untitled") -> str:
    """Create a filesystem-safe slug while preserving Chinese labels."""
    text = clean_inline_text(text).lower()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or fallback


def _looks_like_role(text: str) -> bool:
    return any(keyword.lower() in text.lower() for keyword in _ROLE_KEYWORDS)


def _is_generic_position(text: str) -> bool:
    return clean_inline_text(text).strip('"').strip("'").lower() in _GENERIC_POSITIONS


def _cleanup_position(text: str) -> str:
    text = clean_inline_text(text)
    text = text.split("：")[0].split(":")[0].strip()
    text = re.sub(r"^(?:你是|你是一位|你是一个|你是一名|你现在是|作为|Act as|You are)\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:一位|一个|一名)\s*", "", text)
    text = re.sub(r"^(?:专业的|资深的|经验丰富的|真实存在的|拥有丰富经验的)\s*", "", text)
    text = re.sub(r"^(?:专业|资深|高级|首席)\s*", "", text)
    for delimiter in ("，", "。", ";", "；"):
        head = text.split(delimiter, 1)[0].strip()
        if head and _looks_like_role(head):
            text = head
            break
    if "的" in text:
        tail = text.rsplit("的", 1)[-1].strip()
        if tail and _looks_like_role(tail):
            text = tail
    return text.strip(" ，。；;\"'")


def extract_position(title: str, prompt: str) -> str:
    """Extract a role/position label from title or prompt body."""
    title = clean_inline_text(title)
    prompt = clean_prompt_text(prompt)
    lines = [clean_inline_text(line) for line in prompt.splitlines() if clean_inline_text(line)]

    role_heading_indexes = [
        idx for idx, line in enumerate(lines)
        if re.fullmatch(r"(?i)(?:role|角色|角色定位|角色定义|职位)\s*(?:\(.+?\))?", line)
    ]
    for idx in role_heading_indexes:
        if idx + 1 < len(lines):
            candidate = _cleanup_position(lines[idx + 1])
            if candidate and not _is_generic_position(candidate) and _looks_like_role(candidate):
                return candidate

    patterns = [
        r"^(?:你是|你是一位|你是一个|你是一名|你现在是|You are|Act as)\s*(.+?)(?:[，。,；;]|$)",
        r"^(?:角色|角色定位|角色定义|职位)[:：]\s*(.+)$",
    ]
    for line in lines[:25]:
        for pattern in patterns:
            match = re.search(pattern, line, flags=re.IGNORECASE)
            if match:
                candidate = _cleanup_position(match.group(1))
                if candidate and not _is_generic_position(candidate):
                    return candidate

    for line in lines[:25]:
        candidate = _cleanup_position(line)
        if candidate and not _is_generic_position(candidate) and _looks_like_role(candidate):
            return candidate

    title_candidate = re.sub(r"(提示词|生成器|最终版生成提示|通用提示词|英文原版提示词)$", "", title).strip()
    title_candidate = _cleanup_position(title_candidate)
    if title_candidate and not _is_generic_position(title_candidate):
        return title_candidate

    digest = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:8]
    return f"未分类职位-{digest}"


def normalize_prompt_title(title: str, position: str) -> str:
    """Choose a stable, readable prompt asset name."""
    cleaned = clean_inline_text(title)
    if any(re.match(pattern, cleaned, flags=re.IGNORECASE) for pattern in _GENERIC_TITLE_PATTERNS):
        return f"{position} 提示词"
    if len(cleaned) < 3:
        return f"{position} 提示词"
    return cleaned


def classify_domain(title: str, prompt: str) -> str:
    """Broad secondary classification for browsing and filtering."""
    text = f"{clean_inline_text(title)} {clean_prompt_text(prompt)}".lower()
    categories = {
        "tech": [
            "engineer", "工程师", "developer", "开发", "code", "代码", "架构",
            "architect", "devops", "运维", "backend", "前端", "frontend",
            "fullstack", "程序员", "技术", "html", "typescript", "yaml", "bash",
        ],
        "business": [
            "产品", "product", "marketing", "营销", "运营", "经理", "manager",
            "ceo", "cfo", "coo", "business", "商业", "strategy", "finance",
            "财务", "sales", "销售", "增长", "growth", "品牌",
        ],
        "creative": [
            "设计", "design", "写作", "writing", "文案", "copy", "创意",
            "creative", "编辑", "editor", "内容", "content", "视频", "风格",
            "仿写", "故事", "memoir", "sanmao",
        ],
        "education": [
            "教师", "teacher", "教育", "education", "教授", "导师", "tutor",
            "学习", "learn", "考试", "exam", "助教", "数学",
        ],
        "medical": [
            "医", "doctor", "health", "健康", "临床", "clinical", "护理",
            "nurse", "诊断", "therapy", "心理", "患者", "中医",
        ],
        "legal": [
            "法", "legal", "律师", "lawyer", "合同", "contract", "合规",
            "compliance", "专利",
        ],
        "general": [],
    }
    for category, keywords in categories.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "general"


def infer_prompt_kind(title: str, prompt: str, *, default: str = "template") -> str:
    """Infer prompt asset kind from content."""
    title_text = clean_inline_text(title).lower()
    prompt_text = clean_prompt_text(prompt)
    if "you are chatgpt" in prompt_text.lower():
        return "system"
    if "工作流程" in prompt_text or "workflow" in prompt_text.lower():
        return "workflow"
    if "persona" in title_text:
        return "persona"
    return default


def infer_status(title: str, position: str) -> str:
    """Mark obviously fragmented records for manual review."""
    cleaned = clean_inline_text(title)
    if position.startswith("未分类职位-"):
        return "needs-review"
    if _is_generic_position(position):
        return "needs-review"
    if len(position) > 48:
        return "needs-review"
    if position.lower() != "chatgpt" and not _looks_like_role(position):
        return "needs-review"
    if any(re.match(pattern, cleaned, flags=re.IGNORECASE) for pattern in _GENERIC_TITLE_PATTERNS):
        return "ready"
    return "ready"


def infer_hat_metadata(
    title: str,
    prompt: str,
) -> tuple[str, HatColor | None, list[HatColor]]:
    """Infer explicit hat metadata from a raw prompt asset."""
    text = f"{clean_inline_text(title)}\n{clean_prompt_text(prompt)}"
    detected: list[HatColor] = []

    for hat, patterns in _HAT_DETECTION_PATTERNS.items():
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            detected.append(hat)

    if not detected:
        return "general", None, []

    if len(detected) == 1:
        return "hat-specific", detected[0], detected

    return "general", None, []


def summarize_prompt(prompt: str, position: str) -> str:
    """Generate a short description from the first informative line."""
    for line in clean_prompt_text(prompt).splitlines():
        candidate = clean_inline_text(line)
        if not candidate:
            continue
        if candidate == position:
            continue
        if len(candidate) > 140:
            return candidate[:137] + "..."
        return candidate
    return ""


def build_builtin_hat_assets(*, source_path: str = "") -> list[PromptAsset]:
    """Create built-in prompt assets for the five thinking hats."""
    hat_prompts = {
        HatColor.WHITE: (
            "White Hat 协议\n"
            "目标：只看事实、数据、证据和信息缺口。\n"
            "要求：使用 W 编号输出，避免主观判断，优先说明来源和置信度。"
        ),
        HatColor.RED: (
            "Red Hat 协议\n"
            "目标：表达直觉、担忧、兴奋或不安。\n"
            "要求：简短直接，不做论证，不伪装成事实。"
        ),
        HatColor.BLACK: (
            "Black Hat 协议\n"
            "目标：识别风险、失败路径、障碍和代价。\n"
            "要求：使用 B 编号输出，尽量引用 W 编号作为依据。"
        ),
        HatColor.YELLOW: (
            "Yellow Hat 协议\n"
            "目标：识别价值、机会、收益和可行回报。\n"
            "要求：使用 Y 编号输出，尽量引用 W 编号作为依据。"
        ),
        HatColor.GREEN: (
            "Green Hat 协议\n"
            "目标：提出新思路、替代方案和突破路径。\n"
            "要求：使用 G 编号输出，尽量回应 B 编号里的风险。"
        ),
    }

    assets: list[PromptAsset] = []
    for hat in HatColor:
        constraint = HAT_CONSTRAINTS[hat]
        prompt = hat_prompts[hat]
        if constraint.required_format:
            prompt += f"\n格式：{constraint.required_format}"
        if constraint.max_sentences is not None:
            prompt += f"\n句数限制：最多 {constraint.max_sentences} 句"
        if constraint.references_required:
            prompt += f"\n引用要求：必须引用 {constraint.references_required} 帽编号"

        assets.append(
            PromptAsset(
                id=f"hat-{hat.value}",
                name=f"{hat.value.title()} Hat 协议",
                position="帽子协议",
                domain="general",
                description=f"{hat.value} 帽的独立思考协议。",
                prompt=prompt,
                kind="hat",
                prompt_mode="full",
                hat_context="hat-specific",
                hat=hat,
                applicable_hats=[hat],
                tags=["hat", hat.value],
                source="system",
                source_title=f"{hat.value.title()} Hat",
                source_path=source_path,
                status="ready",
            )
        )

    return assets


def build_prompt_asset_from_raw(
    item: dict,
    *,
    source: str = "feishu",
    source_path: str = "",
) -> PromptAsset:
    """Normalize a raw Feishu prompt record into a prompt asset."""
    title = clean_inline_text(item.get("title", ""))
    prompt = clean_prompt_text(item.get("content", ""))
    position = extract_position(title, prompt)
    name = normalize_prompt_title(title, position)
    asset_id = slugify_asset_name(name, fallback=slugify_asset_name(position, "prompt"))
    hat_context, hat, applicable_hats = infer_hat_metadata(title, prompt)
    return PromptAsset(
        id=asset_id,
        name=name,
        position=position,
        domain=item.get("category") or classify_domain(title, prompt),
        description=summarize_prompt(prompt, position),
        prompt=prompt,
        kind=infer_prompt_kind(title, prompt),
        prompt_mode="full",
        hat_context=hat_context,
        hat=hat,
        applicable_hats=applicable_hats,
        tags=[position, *( [hat.value] if hat else [] )],
        source=source,
        source_title=title,
        source_path=source_path,
        status=infer_status(title, position),
    )


def build_prompt_asset_from_persona(
    persona: Persona,
    *,
    source_path: str = "",
) -> PromptAsset:
    """Normalize a discussion persona into the shared prompt asset format."""
    return PromptAsset(
        id=persona.id,
        name=persona.name,
        position=persona.name,
        domain=persona.domain,
        description=persona.description,
        prompt=persona.prompt,
        kind="persona",
        prompt_mode="suffix",
        hat_context="orthogonal",
        hat=None,
        applicable_hats=_ALL_HATS,
        tags=[persona.domain, persona.id],
        source="persona",
        source_title=persona.name,
        source_path=source_path,
        status="ready",
    )
