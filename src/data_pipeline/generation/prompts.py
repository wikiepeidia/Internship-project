"""Prompt builders for tiered synthetic dataset generation and judging."""

import json
from textwrap import dedent


THREAT_CLASSES = ["bank_impersonation", "zalo_social_engineering", "task_scam", "benign"]

# Explicit scenario diversity axes for task_scam (used in both complex and bulk prompts).
# Each axis maps to a characteristic trust-then-disappear or advance-payment social-engineering
# pattern observed in real Vietnamese task-scam recruitment messages.
_TASK_SCAM_SCENARIO_AXES = dedent(
    """
    Scenario axes — cover as many distinct types as possible across the generated samples:
    1. Like/follow/comment farms: recruiter asks victims to like, follow, or comment on social
       media posts (TikTok, Facebook, YouTube) for per-task pay that never arrives.
    2. Shopee/Lazada review-bombing: victim is told to buy a product, post a 5-star review,
       then receive a full cashback refund plus commission — advance purchase is never refunded.
    3. Crypto referral schemes: victim earns commissions by registering on a fake crypto platform
       via the recruiter's link; withdrawals are always blocked until "verification fees" are paid.
    4. Fake purchase seeding (order-boosting): victim places ghost orders on an online shop to
       inflate sales rankings; the "commission" transfer is delayed indefinitely after payment.
    5. Zalo/Telegram livestream engagement: victim joins a livestream group and places fake
       engagement orders; after completing several small paid tasks the final larger task is
       blocked until an "account upgrade fee" is sent.

    Each message MUST follow one of these two social-engineering structures:
    - Trust-then-disappear: recruiter pays small amounts first to build trust, then disappears
      after the victim completes a larger task or sends a deposit.
    - Advance-payment: victim is asked to pay an activation, registration, or upgrade fee
      before receiving any payment; the fee is always lost.
    """
).strip()


def _build_task_scam_diversity_block(count_label: str) -> str:
    """Return the task_scam-specific diversity instructions block for prompt injection."""
    return dedent(
        f"""
        IMPORTANT — this is a task_scam generation run targeting {count_label}.
        task_scam messages are the hardest class to detect because they resemble legitimate
        part-time job offers. To maximize recall for this class the generated messages MUST:
        - Use distinctive scenario types, not generic "online job" phrasing.
        - Name specific platforms (TikTok, Shopee, Lazada, Binance, Zalo, Telegram).
        - Include concrete pay structures (per-task rate, daily cap, commission percentage).
        - Show the trust-then-disappear or advance-payment manipulation pattern explicitly.
        - Vary recruiter persona: Facebook group admin, Zalo contact, Telegram bot, SMS.
        - Use natural Vietnamese code-switching: task, order, commission, app, link, group.
        - Mix short SMS pitches and longer Zalo/Messenger conversation-style messages.

        {_TASK_SCAM_SCENARIO_AXES}
        """
    ).strip()


def build_complex_prompt(seed_text: str, threat_class: str, num_variants: int = 3) -> str:
    """Build the high-quality Claude prompt for complex synthetic examples."""
    task_scam_block = (
        "\n\n        " + _build_task_scam_diversity_block(f"{num_variants} variants")
        if threat_class == "task_scam"
        else ""
    )
    return dedent(
        f"""
    You are generating realistic Vietnamese financial messaging examples for a phishing detection dataset.

        Seed text anchor:
        {seed_text}

        Target threat class: {threat_class}
        Variants required: {num_variants}

        Requirements:
        - Generate {num_variants} realistic Vietnamese message variants as a JSON array.
        - Preserve natural Vietnamese code-switching with OTP, Internet Banking, Smart OTP, link, login, app, and account.
        - Use Vietnamese teencode or SMS shorthand only when natural, including k, ko, dc, nha, ak.
        - Vary URLs, phone numbers, urgency level, sender persona, and channel style.
        - Produce a mix of short SMS-like messages and longer Zalo or Messenger-like messages.
        - Do not copy the seed URL, sender, or phone number directly.
        - risk_tier is contextual and MUST be assigned from semantic severity, not derived from label.
        - suspicious_spans must contain up to 3 exact substrings from the generated text; use [] when none apply.
        - xai_explanation must be one concise Vietnamese sentence, specific and actionable, with at least 20 characters.{task_scam_block}

        Return ONLY a JSON array with text, label, risk_tier, suspicious_spans, and xai_explanation.
        """
    ).strip()


