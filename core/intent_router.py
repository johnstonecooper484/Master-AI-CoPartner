"""
core/intent_router.py

Intent Router — Think Before Speak
----------------------------------
Sits between inputs (voice, chat, vision context) and the AI brain (AIEngine).

Responsibilities:
- Two-pass reasoning (draft → verify)
- Permission gating for CHAT responses
- Voice input is ALWAYS allowed (voice is direct user intent)
- Auto-reply master switch for chat (default OFF)
- Manual response triggers
- Suggested-response queue (co-pilot mode)

This module NEVER:
- speaks directly
- writes memory directly
- executes actions directly
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import logging

log = logging.getLogger("intent_router")


class IntentRouter:
    def __init__(self):
        # --- PERMISSION STATE ---
        # Auto-reply to chat messages (MASTER SWITCH)
        self.auto_reply_enabled: bool = False  # DEFAULT = OFF (locked)

        # Manual triggers (one-shot)
        self.respond_now_requested: bool = False
        self.respond_to_suggestion_requested: bool = False

        # --- QUEUES / STATE ---
        self.last_message: Optional[Dict[str, Any]] = None
        self.suggested_response: Optional[Dict[str, Any]] = None

    # =========================================================
    # PERMISSION CONTROLS (called by UI / hotkeys later)
    # =========================================================

    def set_auto_reply(self, enabled: bool):
        self.auto_reply_enabled = bool(enabled)
        log.info("Auto-reply set to %s", self.auto_reply_enabled)

    def trigger_respond_now(self):
        self.respond_now_requested = True
        log.info("Manual respond-now triggered")

    def trigger_respond_to_suggestion(self):
        self.respond_to_suggestion_requested = True
        log.info("Respond-to-suggestion triggered")

    # =========================================================
    # INPUT REGISTRATION
    # =========================================================

    def register_message(self, message: Dict[str, Any]):
        """
        message example:
        {
            "user": "voice" / "viewer123",
            "text": "hello",
            "source": "voice_input" / "twitch"
        }
        """
        self.last_message = message
        # If a new message arrives, the old suggestion is no longer safe/relevant.
        self.suggested_response = None
        log.debug("Message registered: %s", message)

    # Backward compatible name (your main.py used register_chat_message)
    def register_chat_message(self, message: Dict[str, Any]):
        self.register_message(message)

    # =========================================================
    # CORE ROUTING LOGIC
    # =========================================================

    def route_intent(
        self,
        ai_engine,
        vision_description: Optional[str] = None
    ) -> Optional[str]:
        """
        Main entry point.
        Returns:
          - final response text (if allowed to speak)
          - None (if no response should be spoken)
        """

        if not self.last_message:
            return None

        src = str(self.last_message.get("source", "")).strip().lower()

        # -----------------------------------------------------
        # VOICE INPUT: ALWAYS ALLOWED
        # -----------------------------------------------------
        # Voice is direct user intent; it should respond normally.
        if src == "voice_input":
            return self._generate_response(
                ai_engine,
                self.last_message,
                vision_description
            )

        # -----------------------------------------------------
        # CHAT INPUT: PERMISSION GATED
        # -----------------------------------------------------
        if self.auto_reply_enabled:
            return self._generate_response(
                ai_engine,
                self.last_message,
                vision_description
            )

        if self.respond_now_requested:
            self.respond_now_requested = False
            return self._generate_response(
                ai_engine,
                self.last_message,
                vision_description
            )

        # Co-pilot mode: suggest only (queue draft), speak only if user triggers
        if not self.suggested_response:
            suggestion = self._draft_only(
                ai_engine,
                self.last_message,
                vision_description
            )
            self.suggested_response = {
                "message": self.last_message,
                "draft": suggestion
            }
            log.info("Suggested response queued (no speaking)")

        if self.respond_to_suggestion_requested and self.suggested_response:
            self.respond_to_suggestion_requested = False
            final = self._verify_and_finalize(
                ai_engine,
                self.suggested_response["draft"],
                self.suggested_response["message"],
                vision_description
            )
            self.suggested_response = None
            return final

        return None

    # =========================================================
    # ENGINE CALL (matches your AIEngine API)
    # =========================================================

    def _call_engine(self, ai_engine, prompt: str, source: str) -> str:
        """
        Your AIEngine uses .process(text, meta).
        We route prompts through that.
        """
        meta = {"source": source}
        return ai_engine.process(prompt, meta)

    # =========================================================
    # TWO-PASS THINK BEFORE SPEAK
    # =========================================================

    def _generate_response(self, ai_engine, message, vision_description):
        draft = self._draft_only(ai_engine, message, vision_description)
        final = self._verify_and_finalize(
            ai_engine, draft, message, vision_description
        )
        return final

    def _draft_only(self, ai_engine, message, vision_description):
        prompt = self._build_prompt(
            message,
            vision_description,
            mode="draft"
        )
        log.debug("Drafting response")
        return self._call_engine(ai_engine, prompt, source="intent_router_draft")

    def _verify_and_finalize(self, ai_engine, draft, message, vision_description):
        prompt = self._build_prompt(
            message,
            vision_description,
            mode="verify",
            draft=draft
        )
        log.debug("Verifying response")
        return self._call_engine(ai_engine, prompt, source="intent_router_verify")

    # =========================================================
    # PROMPT BUILDER
    # =========================================================

    def _build_prompt(
        self,
        message,
        vision_description,
        mode: str,
        draft: Optional[str] = None
    ) -> str:
        base = [
            "You are an AI co-partner assisting John.",
            "Rules:",
            "- Be concise and step-by-step.",
            "- Do NOT guess.",
            "- If uncertain, ask ONE short question.",
            "- Stay calm and respectful.",
        ]

        if vision_description:
            base.append("VISION CONTEXT:")
            base.append(vision_description)

        base.append("MESSAGE:")
        base.append(f'{message.get("user","?")}: {message.get("text","")}')

        if mode == "draft":
            base.append("TASK: Draft a helpful response. Do not over-explain.")
        elif mode == "verify":
            base.append("DRAFT RESPONSE:")
            base.append(draft or "")
            base.append(
                "TASK: Verify the draft matches the context. "
                "Fix errors. Shorten if needed. "
                "If confidence is low, ask one question instead."
            )

        return "\n".join(base)
