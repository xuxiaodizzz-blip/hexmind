"""Tests for engine/validator.py - hat constraint enforcement."""

from hexmind.engine.validator import OutputValidator
from hexmind.models.hat import HatColor
from hexmind.models.llm import TokenUsage
from hexmind.models.persona import Persona, PersonaTemperature
from hexmind.models.round import OutputItem, PanelistOutput


def _make_persona(**overrides) -> Persona:
    defaults = dict(
        id="test-persona",
        name="Test",
        domain="tech",
        description="test persona",
        temperature=PersonaTemperature(),
        system_prompt_suffix="",
    )
    defaults.update(overrides)
    return Persona(**defaults)


def _make_output(
    content: str,
    hat: HatColor,
    items: list[OutputItem] | None = None,
) -> PanelistOutput:
    return PanelistOutput(
        persona_id="test-persona",
        hat=hat,
        content=content,
        items=items or [],
        raw_content=content,
        token_usage=TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        validation_passed=True,
    )


class TestWhiteHat:
    def test_valid_white_output(self):
        v = OutputValidator()
        output = _make_output("W1: data shows 35% growth\nW2: sample size was 500", HatColor.WHITE)
        result = v.validate(output, HatColor.WHITE, _make_persona())
        assert result.passed

    def test_white_hat_rejects_opinions(self):
        v = OutputValidator()
        output = _make_output("W1: I think the market is growing quickly", HatColor.WHITE)
        result = v.validate(output, HatColor.WHITE, _make_persona())
        assert not result.passed
        assert any(v.rule == "prohibited_pattern" for v in result.violations)

    def test_white_hat_format_required(self):
        v = OutputValidator()
        output = _make_output("The market is growing by 35%", HatColor.WHITE)
        result = v.validate(output, HatColor.WHITE, _make_persona())
        assert not result.passed
        assert any(v.rule == "format" for v in result.violations)


class TestRedHat:
    def test_valid_red_output(self):
        v = OutputValidator()
        output = _make_output("直觉：这个方案让我不安。", HatColor.RED)
        result = v.validate(output, HatColor.RED, _make_persona())
        assert result.passed

    def test_red_hat_too_many_sentences(self):
        v = OutputValidator()
        content = "直觉：第一句。第二句。第三句。第四句。"
        output = _make_output(content, HatColor.RED)
        result = v.validate(output, HatColor.RED, _make_persona())
        assert not result.passed
        assert any(v.rule == "max_sentences" for v in result.violations)

    def test_red_hat_exactly_three_sentences(self):
        v = OutputValidator()
        content = "直觉：第一句。第二句。第三句。"
        output = _make_output(content, HatColor.RED)
        result = v.validate(output, HatColor.RED, _make_persona())
        assert result.passed


class TestBlackHat:
    def test_valid_black_output(self):
        v = OutputValidator()
        output = _make_output("B1: based on W1, there is a survivorship bias risk", HatColor.BLACK)
        result = v.validate(output, HatColor.BLACK, _make_persona())
        assert result.passed

    def test_black_hat_must_reference_white(self):
        v = OutputValidator()
        output = _make_output("B1: there is technical risk", HatColor.BLACK)
        result = v.validate(output, HatColor.BLACK, _make_persona())
        assert not result.passed
        assert any(v.rule == "references" for v in result.violations)

    def test_black_hat_format_required(self):
        v = OutputValidator()
        output = _make_output("Risk comes from weak evidence", HatColor.BLACK)
        result = v.validate(output, HatColor.BLACK, _make_persona())
        assert not result.passed
        assert any(v.rule == "format" for v in result.violations)


class TestYellowHat:
    def test_valid_yellow_output(self):
        v = OutputValidator()
        output = _make_output("Y1: based on W1, this creates a large market opportunity", HatColor.YELLOW)
        result = v.validate(output, HatColor.YELLOW, _make_persona())
        assert result.passed

    def test_yellow_hat_must_reference_white(self):
        v = OutputValidator()
        output = _make_output("Y1: this is a huge opportunity", HatColor.YELLOW)
        result = v.validate(output, HatColor.YELLOW, _make_persona())
        assert not result.passed
        assert any(v.rule == "references" for v in result.violations)


class TestGreenHat:
    def test_valid_green_output(self):
        v = OutputValidator()
        output = _make_output("G1: to address B1, roll this out gradually", HatColor.GREEN)
        result = v.validate(output, HatColor.GREEN, _make_persona())
        assert result.passed

    def test_green_hat_must_reference_black(self):
        v = OutputValidator()
        output = _make_output("G1: roll this out gradually", HatColor.GREEN)
        result = v.validate(output, HatColor.GREEN, _make_persona())
        assert not result.passed
        assert any(v.rule == "references" for v in result.violations)


class TestMultipleViolations:
    def test_accumulates_violations(self):
        v = OutputValidator()
        output = _make_output("I think this market is great", HatColor.WHITE)
        result = v.validate(output, HatColor.WHITE, _make_persona())
        assert not result.passed
        rules = {v.rule for v in result.violations}
        assert "prohibited_pattern" in rules
        assert "format" in rules


class TestEmptyContent:
    def test_empty_content_fails_format(self):
        v = OutputValidator()
        output = _make_output("", HatColor.WHITE)
        result = v.validate(output, HatColor.WHITE, _make_persona())
        assert not result.passed
        assert any(v.rule == "format" for v in result.violations)