def build_bulk_prompt(seed_text: str, threat_class: str, count: int = 10) -> str:
    """Build the higher-diversity prompt for Gemini or OpenRouter bulk generation."""
    task_scam_block = (
        "\n\n        " + _build_task_scam_diversity_block(f"{count} samples")
        if threat_class == "task_scam"
        else ""
    )
    return dedent(
        f"""
        Generate {count} Vietnamese financial messaging examples as a JSON array.

        Seed text anchor:
        {seed_text}

        Target threat class: {threat_class}

        Diversity instructions:
        - Prioritize diversity across phrasing, sender identity, urgency, fake URLs, phone numbers, formatting, and social-engineering hooks.
        - Keep natural Vietnamese code-switching with OTP, Internet Banking, Smart OTP, login, app, account, and link where realistic.
        - Include natural teencode or shorthand such as k, ko, dc, nha, ak where appropriate.
        - Keep xai_explanation to one concise Vietnamese sentence that stays specific and actionable.
        - risk_tier is contextual and not a fixed mapping from label.
        - suspicious_spans must contain up to 3 exact substrings from the text; use [] when none apply.{task_scam_block}

        Return ONLY a JSON array with text, label, risk_tier, suspicious_spans, and xai_explanation.
        """
    ).strip()


def build_judge_prompt(
        record_text: str,
        record_label: str,
        record_risk_tier: str,
        record_suspicious_spans: list[str],
        record_explanation: str,
) -> str:
    """Build the LLM-as-judge prompt for synthetic sample validation."""
    return dedent(
        f"""
                Validate this synthetic Vietnamese financial messaging sample.

        Text:
        {record_text}

        Label: {record_label}
                Risk tier: {record_risk_tier}
                Suspicious spans: {json.dumps(record_suspicious_spans, ensure_ascii=False)}
        Explanation:
        {record_explanation}

                Score these dimensions from 1 to 5:
                - realism
                - label_correctness
                - code_switch_naturalness
                - risk_tier_correctness
                - suspicious_span_accuracy

                For suspicious_span_accuracy, score whether the spans are exact substrings from the text and whether they point to genuinely suspicious cues.
                Mark pass true only if all five scores are at least 3.

        Return ONLY this JSON object:
        {{
          "realism": 1,
          "label_correctness": 1,
          "code_switch_naturalness": 1,
                    "risk_tier_correctness": 1,
                    "suspicious_span_accuracy": 1,
          "pass": false,
                    "reason": "very short reason, max 18 words"
        }}
        """
    ).strip()


def build_benign_prompt(num_variants: int = 10) -> str:
    """Build a benign-only generation prompt to diversify the negative class."""
    return dedent(
        f"""
        Generate {num_variants} benign Vietnamese financial messages as a JSON array.

        Cover diverse benign scenarios such as bank notifications, transaction confirmations, service updates, marketing offers, OTP confirmations, account statements, and balance alerts.

        Requirements:
        - label MUST be exactly "benign" for every item. Do not use subtype labels such as transaction_confirmation, service_update, otp_confirmation, or marketing_offer.
        - Use natural Vietnamese with realistic code-switching such as OTP, Internet Banking, Smart OTP, app, account, and login when appropriate.
        - Keep risk_tier appropriate to benign or at most low-suspicion edge cases only when the wording justifies it.
        - suspicious_spans should be empty unless the wording genuinely contains a confusing cue.
        - xai_explanation must be one concise Vietnamese sentence with at least 20 characters.
        - Return ONLY a JSON array with text, label, risk_tier, suspicious_spans, and xai_explanation.
        """
    ).strip()